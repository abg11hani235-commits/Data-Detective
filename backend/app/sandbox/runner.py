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
from app.sandbox.security import CodeSecurityChecker


async def read_bounded_process_output(
    proc: asyncio.subprocess.Process,
    max_bytes: int,
    timeout: float,
) -> Tuple[str, str, bool, bool]:
    """
    Reads stdout and stderr concurrently up to max_bytes without buffering unbounded data in RAM.
    If stream output exceeds max_bytes or process exceeds timeout, kills process immediately.
    Returns (stdout_str, stderr_str, is_timeout, is_output_exceeded).
    """
    stdout_chunks: List[bytes] = []
    stderr_chunks: List[bytes] = []
    stdout_len = 0
    stderr_len = 0
    exceeded = False

    async def read_stream(stream: Optional[asyncio.StreamReader], is_stdout: bool):
        nonlocal stdout_len, stderr_len, exceeded
        if not stream:
            return
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break
            if is_stdout:
                stdout_len += len(chunk)
                if stdout_len <= max_bytes:
                    stdout_chunks.append(chunk)
                else:
                    exceeded = True
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break
            else:
                stderr_len += len(chunk)
                if stderr_len <= max_bytes:
                    stderr_chunks.append(chunk)
                else:
                    exceeded = True
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    break

    try:
        await asyncio.wait_for(
            asyncio.gather(
                read_stream(proc.stdout, True),
                read_stream(proc.stderr, False),
                proc.wait(),
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return (
            b"".join(stdout_chunks).decode("utf-8", errors="replace"),
            b"".join(stderr_chunks).decode("utf-8", errors="replace"),
            True,   # is_timeout
            exceeded,
        )

    return (
        b"".join(stdout_chunks).decode("utf-8", errors="replace"),
        b"".join(stderr_chunks).decode("utf-8", errors="replace"),
        False,  # is_timeout
        exceeded,
    )


class SandboxRunner:
    """
    Isolated Python Execution Worker.
    Runs analysis code in an isolated subprocess with stripped environment,
    restricted directory access, and timeout enforcement.
    Note: On platforms without Docker containerization, this represents an MVP
    process isolation boundary with defense-in-depth, not a hardened microVM.
    """

    MAX_OUTPUT_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

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

        # Step 1: Static AST validation
        is_safe, violations = CodeSecurityChecker.validate_code(code)
        if not is_safe:
            return ExecutionOutput(
                status="error",
                error_message="Security Policy Violation: " + "; ".join(violations),
                warnings=violations,
            )

        # Step 2: Prepare temporary isolated directory
        run_id = str(uuid.uuid4())
        sandbox_dir = settings.SANDBOX_DIR / run_id
        output_dir = sandbox_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy dataset into sandbox
            dest_dataset = sandbox_dir / f"dataset.{file_type.lower()}"
            shutil.copyfile(dataset_path, dest_dataset)

            # Generate execution script wrapper
            wrapper_script = cls._build_script(code, file_type.lower())
            script_path = sandbox_dir / "analysis.py"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(wrapper_script)

            # Step 3: Prepare stripped environment (no secrets/API keys)
            safe_env: Dict[str, str] = {
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            }

            # Step 4: Execute in child process with timeout and bounded stream reading
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "analysis.py",
                cwd=str(sandbox_dir),
                env=safe_env,
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
                    error_message=f"Execution timed out after {timeout} seconds. The computation was too intensive.",
                    stdout=stdout_str,
                )

            if is_output_exceeded:
                return ExecutionOutput(
                    status="error",
                    error_message=f"Execution exceeded maximum output limit ({settings.MAX_STDOUT_BYTES} bytes).",
                    stdout=stdout_str,
                )

            # Step 5: Check exit code
            if proc.returncode != 0:
                clean_stderr = stderr_str.strip()
                # Remove absolute sandbox path references for clean error reporting
                clean_stderr = clean_stderr.replace(str(sandbox_dir), "[sandbox]")
                return ExecutionOutput(
                    status="error",
                    error_message=clean_stderr or f"Process failed with exit code {proc.returncode}",
                    stdout=stdout_str,
                )

            # Step 6: Validate output contract
            results_file = output_dir / "results.json"
            if not results_file.exists():
                return ExecutionOutput(
                    status="error",
                    error_message="Analysis completed but did not produce 'output/results.json' according to contract.",
                    stdout=stdout_str,
                )

            # Check output file size
            file_size = results_file.stat().st_size
            if file_size > cls.MAX_OUTPUT_SIZE_BYTES:
                return ExecutionOutput(
                    status="error",
                    error_message=f"Output payload exceeded size limit ({file_size} bytes > {cls.MAX_OUTPUT_SIZE_BYTES} bytes).",
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

        except Exception as e:
            logger.error(f"Unexpected sandbox error: {type(e).__name__}: {str(e)}")
            return ExecutionOutput(
                status="error",
                error_message=f"Execution environment error: {str(e)}",
            )
        finally:
            # Clean up sandbox directory
            try:
                shutil.rmtree(sandbox_dir, ignore_errors=True)
            except Exception:
                pass

    @classmethod
    def _build_script(cls, user_code: str, file_type: str) -> str:
        # Preload the DataFrame so user code has immediate access to `df`
        loader = ""
        if file_type == "csv":
            loader = "df = pd.read_csv('dataset.csv')"
        elif file_type in ["xlsx", "xls"]:
            loader = "df = pd.read_excel('dataset.xlsx')"
        elif file_type == "json":
            loader = "df = pd.read_json('dataset.json')"
        else:
            loader = "df = pd.read_csv('dataset.csv')"

        return f"""# -*- coding: utf-8 -*-
import os
import sys
import json
import pandas as pd
import numpy as np

# Create output folder
os.makedirs('output', exist_ok=True)

# Preload dataset
{loader}

# Scrub runtime environment and disable dangerous attributes
os.environ.clear()
for dangerous_attr in ['system', 'popen', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe', 'fork']:
    if hasattr(os, dangerous_attr):
        try:
            delattr(os, dangerous_attr)
        except Exception:
            pass

# User analysis script starts here
{user_code}
"""
