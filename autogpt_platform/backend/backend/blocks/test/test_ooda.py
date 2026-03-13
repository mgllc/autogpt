"""Tests for OODA Loop blocks (GovDOSS integration)."""

import pytest

from backend.blocks.ooda import (
    OODAActBlock,
    OODADecideBlock,
    OODAObserveBlock,
    OODAOrientBlock,
)
from backend.executor.ooda_loop import OODAContext, OODAStage
from backend.util.govdoss import KIS4Dimension, KIS4Tag, SOA4Action, SOA4AuditEvent
from backend.util.test import execute_block_test

# ---------------------------------------------------------------------------
# Block scaffold tests (run each block's built-in test_input / test_output)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ooda_observe_block():
    await execute_block_test(OODAObserveBlock())


@pytest.mark.asyncio
async def test_ooda_orient_block():
    await execute_block_test(OODAOrientBlock())


@pytest.mark.asyncio
async def test_ooda_decide_block():
    await execute_block_test(OODADecideBlock())


@pytest.mark.asyncio
async def test_ooda_act_block():
    await execute_block_test(OODAActBlock())


# ---------------------------------------------------------------------------
# Observe stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observe_emits_observation_and_stage():
    block = OODAObserveBlock()
    outputs: list[tuple[str, object]] = []
    async for key, value in block.run(
        OODAObserveBlock.Input(
            data={"sensor": "temperature", "value": 42}, source="iot"
        )
    ):
        outputs.append((key, value))

    keys = {k for k, _ in outputs}
    assert "observation" in keys
    assert "ooda_stage" in keys
    assert dict(outputs)["ooda_stage"] == OODAStage.OBSERVE.value
    assert dict(outputs)["source"] == "iot"


@pytest.mark.asyncio
async def test_observe_defaults_source_to_unknown():
    block = OODAObserveBlock()
    outputs = {}
    async for key, value in block.run(OODAObserveBlock.Input(data="hello")):
        outputs[key] = value

    assert outputs["source"] == "unknown"


# ---------------------------------------------------------------------------
# Orient stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orient_builds_orientation_model():
    block = OODAOrientBlock()
    obs = {"reading": 99}
    ctx = {"threshold": 80}

    outputs = {}
    async for key, value in block.run(
        OODAOrientBlock.Input(observation=obs, context=ctx, label="temp_check")
    ):
        outputs[key] = value

    assert outputs["ooda_stage"] == OODAStage.ORIENT.value
    orientation = outputs["orientation"]
    assert orientation["label"] == "temp_check"
    assert orientation["observation"] == obs
    assert orientation["context"] == ctx


@pytest.mark.asyncio
async def test_orient_defaults_label():
    block = OODAOrientBlock()
    outputs = {}
    async for key, value in block.run(OODAOrientBlock.Input(observation="data")):
        outputs[key] = value

    assert outputs["orientation"]["label"] == "observation"


# ---------------------------------------------------------------------------
# Decide stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decide_selects_from_context_key():
    block = OODADecideBlock()
    orientation = {
        "label": "test",
        "observation": "x",
        "context": {"next_action": "abort"},
    }
    outputs = {}
    async for key, value in block.run(
        OODADecideBlock.Input(
            orientation=orientation,
            options=["proceed", "abort", "wait"],
            decision_key="next_action",
        )
    ):
        outputs[key] = value

    assert outputs["decision"] == "abort"
    assert outputs["ooda_stage"] == OODAStage.DECIDE.value


@pytest.mark.asyncio
async def test_decide_fallback_to_first_option():
    block = OODADecideBlock()
    orientation = {"label": "test", "observation": "x", "context": {}}
    outputs = {}
    async for key, value in block.run(
        OODADecideBlock.Input(
            orientation=orientation,
            options=["proceed", "abort"],
        )
    ):
        outputs[key] = value

    assert outputs["decision"] == "proceed"


@pytest.mark.asyncio
async def test_decide_unknown_key_falls_back_to_first_option():
    block = OODADecideBlock()
    orientation = {
        "label": "test",
        "observation": "x",
        "context": {"next_action": "fly"},  # "fly" not in options
    }
    outputs = {}
    async for key, value in block.run(
        OODADecideBlock.Input(
            orientation=orientation,
            options=["proceed", "abort"],
            decision_key="next_action",
        )
    ):
        outputs[key] = value

    assert outputs["decision"] == "proceed"


# ---------------------------------------------------------------------------
# Act stage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_act_records_outcome_and_closes_cycle():
    block = OODAActBlock()
    outputs = {}
    async for key, value in block.run(
        OODAActBlock.Input(action="proceed", result={"status": "ok"}, success=True)
    ):
        outputs[key] = value

    assert outputs["action"] == "proceed"
    assert outputs["result"] == {"status": "ok"}
    assert outputs["success"] is True
    assert outputs["cycle_complete"] is True
    assert outputs["ooda_stage"] == OODAStage.ACT.value


@pytest.mark.asyncio
async def test_act_records_failure():
    block = OODAActBlock()
    outputs = {}
    async for key, value in block.run(
        OODAActBlock.Input(action="abort", result=None, success=False)
    ):
        outputs[key] = value

    assert outputs["success"] is False
    assert outputs["cycle_complete"] is True


# ---------------------------------------------------------------------------
# OODAContext (executor model)
# ---------------------------------------------------------------------------


def test_ooda_context_initial_stage():
    ctx = OODAContext()
    assert ctx.current_stage == OODAStage.OBSERVE
    assert ctx.cycle_count == 0


def test_ooda_context_advance_through_full_cycle():
    ctx = OODAContext()
    ctx = ctx.advance()
    assert ctx.current_stage == OODAStage.ORIENT
    ctx = ctx.advance()
    assert ctx.current_stage == OODAStage.DECIDE
    ctx = ctx.advance()
    assert ctx.current_stage == OODAStage.ACT
    # completing ACT resets to OBSERVE and increments cycle_count
    ctx = ctx.advance()
    assert ctx.current_stage == OODAStage.OBSERVE
    assert ctx.cycle_count == 1


def test_ooda_context_record_observation():
    ctx = OODAContext()
    ctx = ctx.record_observation("data1")
    ctx = ctx.record_observation("data2")
    assert ctx.observations == ["data1", "data2"]


def test_ooda_context_set_orientation():
    ctx = OODAContext()
    ctx = ctx.set_orientation({"key": "value"})
    assert ctx.orientation == {"key": "value"}


def test_ooda_context_set_decision():
    ctx = OODAContext()
    ctx = ctx.set_decision("proceed")
    assert ctx.decision == "proceed"


def test_ooda_context_record_act_result():
    ctx = OODAContext()
    ctx = ctx.record_act_result({"status": "ok"})
    assert ctx.act_results == [{"status": "ok"}]


def test_ooda_stage_next_stage_cycles():
    assert OODAStage.OBSERVE.next_stage == OODAStage.ORIENT
    assert OODAStage.ORIENT.next_stage == OODAStage.DECIDE
    assert OODAStage.DECIDE.next_stage == OODAStage.ACT
    assert OODAStage.ACT.next_stage == OODAStage.OBSERVE


# ---------------------------------------------------------------------------
# GovDOSS – KIS⁴ tag
# ---------------------------------------------------------------------------


def test_kis4_tag_is_compliant_when_all_dimensions_present():
    tag = KIS4Tag(dimensions=list(KIS4Dimension))
    assert tag.is_compliant is True


def test_kis4_tag_not_compliant_when_dimensions_missing():
    tag = KIS4Tag(dimensions=[KIS4Dimension.SIMPLE, KIS4Dimension.SECURE])
    assert tag.is_compliant is False


def test_kis4_tag_summary():
    tag = KIS4Tag(dimensions=[KIS4Dimension.SIMPLE, KIS4Dimension.SECURE])
    summary = tag.summary()
    assert "SIMPLE" in summary
    assert "SECURE" in summary


# ---------------------------------------------------------------------------
# GovDOSS – SOA⁴ audit event
# ---------------------------------------------------------------------------


def test_soa4_audit_event_creation():
    event = SOA4AuditEvent(
        subject_id="user-123",
        object_type="graph_execution",
        object_id="exec-456",
        action=SOA4Action.EXECUTE,
    )
    assert event.subject_id == "user-123"
    assert event.outcome == "success"
    assert event.required_approval is False


def test_soa4_audit_event_log_does_not_raise():
    event = SOA4AuditEvent(
        subject_id="user-abc",
        object_type="graph",
        object_id="graph-001",
        action=SOA4Action.CREATE,
        outcome="success",
    )
    # log() should not raise
    event.log()
