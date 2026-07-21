"""P14/B — the Human Interaction surface exposes (never bypasses) the constitutional platform.

End-to-end proof that an operator drives and inspects the whole pipeline through one façade — submit,
status, execution graph, Knowledge, lineage, replay, restart — with durable replay + restart, and that
the learning loop reaches the operator (Goal → Knowledge → next Goal through the surface).
"""

from __future__ import annotations

from nexus_core.contracts.enums import KnowledgeType
from nexus_human_interaction import build_human_interaction, reference_operator_request
from nexus_infra import build_durable_infrastructure, build_infrastructure
from nexus_workflows.spine import SpineControl, SpineStage


def test_operator_submits_and_reaches_knowledge() -> None:
    facade = build_human_interaction(build_infrastructure()).facade
    response = facade.submit(reference_operator_request(run="r1"))
    assert response.succeeded and response.status == "completed"
    assert response.knowledge_item_ids
    # Every operation went through the pipeline; inspection projects it.
    assert facade.status("op-arch-r1").is_complete
    assert facade.execution_graph("op-arch-r1").nodes == ("node-draft", "node-review")
    assert facade.knowledge(kind=KnowledgeType.LESSON).items


def test_operator_flow_is_deterministic() -> None:
    def once():
        facade = build_human_interaction(build_infrastructure()).facade
        facade.submit(reference_operator_request(run="r1"))
        return [(e.identifier, e.type, e.payload) for e in facade.history("op-arch-r1")]

    assert once() == once()  # byte-identical operator + pipeline event stream across runs


def test_interaction_replays_from_the_durable_log(tmp_path) -> None:
    db = str(tmp_path / "hi.db")
    build_human_interaction(build_durable_infrastructure(db)).facade.submit(
        reference_operator_request(run="r1")
    )
    # A fresh façade over the reopened file reconstructs the operator session exactly.
    replayed = build_human_interaction(build_durable_infrastructure(db)).facade.replay("op-arch-r1")
    assert replayed.submitted and replayed.responded
    assert replayed.status == "completed"
    assert replayed.pipeline_session_ref.identifier == "pipe-op-arch-r1"


def test_restart_resumes_without_replaying_completed_stages(tmp_path) -> None:
    db = str(tmp_path / "restart.db")
    request = reference_operator_request(run="r1")

    paused = build_human_interaction(build_durable_infrastructure(db)).facade.submit(
        request, control=SpineControl(stop_after_stage=SpineStage.ACTUATION)
    )
    assert paused.status == "paused"

    resumed = build_human_interaction(build_durable_infrastructure(db)).facade.restart(request)
    assert resumed.status == "completed" and resumed.succeeded
    # The completed constitutional stages are reconstructed — not replayed (INV-18).
    assert resumed.reconstructed_stages == (
        SpineStage.INTENT.value,
        SpineStage.ENGINEERING.value,
        SpineStage.CONTEXT.value,
        SpineStage.PLANNING.value,
        SpineStage.ACTUATION.value,
    )
    assert resumed.executed_stages == (
        SpineStage.VALIDATION.value,
        SpineStage.RECOVERY.value,
        SpineStage.REFLECTION.value,
        SpineStage.KNOWLEDGE.value,
    )


def test_learning_loop_reaches_the_operator_surface() -> None:
    # Goal → Knowledge → next Goal, through the operator façade.
    first = build_human_interaction(build_infrastructure())
    r1 = first.facade.submit(reference_operator_request(run="r1"))
    assert r1.knowledge_grounding is not None and r1.knowledge_grounding.consumed == 0

    second = build_human_interaction(
        build_infrastructure(), knowledge_repositories=first.spine.pipeline.knowledge.repositories
    )
    r2 = second.facade.submit(reference_operator_request(run="r2"))
    assert r2.knowledge_grounding is not None and r2.knowledge_grounding.consumed >= 1
    # The operator can inspect the provenance of what grounded the run.
    lineage = second.facade.explain_lineage("op-arch-r2")
    assert lineage.knowledge_provenance.get("count") == r2.knowledge_grounding.consumed
