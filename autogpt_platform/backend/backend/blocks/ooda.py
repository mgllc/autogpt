"""
OODA Loop Blocks
================
Four blocks that together implement the Observe → Orient → Decide → Act (OODA)
loop pattern, following GovDOSS KIS⁴ and SOA⁴ governance principles.

Each block corresponds to one phase of the loop:

* ``OODAObserveBlock``  – aggregate raw observations.
* ``OODAOrientBlock``   – contextualise and enrich observations.
* ``OODADecideBlock``   – select the best action from oriented data.
* ``OODAActBlock``      – execute the decided action and capture the outcome.

Blocks can be chained in a graph to create a complete OODA cycle.  The
``ooda_stage`` field in ``ExecutionContext`` is set by each block so that
downstream telemetry can track loop progress.
"""

from typing import Any, Optional

from backend.blocks._base import (
    Block,
    BlockCategory,
    BlockOutput,
    BlockSchemaInput,
    BlockSchemaOutput,
)
from backend.data.model import SchemaField
from backend.executor.ooda_loop import OODAStage

# ---------------------------------------------------------------------------
# Observe Block
# ---------------------------------------------------------------------------


class OODAObserveBlock(Block):
    """
    **Observe** – the first stage of the OODA loop.

    Accepts one or more raw data inputs and emits them as structured
    observations ready for the Orient stage.  Annotates the
    ``ExecutionContext`` with ``ooda_stage = "observe"``.
    """

    class Input(BlockSchemaInput):
        data: Any = SchemaField(
            description=(
                "Raw input data to observe (any type: text, number, list, dict, …)."
            ),
            placeholder="Enter the value to observe",
        )
        source: Optional[str] = SchemaField(
            description="Optional label identifying the data source (e.g. 'sensor', 'api', 'user').",
            default=None,
        )

    class Output(BlockSchemaOutput):
        observation: Any = SchemaField(
            description="The observed data, passed unchanged to the next stage."
        )
        source: str = SchemaField(description="The labelled source of the observation.")
        ooda_stage: str = SchemaField(
            description="OODA stage tag: always 'observe' for this block."
        )

    def __init__(self):
        super().__init__(
            id="a1b2c3d4-0001-4000-8000-100000000001",
            input_schema=OODAObserveBlock.Input,
            output_schema=OODAObserveBlock.Output,
            description=(
                "OODA Observe – collect raw inputs and environmental signals. "
                "This is the first stage of the GovDOSS OODA loop."
            ),
            categories={BlockCategory.OODA, BlockCategory.LOGIC},
            test_input={
                "data": {"temperature": 72, "humidity": 55},
                "source": "weather_sensor",
            },
            test_output=[
                ("observation", {"temperature": 72, "humidity": 55}),
                ("source", "weather_sensor"),
                ("ooda_stage", OODAStage.OBSERVE.value),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        source = input_data.source or "unknown"
        yield "observation", input_data.data
        yield "source", source
        yield "ooda_stage", OODAStage.OBSERVE.value


# ---------------------------------------------------------------------------
# Orient Block
# ---------------------------------------------------------------------------


class OODAOrientBlock(Block):
    """
    **Orient** – the second stage of the OODA loop.

    Accepts an observation and user-supplied context to produce an enriched
    orientation model that drives the Decide stage.
    """

    class Input(BlockSchemaInput):
        observation: Any = SchemaField(
            description="Raw observation from the Observe stage.",
        )
        context: Optional[dict[str, Any]] = SchemaField(
            description=(
                "Optional structured context (background knowledge, prior state, "
                "environmental data) to help orient the observation."
            ),
            default=None,
        )
        label: Optional[str] = SchemaField(
            description="Short human-readable label describing the observation type.",
            default=None,
        )

    class Output(BlockSchemaOutput):
        orientation: dict[str, Any] = SchemaField(
            description=(
                "Enriched orientation model: a dict containing the observation, "
                "any supplied context, and a label."
            )
        )
        ooda_stage: str = SchemaField(
            description="OODA stage tag: always 'orient' for this block."
        )

    def __init__(self):
        super().__init__(
            id="a1b2c3d4-0002-4000-8000-100000000002",
            input_schema=OODAOrientBlock.Input,
            output_schema=OODAOrientBlock.Output,
            description=(
                "OODA Orient – contextualise observations into actionable understanding. "
                "This is the second stage of the GovDOSS OODA loop."
            ),
            categories={BlockCategory.OODA, BlockCategory.LOGIC},
            test_input={
                "observation": {"temperature": 72, "humidity": 55},
                "context": {"threshold_temp": 80, "location": "server_room"},
                "label": "environmental_check",
            },
            test_output=[
                (
                    "orientation",
                    {
                        "label": "environmental_check",
                        "observation": {"temperature": 72, "humidity": 55},
                        "context": {"threshold_temp": 80, "location": "server_room"},
                    },
                ),
                ("ooda_stage", OODAStage.ORIENT.value),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        orientation: dict[str, Any] = {
            "label": input_data.label or "observation",
            "observation": input_data.observation,
            "context": input_data.context or {},
        }
        yield "orientation", orientation
        yield "ooda_stage", OODAStage.ORIENT.value


# ---------------------------------------------------------------------------
# Decide Block
# ---------------------------------------------------------------------------


class OODADecideBlock(Block):
    """
    **Decide** – the third stage of the OODA loop.

    Evaluates an orientation model against a set of labelled options and
    selects the best match using simple rule-based logic (no LLM required).
    For AI-powered decision logic, combine this block with ``AIConditionBlock``.
    """

    class Input(BlockSchemaInput):
        orientation: dict[str, Any] = SchemaField(
            description="Orientation model produced by the Orient stage.",
        )
        options: list[str] = SchemaField(
            description=(
                "Ordered list of possible actions to choose from. "
                "The block selects the first option by default unless a "
                "``decision_key`` match is found in the orientation context."
            ),
            default=["proceed", "abort"],
        )
        decision_key: Optional[str] = SchemaField(
            description=(
                "Optional key to look up in orientation['context'] whose value "
                "determines the selected option.  If the value matches an option "
                "name the corresponding option is selected; otherwise the first "
                "option is used as a fallback."
            ),
            default=None,
        )

    class Output(BlockSchemaOutput):
        decision: str = SchemaField(
            description="The selected action / option from the provided list."
        )
        orientation: dict[str, Any] = SchemaField(
            description="The original orientation model, passed through unchanged."
        )
        ooda_stage: str = SchemaField(
            description="OODA stage tag: always 'decide' for this block."
        )

    def __init__(self):
        super().__init__(
            id="a1b2c3d4-0003-4000-8000-100000000003",
            input_schema=OODADecideBlock.Input,
            output_schema=OODADecideBlock.Output,
            description=(
                "OODA Decide – select the best next action from oriented understanding. "
                "This is the third stage of the GovDOSS OODA loop."
            ),
            categories={BlockCategory.OODA, BlockCategory.LOGIC},
            test_input={
                "orientation": {
                    "label": "environmental_check",
                    "observation": {"temperature": 72},
                    "context": {"action": "proceed"},
                },
                "options": ["proceed", "abort", "alert"],
                "decision_key": "action",
            },
            test_output=[
                ("decision", "proceed"),
                (
                    "orientation",
                    {
                        "label": "environmental_check",
                        "observation": {"temperature": 72},
                        "context": {"action": "proceed"},
                    },
                ),
                ("ooda_stage", OODAStage.DECIDE.value),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        options = input_data.options or ["proceed"]
        decision = options[0]

        if input_data.decision_key:
            ctx = input_data.orientation.get("context", {})
            candidate = str(ctx.get(input_data.decision_key, "")).strip()
            if candidate in options:
                decision = candidate

        yield "decision", decision
        yield "orientation", input_data.orientation
        yield "ooda_stage", OODAStage.DECIDE.value


# ---------------------------------------------------------------------------
# Act Block
# ---------------------------------------------------------------------------


class OODAActBlock(Block):
    """
    **Act** – the fourth and final stage of the OODA loop.

    Records the outcome of executing a decided action.  The ``action``
    input is the decision string from the Decide stage; ``result`` is
    whatever the downstream execution produced.  This block closes the
    loop by emitting ``cycle_complete = True`` so that a subsequent
    Observe block can start the next iteration.
    """

    class Input(BlockSchemaInput):
        action: str = SchemaField(
            description="The action that was executed (decision from the Decide stage).",
        )
        result: Any = SchemaField(
            description="The outcome or return value produced by executing the action.",
            default=None,
        )
        success: bool = SchemaField(
            description="Whether the action completed successfully.",
            default=True,
        )

    class Output(BlockSchemaOutput):
        action: str = SchemaField(description="The action that was recorded.")
        result: Any = SchemaField(description="The outcome of the action.")
        success: bool = SchemaField(description="Whether the action succeeded.")
        cycle_complete: bool = SchemaField(
            description=(
                "Always True – signals that one full OODA cycle has completed "
                "and a new Observe stage may begin."
            )
        )
        ooda_stage: str = SchemaField(
            description="OODA stage tag: always 'act' for this block."
        )

    def __init__(self):
        super().__init__(
            id="a1b2c3d4-0004-4000-8000-100000000004",
            input_schema=OODAActBlock.Input,
            output_schema=OODAActBlock.Output,
            description=(
                "OODA Act – execute the decided action and record its outcome. "
                "This is the fourth (final) stage of the GovDOSS OODA loop. "
                "Connect the cycle_complete output back to an Observe block to "
                "start the next iteration."
            ),
            categories={BlockCategory.OODA, BlockCategory.LOGIC},
            test_input={
                "action": "proceed",
                "result": {"status": "ok", "message": "Action executed successfully."},
                "success": True,
            },
            test_output=[
                ("action", "proceed"),
                (
                    "result",
                    {"status": "ok", "message": "Action executed successfully."},
                ),
                ("success", True),
                ("cycle_complete", True),
                ("ooda_stage", OODAStage.ACT.value),
            ],
        )

    async def run(self, input_data: Input, **kwargs) -> BlockOutput:
        yield "action", input_data.action
        yield "result", input_data.result
        yield "success", input_data.success
        yield "cycle_complete", True
        yield "ooda_stage", OODAStage.ACT.value
