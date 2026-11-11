import asyncio
import json
import pytest
from pathlib import Path
from app.sandbox.docker_runner import DockerSandboxRunner


@pytest.mark.asyncio
async def test_docker_available_detects_image():
    is_avail = await DockerSandboxRunner.is_docker_available()
    assert is_avail is True, "Expected data-detective-sandbox:latest image to be present and available in Docker."


@pytest.mark.asyncio
async def test_docker_executes_analysis_successfully(tmp_path):
    dataset_file = tmp_path / "sales.csv"
    dataset_file.write_text("item,qty,price\nA,10,5.0\nB,5,20.0\nA,2,5.0\n", encoding="utf-8")

    code = """
import json
import pandas as pd
import numpy as np
import plotly.express as px

# Analysis
total_revenue = float((df['qty'] * df['price']).sum())
summary = df.groupby('item')['qty'].sum().reset_index()

fig = px.bar(summary, x='item', y='qty', title='Quantity by Item')

results = {
    "status": "success",
    "metrics": {"total_revenue": total_revenue},
    "tables": [{"name": "item_summary", "columns": list(summary.columns), "data": summary.to_dict(orient="records")}],
    "charts": [{"figure": json.loads(fig.to_json()), "caption": "Quantity by Item"}],
    "warnings": []
}

with open("output/results.json", "w") as f:
    json.dump(results, f)
"""

    output = await DockerSandboxRunner.execute(
        code=code,
        dataset_path=dataset_file,
        file_type="csv",
        timeout_seconds=10,
    )

    assert output.status == "success", f"Container execution failed: {output.error_message}"
    assert output.metrics.get("total_revenue") == 160.0
    assert len(output.tables) == 1
    assert output.tables[0]["name"] == "item_summary"
    assert len(output.charts) == 1
    assert "data" in output.charts[0]["figure"]


@pytest.mark.asyncio
async def test_docker_enforces_non_root_user():
    """Verify that container executes as non-root user UID 10001 (sandboxuser)."""
    proc = await asyncio.create_subprocess_exec(
        "docker", "run", "--rm",
        "--user", "10001:10001",
        DockerSandboxRunner.IMAGE_NAME,
        "id", "-u",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    assert stdout.decode().strip() == "10001"


@pytest.mark.asyncio
async def test_docker_enforces_readonly_dataset_and_workspace(tmp_path):
    """Verify that attempts to write to read-only rootfs or read-only dataset mount fail with OSError."""
    dummy_csv = tmp_path / "dummy.csv"
    dummy_csv.write_text("a,b\n1,2\n", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    proc = await asyncio.create_subprocess_exec(
        "docker", "run", "--rm",
        "--read-only",
        "--user", "10001:10001",
        "-v", f"{dummy_csv.resolve()}:/workspace/dataset.csv:ro",
        "-v", f"{output_dir.resolve()}:/workspace/output:rw",
        "-w", "/workspace",
        DockerSandboxRunner.IMAGE_NAME,
        "python3", "-c", "open('dataset.csv', 'w')",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode != 0
    err_str = stderr.decode()
    assert "Read-only file system" in err_str or "Permission denied" in err_str


@pytest.mark.asyncio
async def test_docker_allows_output_directory_write(tmp_path):
    """Verify that writing strictly inside /workspace/output succeeds while rootfs is read-only."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    proc = await asyncio.create_subprocess_exec(
        "docker", "run", "--rm",
        "--read-only",
        "--user", "10001:10001",
        "-v", f"{output_dir.resolve()}:/workspace/output:rw",
        "-w", "/workspace",
        DockerSandboxRunner.IMAGE_NAME,
        "python3", "-c", "with open('output/test.txt', 'w') as f: f.write('ok')",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert proc.returncode == 0
    assert (output_dir / "test.txt").read_text() == "ok"


@pytest.mark.asyncio
async def test_docker_timeout_enforcement(tmp_path):
    """Verify that long-running computation inside container triggers timeout."""
    dataset_file = tmp_path / "dummy.csv"
    dataset_file.write_text("x\n1\n", encoding="utf-8")

    code = """
import time
time.sleep(10)
"""
    t0 = asyncio.get_event_loop().time()
    output = await DockerSandboxRunner.execute(
        code=code,
        dataset_path=dataset_file,
        file_type="csv",
        timeout_seconds=2,
    )
    elapsed = asyncio.get_event_loop().time() - t0

    assert 1.5 <= elapsed <= 4.5
    assert output.status == "error"
    assert "timed out" in output.error_message.lower()
