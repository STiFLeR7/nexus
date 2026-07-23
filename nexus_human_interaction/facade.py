"""The Human Interaction façade (P14/B) — the first constitutional operator surface.

:class:`HumanInteraction` is a *façade*, not a UI framework: it exposes the constitutional platform and
never bypasses it. Every operation invokes **only** the :class:`~nexus_workflows.spine.ConstitutionalPipeline`
(``submit`` / ``restart`` drive it; ``status`` / ``history`` / ``execution_graph`` / ``knowledge`` /
``replay`` / ``explain_lineage`` project it) — no engine is ever called directly, and the façade owns no
reasoning. It owns exactly four things: request translation (``OperatorRequest`` → ``SpineRequest``),
response formatting, session lookup, and progress reporting, recording its own durable ``interaction.*``
facts so an operator session replays exactly and a restart resumes without replaying completed stages.
"""

from __future__ import annotations

from collections.abc import Callable

from nexus_approval import (
    ApprovalDecision,
    ApprovalExchange,
    ApprovalExplanation,
    ApprovalRequest,
)
from nexus_core.contracts.base import Struct
from nexus_core.contracts.enums import KnowledgeType
from nexus_core.domain.event import Event
from nexus_human_interaction import events as ievents
from nexus_human_interaction.model import (
    ExecutionGraphView,
    InteractionResponse,
    InteractionSession,
    InteractionStatus,
    KnowledgeView,
    LineageView,
    OperatorRequest,
)
from nexus_human_interaction.observability import OperatorObservability
from nexus_human_interaction.session import reconstruct_interaction_session
from nexus_infra import InfrastructureContext, content_hash
from nexus_workflows.spine import ConstitutionalPipeline, SpineControl, SpineRequest, SpineRun


class HumanInteraction:
    """The operator façade over the constitutional pipeline (invokes only the pipeline)."""

    def __init__(
        self,
        pipeline: ConstitutionalPipeline,
        infrastructure: InfrastructureContext,
        approval: ApprovalExchange,
        *,
        now: Callable[[], str] | None = None,
        observability: OperatorObservability | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._infra = infrastructure
        # The Approval Exchange (P15) is the sole owner of approval coordination — the façade never
        # bypasses it; its approval methods delegate here and it owns no approval logic (presentation only).
        self._approval = approval
        self._now = now or ievents.system_now
        self._obs = observability or OperatorObservability(infrastructure.observability)

    # -- drive the pipeline -------------------------------------------------- #

    def submit(
        self, request: OperatorRequest, *, control: SpineControl | None = None
    ) -> InteractionResponse:
        """Translate the operator request, drive the whole pipeline, record + format the response."""
        spine = _translate(request)
        self._emit(
            request,
            ievents.INTERACTION_SESSION_STARTED,
            {"pipeline_session": spine.pipeline_session_id, "request": request.identity},
        )
        self._emit(
            request,
            ievents.INTERACTION_REQUEST_SUBMITTED,
            {
                "request_text": request.request_text,
                "subject": request.knowledge_subject,
                "scope": request.scope,
                "work_items": [item.key for item in request.work_items],
            },
        )
        run = self._pipeline.run(spine, control=control)
        self._obs.submitted()
        return self._record(request, run, resumed=False)

    def restart(self, request: OperatorRequest) -> InteractionResponse:
        """Resume a paused/interrupted operator session — the pipeline reconstructs completed stages."""
        spine = _translate(request)
        run = self._pipeline.run(spine)  # the coordinator seeds from the log and resumes (INV-18)
        self._obs.resumed()
        self._emit(
            request,
            ievents.INTERACTION_RESUMED,
            {"reconstructed": list(run.reconstructed_stages)},
        )
        return self._record(request, run, resumed=True)

    # -- approval surface (delegates to the Approval Exchange, never bypassed) - #

    def pending_approvals(self, identity: str) -> tuple[ApprovalRequest, ...]:
        """The gates of this session still awaiting an operator decision (from the Approval Exchange)."""
        return self._approval.pending(_pipeline_session_id(identity))

    def approve(
        self, request: OperatorRequest, node: str, *, decided_by: str = "operator", reason: str = ""
    ) -> ApprovalDecision:
        """Authorize a gate — the Approval Exchange records it and resumes the paused pipeline."""
        decision = self._approval.approve(
            _translate(request), node, decided_by=decided_by, reason=reason
        )
        self._obs.resumed()
        return decision

    def deny(
        self, request: OperatorRequest, node: str, *, decided_by: str = "operator", reason: str = ""
    ) -> ApprovalDecision:
        """Deny a gate — the Approval Exchange records it; the gated node is not authorized to run."""
        return self._approval.deny(
            _pipeline_session_id(request.identity), node, decided_by=decided_by, reason=reason
        )

    def approval_explanation(self, identity: str, node: str) -> ApprovalExplanation:
        """Explain why a gate required approval and its current state (via the Approval Exchange)."""
        return self._approval.explanation(_pipeline_session_id(identity), node)

    def approval_history(self, identity: str) -> tuple[ApprovalRequest, ...]:
        """The full approval-decision history for the session (via the Approval Exchange)."""
        return self._approval.history(_pipeline_session_id(identity))

    # -- inspect the platform (read-only projections) ------------------------ #

    def status(self, identity: str) -> InteractionStatus:
        """Report the pipeline progress for a session (reconstructed from the log)."""
        session = self._pipeline.session(_pipeline_session_id(identity))
        return InteractionStatus(
            session_id=_interaction_session_id(identity),
            status=session.status.value,
            current_stage=session.current_stage,
            stages_completed=session.stages_completed,
            is_complete=session.status.value == "completed",
        )

    def session(self, identity: str) -> InteractionSession:
        """Reconstruct the operator interaction session from the ``interaction.*`` log."""
        return reconstruct_interaction_session(
            self._pipeline.history(), _interaction_session_id(identity)
        )

    def history(self, identity: str) -> tuple[Event, ...]:
        """The correlated event history for the session's run (the audit trail)."""
        pipe = _pipeline_session_id(identity)
        return tuple(
            event
            for event in self._pipeline.history()
            if event.identifier.startswith(f"evt-{pipe}-")
            or event.identifier.startswith(f"evt-{_interaction_session_id(identity)}-")
        )

    def execution_graph(self, _identity: str) -> ExecutionGraphView:
        """The frozen Execution Graph topology for the run (reconstructed; never re-planned)."""
        graph = self._pipeline.execution_graph()
        if graph is None:
            return ExecutionGraphView(nodes=(), edges=())
        return ExecutionGraphView(
            nodes=tuple(node.identifier for node in graph.nodes),
            edges=tuple((edge.source_node, edge.target_node) for edge in graph.edges),
        )

    def knowledge(
        self, *, subject: str | None = None, kind: KnowledgeType | None = None
    ) -> KnowledgeView:
        """Inspect Knowledge read-only through the pipeline (the engine is never user-callable)."""
        served = self._pipeline.inspect_knowledge(subject=subject, kind=kind)
        return KnowledgeView(
            items=tuple((item.identity, subject or "", item.type.value) for item in served)
        )

    def replay(self, identity: str) -> InteractionSession:
        """Deterministically reconstruct the operator session from the durable log (no re-execution)."""
        return self.session(identity)

    def explain_lineage(self, identity: str) -> LineageView:
        """Explain the run's execution lineage + the Knowledge that grounded it (from the log)."""
        timeline = self._pipeline.lineage()
        grounded: dict[str, object] = {}
        for event in self._pipeline.history():
            if event.type == "pipeline.knowledge_grounded":
                grounded = dict(event.payload)
        return LineageView(
            stages=tuple((stage.producer, stage.count) for stage in timeline.stages),
            total_events=timeline.total_events,
            knowledge_provenance=grounded,
        )

    # -- formatting + events ------------------------------------------------- #

    def _record(
        self, request: OperatorRequest, run: SpineRun, *, resumed: bool
    ) -> InteractionResponse:
        grounding = run.knowledge_grounding
        # If the run paused at an approval boundary, surface the request through the Approval Exchange
        # (it publishes idempotently; a run with no waiting gate is a no-op) — presentation, not logic.
        waiting = run.execution_state.waiting_nodes if run.execution_state is not None else ()
        pending = self._approval.publish(_pipeline_session_id(request.identity), waiting)
        self._emit(
            request,
            ievents.INTERACTION_RESPONSE_RECORDED,
            {
                "status": run.status.value,
                "knowledge_item_ids": list(run.knowledge_item_ids),
                "knowledge_references": list(grounding.selected_ids) if grounding else [],
                "stages_completed": list(run.pipeline_session.stages_completed),
                "reconstructed": list(run.reconstructed_stages),
                "executed": list(run.executed_stages),
                "resumed": resumed,
            },
        )
        self._obs.responded(stages=len(run.pipeline_session.stages_completed))
        return InteractionResponse(
            session_id=request.interaction_session_id,
            status=run.status.value,
            pipeline_session=run.pipeline_session,
            goal_ref=run.goal_ref,
            plan_ref=run.plan_ref,
            execution_status=run.execution_state.status.value if run.execution_state else None,
            validation_decisions=run.validation_decisions,
            knowledge_item_ids=run.knowledge_item_ids,
            knowledge_grounding=grounding,
            reconstructed_stages=run.reconstructed_stages,
            executed_stages=run.executed_stages,
            progress=run.pipeline_session.stages_completed,
            pending_approvals=pending,
        )

    def _emit(self, request: OperatorRequest, event_type: str, payload: Struct) -> None:
        session = request.interaction_session_id
        full: Struct = {"session": session, **payload}
        identifier = f"evt-{session}-{event_type.split('.')[-1]}-{content_hash(full)[:16]}"
        self._infra.emit(
            ievents.build_event(identifier, event_type, request.correlation, full, self._now())
        )


def _translate(request: OperatorRequest) -> SpineRequest:
    """Request translation — the one operator→constitutional-contract mapping (no reasoning)."""
    return SpineRequest(
        identity=request.identity,
        request_text=request.request_text,
        work_items=request.work_items,
        knowledge_subject=request.knowledge_subject,
        scope=request.scope,
        knowledge_kind=request.knowledge_kind,
        context_fragments=request.context_fragments,
        capabilities=request.capabilities,
        fail=request.fail,
        correlation_identifier=request.correlation_identifier,
    )


def _pipeline_session_id(identity: str) -> str:
    return f"pipe-{identity}"


def _interaction_session_id(identity: str) -> str:
    return f"hi-{identity}"
