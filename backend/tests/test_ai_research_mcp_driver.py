"""Tests for the agent-side Colab MCP driver bridge (OD-41 / WP5)."""

import asyncio
import json

import pytest

from app.services.ai_research import ColabMCPDriver
from app.services.free_sandboxes.base import EnvironmentState, SandboxError, WorkloadRequest


def spec(accelerator, variant="VARIANT_GPU", eligible=True):
    return {
        "eligible": eligible,
        "key": {
            "accelerator": accelerator,
            "variant": variant,
            "shape": "SHAPE_STANDARD",
        },
    }


class StubCaller:
    def __init__(self, specs=None, runtimes=None, result=None, execution_error=None):
        self.specs = specs if specs is not None else [spec("T4")]
        self.runtimes = runtimes or []
        self.result = result or {"accuracy": 0.82}
        self.execution_error = execution_error
        self.calls = []

    async def __call__(self, name, args):
        self.calls.append((name, args))
        if name == "list_runtime_specs":
            return {"runtimeSpecs": self.specs}
        if name == "list_runtimes":
            return {"runtimes": self.runtimes}
        if name == "create_runtime":
            return {"name": "runtimes/new-runtime"}
        if name == "create_session":
            return {"name": "runtimes/new-runtime/sessions/iam-1"}
        if name == "execute_code":
            if self.execution_error:
                return {"executionError": {"name": "RuntimeError", "value": self.execution_error}}
            if "iam_result.json" in args.get("code", ""):
                return {"stdout": json.dumps(self.result)}
            return {"stdout": "ok"}
        if name in ("delete_session", "delete_runtime"):
            return {}
        raise AssertionError(f"unexpected tool: {name}")


def request():
    return WorkloadRequest(
        task_id="exp_mcp",
        capability="model_evaluation",
        description="vLLM serving",
    )


def test_pick_gpu_spec_prefers_free_t4():
    driver = ColabMCPDriver(StubCaller(specs=[spec("A100", eligible=False), spec("T4")]))
    picked = driver.pick_gpu_spec(asyncio.run(driver.runtime_specs()))
    assert picked["accelerator"] == "T4"


def test_pick_gpu_spec_fails_closed_when_no_gpu():
    driver = ColabMCPDriver(StubCaller(specs=[spec("NONE", variant="VARIANT_CPU")]))
    with pytest.raises(SandboxError):
        driver.pick_gpu_spec(asyncio.run(driver.runtime_specs()))


def test_provision_reuses_existing_gpu_runtime():
    caller = StubCaller(
        runtimes=[{"name": "runtimes/existing", "runtimeSpec": {"key": spec("T4")["key"]}}]
    )
    driver = ColabMCPDriver(caller)
    assert asyncio.run(driver.provision(request())) == "runtimes/existing"
    assert not any(name == "create_runtime" for name, _ in caller.calls)


def test_provision_creates_runtime_with_request_id():
    caller = StubCaller()
    driver = ColabMCPDriver(caller)
    name = asyncio.run(driver.provision(request()))
    assert name == "runtimes/new-runtime"
    create = next(args for tool_name, args in caller.calls if tool_name == "create_runtime")
    assert create["requestId"]
    assert create["runtime"]["runtimeSpec"]["accelerator"] == "T4"


def test_execute_cells_and_collect_result():
    caller = StubCaller(result={"accuracy": 0.91})
    driver = ColabMCPDriver(caller)
    asyncio.run(driver.provision(request()))
    asyncio.run(driver.start("runtimes/new-runtime"))
    outputs = asyncio.run(driver.execute_cells("runtimes/new-runtime", ["print(1)", "x = 2"]))
    assert len(outputs) == 2
    assert asyncio.run(driver.collect("runtimes/new-runtime")) == {"accuracy": 0.91}


def test_execution_error_is_reported():
    driver = ColabMCPDriver(StubCaller(execution_error="out of memory"))
    asyncio.run(driver.provision(request()))
    asyncio.run(driver.start("runtimes/new-runtime"))
    with pytest.raises(SandboxError, match="out of memory"):
        asyncio.run(driver.execute_cells("runtimes/new-runtime", ["bad()"]))


def test_status_and_cleanup():
    caller = StubCaller(runtimes=[{"name": "runtimes/new-runtime"}])
    driver = ColabMCPDriver(caller)
    asyncio.run(driver.provision(request()))
    asyncio.run(driver.start("runtimes/new-runtime"))
    assert asyncio.run(driver.status("runtimes/new-runtime")) == EnvironmentState.RUNNING
    asyncio.run(driver.cleanup("runtimes/new-runtime", delete_runtime=True))
    called = {name for name, _ in caller.calls}
    assert "delete_session" in called
    assert "delete_runtime" in called
