import asyncio
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.config import settings
from app.logging import logger
from app.models.schemas import ExecutionOutput
from app.sandbox.runner import SandboxRunner, read_bounded_process_output
from app.sandbox.security import CodeSecurityChecker


class DockerSandboxRunner:
    """
    Production-grade container execution runner using rootless Docker.
    Enforces kernel-level boundaries:
      - --network none (strictly offline)
      - --read-only root filesystem
      - --tmpfs /tmp:rw,noexec,nosuid,size=64m
      - --user 10001:10001 (unprivileged non-root UID)
      - --security-opt no-new-privileges:true
      - --cap-drop=ALL (drops all Linux capabilities)
      - --cpus=1.0 & --memory=512m & --pids-limit=64
      - Split mounts: read-only dataset & code, isolated read-write output/
    Falls back gracefully to SandboxRunner (AST-filtered subprocess) if Docker daemon is not active.
    """

    IMAGE_NAME = "data-detective-sandbox:latest"

    @classmethod
    async def is_docker_available(cls) -> bool:
        """Check if Docker CLI is installed, daemon is reachable, and sandbox image exists."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "image",
                "inspect",
                cls.IMAGE_NAME,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            return proc.returncode == 0
        except Exception:
            return False

    @classmethod
    async def execute(
        cls,
        code: str,
        dataset_path: Path,
        file_type: str,
        timeout_seconds: Optional[int] = None,
    ) -> ExecutionOutput:
        timeout = timeout_seconds or settings.SANDBOX_TIMEOUT_SECONDS

        # Check code size limit
        if len(code.encode("utf-8")) > settings.MAX_GENERATED_CODE_SIZE_BYTES:
            return ExecutionOutput(
                status="error",
                error_message=f"Code size limit exceeded ({len(code)} bytes > {settings.MAX_GENERATED_CODE_SIZE_BYTES} bytes).",
            )

        # Static AST validation check first
        is_safe, violations = CodeSecurityChecker.validate_code(code)
        if not is_safe:
            return ExecutionOutput(
                status="error",
                error_message="Security Policy Violation: " + "; ".join(violations),
                warnings=violations,
            )

        docker_ready = await cls.is_docker_available()
        if not docker_ready:
            logger.info(
                "Docker daemon is not available on host. Gracefully delegating execution to AST-restricted subprocess sandbox."
            )
            return await SandboxRunner.execute(
                code=code,
                dataset_path=dataset_path,
                file_type=file_type,
                timeout_seconds=timeout,
            )

        # Prepare isolated workspace
        run_id = str(uuid.uuid4())
        sandbox_dir = settings.SANDBOX_DIR / run_id
        output_dir = sandbox_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy dataset into sandbox
            dest_dataset = sandbox_dir / f"dataset.{file_type.lower()}"
            shutil.copyfile(dataset_path, dest_dataset)

            # Generate script wrapper
            wrapper_script = SandboxRunner._build_script(code, file_type.lower())
            script_path = sandbox_dir / "analysis.py"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(wrapper_script)

            # Build Docker command with non-root user, dropped capabilities, no-new-privileges, and split ro/rw mounts
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "--security-opt", "no-new-privileges:true",
                "--user", "10001:10001",
                "--cap-drop=ALL",
                "--cpus", "1.0",
                "--memory", f"{settings.SANDBOX_MAX_MEMORY_MB}m",
                "--pids-limit", "64",
                "-v", f"{dest_dataset.resolve()}:/workspace/dataset.{file_type.lower()}:ro",
                "-v", f"{script_path.resolve()}:/workspace/analysis.py:ro",
                "-v", f"{output_dir.resolve()}:/workspace/output:rw",
                "-w", "/workspace",
                cls.IMAGE_NAME,
                "python3", "analysis.py",
            ]

            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_str, stderr_str, is_timeout, is_output_exceeded = await read_bounded_process_output(
                proc=proc,
                max_bytes=settings.MAX_STDOUT_BYTES,
                timeout=float(timeout),
            )

            if is_timeout:
                return ExecutionOutput(
                    status="error",
                    error_message=f"Container execution timed out after {timeout} seconds.",
                    stdout=stdout_str,
                )

            if is_output_exceeded:
                return ExecutionOutput(
                    status="error",
                    error_message=f"Container execution exceeded maximum output limit ({settings.MAX_STDOUT_BYTES} bytes).",
                    stdout=stdout_str,
                )

            if proc.returncode != 0:
                clean_stderr = stderr_str.strip().replace(str(sandbox_dir), "[sandbox]")
                return ExecutionOutput(
                    status="error",
                    error_message=clean_stderr or f"Container process failed with code {proc.returncode}",
                    stdout=stdout_str,
                )

            # Validate output contract
            results_file = output_dir / "results.json"
            if not results_file.exists():
                return ExecutionOutput(
                    status="error",
                    error_message="Analysis completed in container but did not produce 'output/results.json'.",
                    stdout=stdout_str,
                )

            # Check output file size limit before reading into memory
            file_size = results_file.stat().st_size
            if file_size > SandboxRunner.MAX_OUTPUT_SIZE_BYTES:
                return ExecutionOutput(
                    status="error",
                    error_message=f"Container output payload exceeded size limit ({file_size} bytes > {SandboxRunner.MAX_OUTPUT_SIZE_BYTES} bytes).",
                )

            with open(results_file, "r", encoding="utf-8") as f:
                output_data = json.load(f)

            return ExecutionOutput(
                status=output_data.get("status", "success"),
                tables=output_data.get("tables", []),
                metrics=output_data.get("metrics", {}),
                charts=output_data.get("charts", []),
                warnings=output_data.get("warnings", []),
                stdout=stdout_str,
            )

        except Exception as exc:
            logger.error(f"Docker sandbox unexpected error: {str(exc)}")
            return ExecutionOutput(
                status="error",
                error_message=f"Container execution error: {str(exc)}",
            )
        finally:
            try:
                shutil.rmtree(sandbox_dir, ignore_errors=True)
            except Exception:
                pass
