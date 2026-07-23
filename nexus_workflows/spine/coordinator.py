"""The Constitutional Pipeline — one deterministic Goal→Knowledge driver (P13/F-1, F-2, F-3).

:class:`ConstitutionalPipeline` is the single spine coordinator. It invokes each constitutional owner
**exactly once**, in dependency order, passing only constitutional contracts::

    Intent → Engineering → Context → Planning → Execution Actuation → [Execution→Validation seam]
        → Validation → Recovery → Reflection → Knowledge

It contains **no business logic** and owns none of the owners' behavior — it reasons/estimates/plans/
traverses/validates/recovers/reflects/learns through nobody's internals. Its only durable facts are the
additive ``pipeline.*`` events; every owner records its own facts on the same shared log unchanged.

Durability + restart (F-2) ride that shared log (ADR-007; INV-13/14/18). The pipeline's restart
checkpoints are the four owner-embedded artifacts on the log — the resolved **Goal** (``intent.resolved``),
the **EngineeringStrategy** (``engineering.strategized``), the **ExecutionPlan**
(``planning.execution_plan_assembled``), and the **ExecutionState** (``execution.completed``). On restart
the coordinator reconstructs each from the log (never re-invoking its owner) and resumes at the first
constitutional boundary not yet on the log; the Execution Actuator itself resumes node-level from the same
log if execution was interrupted mid-flight. Context Engineering is checkpointed jointly with Planning —
its ContextPackage is a transient, deterministic input consumed only by Planning and superseded by the
log-embedded ExecutionPlan, so it is never persisted as a second copy of another owner's artifact.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from nexus_context import ContextRequest, context_reference
from nexus_context.grounding import GroundedContextEngineeringContext, GroundingInputs
from nexus_core.contracts.base import Reference, Struct
from nexus_core.contracts.enums import ConfidenceLadder, KnowledgeType
from nexus_core.domain.context_package import ContextPackage
from nexus_core.domain.event import Event
from nexus_core.domain.execution_graph import ExecutionGraph
from nexus_core.domain.goal import Goal
from nexus_core.domain.knowledge import Knowledge
from nexus_engineering import ENGINEERING_STRATEGIZED, EngineeringContext
from nexus_engineering.model import EngineeringStrategy
from nexus_estimation.composition import EstimationContext
from nexus_execution.actuation import (
    EXECUTION_COMPLETED,
    ActuationInputs,
    ActuationStatus,
    ExecutionState,
    build_execution_actuation,
)
from nexus_execution.adapter import RuntimeAdapter
from nexus_execution.results import ExecutionResult
from nexus_infra import InfrastructureContext, NullObservability, Observability, content_hash
from nexus_intent.composition import IntentContext
from nexus_intent.events import INTENT_RESOLVED
from nexus_intent.model import IntentAnalysis, request_from_text
from nexus_knowledge import KnowledgeCandidate, KnowledgeContextBundle, KnowledgeQuery
from nexus_planning.grounded import ExecutionPlan, GroundedPlanningContext, PlanningInputs
from nexus_planning.grounded.assembler import PLANNING_EXECUTION_PLAN_ASSEMBLED
from nexus_policy.composition import PolicyContext
from nexus_recovery import RecoveryContextBundle
from nexus_recovery.plan import RecoveryPlan
from nexus_reflection import ReflectionContextBundle
from nexus_reflection.report import ReflectionReport
from nexus_runtime.events import SystemTimestampSource, TimestampSource
from nexus_validation import ValidationContext
from nexus_validation.report import ValidationReport
from nexus_workflows.executor import ReplayTimeline, reconstruct
from nexus_workflows.spine import events as pevents
from nexus_workflows.spine.bridge import execution_results
from nexus_workflows.spine.learning import KnowledgeSelection, KnowledgeSelector
from nexus_workflows.spine.model import (
    ORDERED_STAGES,
    PipelineSession,
    SpineControl,
    SpineRequest,
    SpineRun,
    SpineStage,
    SpineStatus,
)

_VALIDATION_TARGET_TYPE = "validation_report"

AdapterFactory = Callable[[SpineRequest], RuntimeAdapter]

# Learning disabled (no selector) → an empty grounding selection, i.e. the P13 behavior unchanged.
_EMPTY_SELECTION = KnowledgeSelection(
    subject="",
    kind="",
    governed=False,
    decision="",
    reasoning=(),
    references=(),
    selected_ids=(),
    items=(),
)


# --------------------------------------------------------------------------- #
# Replay integration — reconstruct owner artifacts + the pipeline session         #
# from the shared durable log alone (INV-13/14; no owner re-invoked).             #
# --------------------------------------------------------------------------- #


def find_goal(events: tuple[Event, ...]) -> Goal | None:
    """Reconstruct the resolved Goal from ``intent.resolved`` (no re-understanding — INV-17)."""
    for event in events:
        if event.type == INTENT_RESOLVED:
            return IntentAnalysis.model_validate(event.payload["analysis"]).goal
    return None


def find_strategy(events: tuple[Event, ...]) -> EngineeringStrategy | None:
    """Reconstruct the EngineeringStrategy from ``engineering.strategized`` (no re-inference)."""
    for event in events:
        if event.type == ENGINEERING_STRATEGIZED:
            return EngineeringStrategy.model_validate(event.payload["strategy"])
    return None


def find_plan(events: tuple[Event, ...]) -> ExecutionPlan | None:
    """Reconstruct the ExecutionPlan from ``planning.execution_plan_assembled`` (no re-planning)."""
    for event in events:
        if event.type == PLANNING_EXECUTION_PLAN_ASSEMBLED:
            return ExecutionPlan.model_validate(event.payload["execution_plan"])
    return None


def find_execution_state(events: tuple[Event, ...]) -> ExecutionState | None:
    """Reconstruct the terminal ExecutionState from ``execution.completed`` (no re-execution)."""
    for event in events:
        if event.type == EXECUTION_COMPLETED:
            return ExecutionState.model_validate(event.payload["execution_state"])
    return None


# --------------------------------------------------------------------------- #
# RC2 — goal-scoped restart reconstruction (``_seed``'s own finders)               #
# --------------------------------------------------------------------------- #
#
# ``find_goal``/``find_strategy``/``find_plan``/``find_execution_state`` above return the *first*
# matching fact anywhere in ``events`` — correct only when the log holds exactly one goal. ``_seed``
# scans the *entire* durable log (every goal ever run on this infra), so it must instead find the fact
# that belongs to the request it is actually resuming — matched via each artifact's own goal-reference
# field (never inferred from log position). ``correlation_identifier`` is not a safe key for this: the
# Scheduler deliberately reuses one correlation across every occurrence of a recurring schedule, so two
# genuinely different goal runs (occurrence 0 and occurrence 1) would otherwise look like the same run.


def _own_goal_identity(request: SpineRequest) -> str:
    """The Goal identity Intent Resolution derives for ``request`` (``nexus_intent`` interpreter)."""
    return f"goal-{request.identity}"


def _find_own_goal(events: tuple[Event, ...], goal_identity: str) -> Goal | None:
    for event in events:
        if event.type == INTENT_RESOLVED and event.payload.get("goal") == goal_identity:
            return IntentAnalysis.model_validate(event.payload["analysis"]).goal
    return None


def _find_own_strategy(events: tuple[Event, ...], goal_identity: str) -> EngineeringStrategy | None:
    for event in events:
        if event.type != ENGINEERING_STRATEGIZED:
            continue
        strategy = EngineeringStrategy.model_validate(event.payload["strategy"])
        if strategy.subject_identifier == goal_identity:
            return strategy
    return None


def _find_own_plan(events: tuple[Event, ...], goal_identity: str) -> ExecutionPlan | None:
    for event in events:
        if event.type != PLANNING_EXECUTION_PLAN_ASSEMBLED:
            continue
        plan = ExecutionPlan.model_validate(event.payload["execution_plan"])
        if plan.plan.parent_goal.identifier == goal_identity:
            return plan
    return None


def _find_own_execution_state(
    events: tuple[Event, ...], goal_identity: str
) -> ExecutionState | None:
    for event in events:
        if event.type != EXECUTION_COMPLETED:
            continue
        state = ExecutionState.model_validate(event.payload["execution_state"])
        if state.goal_ref.identifier == goal_identity:
            return state
    return None


def reconstruct_pipeline_session(events: tuple[Event, ...], session_id: str) -> PipelineSession:
    """Rebuild the pipeline session from the ``pipeline.*`` stream (the log is truth — INV-13/14)."""
    prefix = f"evt-{session_id}-"
    completed: list[str] = []
    artifacts: list[tuple[str, str]] = []
    current: str | None = None
    status = SpineStatus.RUNNING
    for event in events:
        if event.producer != pevents.PIPELINE_PRODUCER or not event.identifier.startswith(prefix):
            continue
        if event.type == pevents.PIPELINE_STAGE_STARTED:
            current = str(event.payload.get("stage"))
        elif event.type == pevents.PIPELINE_STAGE_COMPLETED:
            stage = str(event.payload.get("stage"))
            current = stage
            if stage not in completed:
                completed.append(stage)
                artifacts.append((stage, str(event.payload.get("artifact", ""))))
        elif event.type == pevents.PIPELINE_COMPLETED:
            status = SpineStatus.COMPLETED
        elif event.type == pevents.PIPELINE_PAUSED and status is not SpineStatus.COMPLETED:
            status = SpineStatus.PAUSED
    return PipelineSession(
        identity=session_id,
        request_ref=Reference(target_type="spine_request", identifier=session_id),
        status=status,
        current_stage=current,
        stages_completed=tuple(completed),
        stage_artifacts=tuple(artifacts),
        lineage=tuple(completed),
    )


# --------------------------------------------------------------------------- #
# Observability — pipeline-level metadata (instrumentation only, INV-11).         #
# --------------------------------------------------------------------------- #


class PipelineObservability:
    """Pipeline-level counters over the P1 sink (derived convenience, never authoritative)."""

    def __init__(self, observability: Observability | None = None) -> None:
        self._obs: Observability = observability or NullObservability()

    def stage(self, stage: SpineStage) -> None:
        self._obs.increment("pipeline.stage_completed")

    def resumed(self, stage: SpineStage) -> None:
        self._obs.increment("pipeline.resumed")

    def completed(self, stages: int) -> None:
        self._obs.observe("pipeline.stages_completed", float(stages))


# --------------------------------------------------------------------------- #
# The coordinator                                                                 #
# --------------------------------------------------------------------------- #


@dataclass
class _RunCtx:
    """Mutable per-run accumulators — the artifacts threaded between constitutional stages."""

    goal: Goal | None = None
    strategy: EngineeringStrategy | None = None
    knowledge_selection: KnowledgeSelection | None = None
    context_package: ContextPackage | None = None
    plan: ExecutionPlan | None = None
    execution_state: ExecutionState | None = None
    execution_results: tuple[ExecutionResult, ...] = ()
    validation_reports: list[ValidationReport] = field(default_factory=list)
    recovery_plans: list[RecoveryPlan] = field(default_factory=list)
    reflection: ReflectionReport | None = None
    knowledge_item_ids: tuple[str, ...] = ()
    goal_ref: Reference | None = None
    strategy_ref: Reference | None = None
    context_ref: Reference | None = None
    plan_ref: Reference | None = None


class ConstitutionalPipeline:
    """Drives every constitutional owner once, in order, over one shared (durable) log."""

    def __init__(
        self,
        infrastructure: InfrastructureContext,
        *,
        intent: IntentContext,
        engineering: EngineeringContext,
        estimation: EstimationContext,
        policy: PolicyContext,
        grounded_context: GroundedContextEngineeringContext,
        planning: GroundedPlanningContext,
        validation: ValidationContext,
        recovery: RecoveryContextBundle,
        reflection: ReflectionContextBundle,
        knowledge: KnowledgeContextBundle,
        adapter_factory: AdapterFactory,
        selector: KnowledgeSelector | None = None,
        timestamps: TimestampSource | None = None,
        now: Callable[[], str] | None = None,
        observability: PipelineObservability | None = None,
    ) -> None:
        self._infra = infrastructure
        self._intent = intent
        self._engineering = engineering
        self._estimation = estimation
        self._policy = policy
        self._grounded_context = grounded_context
        self._planning = planning
        self._validation = validation
        self._recovery = recovery
        self._reflection = reflection
        self._knowledge = knowledge
        self._adapter_factory = adapter_factory
        # The learning integration (P14/A) — optional: absent → no Knowledge grounding (P13 behavior).
        self._selector = selector
        self._timestamps = timestamps or SystemTimestampSource()
        self._now = now or self._timestamps.now
        self._obs = observability or PipelineObservability(infrastructure.observability)

    # -- public entry point -------------------------------------------------- #

    def run(self, request: SpineRequest, *, control: SpineControl | None = None) -> SpineRun:
        """Drive (or resume) the whole Goal→Knowledge pipeline; return the immutable outcome."""
        control = control or SpineControl()
        ctx = _RunCtx()
        prior = tuple(self._infra.event_store.read_all())
        resume = self._seed(prior, ctx, request)  # reconstruct completed boundaries from the log
        reconstructed = tuple(stage.value for stage in ORDERED_STAGES if _idx(stage) < _idx(resume))
        self._announce(request, resume, reconstructed)

        executed: list[str] = []
        status = SpineStatus.COMPLETED
        for stage in ORDERED_STAGES:
            if _idx(stage) < _idx(resume):
                continue
            self._emit(request, pevents.PIPELINE_STAGE_STARTED, {"stage": stage.value})
            completed, ref = self._run_stage(stage, ctx, request, control)
            executed.append(stage.value)
            if not completed:  # execution actuation stopped before completing (resumable)
                self._emit(
                    request,
                    pevents.PIPELINE_PAUSED,
                    {"stage": stage.value, "reason": "actuation_incomplete"},
                )
                status = SpineStatus.PAUSED
                break
            self._emit(
                request,
                pevents.PIPELINE_STAGE_COMPLETED,
                {"stage": stage.value, "artifact": ref.identifier if ref else ""},
            )
            self._obs.stage(stage)
            if control.stop_after_stage is stage:
                self._emit(
                    request,
                    pevents.PIPELINE_PAUSED,
                    {"stage": stage.value, "reason": "control"},
                )
                status = SpineStatus.PAUSED
                break

        if status is SpineStatus.COMPLETED:
            self._emit(
                request,
                pevents.PIPELINE_COMPLETED,
                {"stages": [stage.value for stage in ORDERED_STAGES]},
            )
            self._obs.completed(len(ORDERED_STAGES))

        events = tuple(self._infra.event_store.read_all())
        session = reconstruct_pipeline_session(events, request.pipeline_session_id)
        return self._build_run(ctx, session, status, reconstructed, tuple(executed), events)

    # -- read-only inspection surface (the pipeline is the single entry point) - #
    #
    # The Human Interaction layer (P14/B) invokes ONLY the pipeline — never an engine directly. These
    # methods project the shared log (deterministic reconstruction, no re-execution) and delegate the
    # one Knowledge read to its sole owner; the pipeline never becomes a bypass.

    def history(self) -> tuple[Event, ...]:
        """The full event history on the shared log (the audit trail)."""
        return tuple(self._infra.event_store.read_all())

    def session(self, session_id: str) -> PipelineSession:
        """Reconstruct one pipeline session's stage progression from the log (INV-13/14)."""
        return reconstruct_pipeline_session(self.history(), session_id)

    def lineage(self) -> ReplayTimeline:
        """Reconstruct the execution lineage (one producer run per contiguous stage) from the log."""
        return reconstruct(self.history())

    def execution_graph(self) -> ExecutionGraph | None:
        """The frozen Execution Graph for the run, reconstructed from ``planning.*`` (no re-planning)."""
        plan = find_plan(self.history())
        return plan.execution_graph if plan is not None else None

    def execution_state(self) -> ExecutionState | None:
        """The terminal ExecutionState, reconstructed from ``execution.completed`` (no re-execution)."""
        return find_execution_state(self.history())

    def inspect_knowledge(
        self, *, subject: str | None = None, kind: KnowledgeType | None = None
    ) -> tuple[Knowledge, ...]:
        """Read Knowledge through its sole owner (read-only serve — the engine is never user-callable)."""
        return self._knowledge.engine.serve(KnowledgeQuery(subject=subject, kind=kind))

    # -- restart seeding (reconstruct completed boundaries from the log) ------ #

    def _seed(self, events: tuple[Event, ...], ctx: _RunCtx, request: SpineRequest) -> SpineStage:
        """Fill ``ctx`` with *this request's own* log-embedded artifacts; return the first stage to (re)run.

        ``events`` is the entire durable log (every goal ever run on this infra), so each artifact is
        matched to ``request``'s own goal identity (RC2's ``_find_own_*`` — see the note above them),
        not merely the first fact of its type. Without this, a second goal run on the same log would
        seed from the *first* goal's Goal/Plan/ExecutionState found in the log and silently skip
        straight to Validation on someone else's execution, never running its own Intent→Actuation.
        """
        goal_identity = _own_goal_identity(request)
        goal = _find_own_goal(events, goal_identity)
        strategy = _find_own_strategy(events, goal_identity)
        plan = _find_own_plan(events, goal_identity)
        state = _find_own_execution_state(events, goal_identity)
        if goal is not None:
            ctx.goal, ctx.goal_ref = goal, Reference(target_type="goal", identifier=goal.identity)
        if strategy is not None:
            ctx.strategy = strategy
            ctx.strategy_ref = Reference(
                target_type="engineering_strategy", identifier=strategy.identity
            )
        if plan is not None:
            ctx.plan = plan
            ctx.plan_ref = Reference(target_type="plan", identifier=plan.plan.identity)
            if plan.context_references:
                ctx.context_ref = plan.context_references[0]
        if state is not None:
            ctx.execution_state = state
        if state is not None:
            return SpineStage.VALIDATION
        if plan is not None:
            return SpineStage.ACTUATION
        if strategy is not None:
            return SpineStage.CONTEXT
        if goal is not None:
            return SpineStage.ENGINEERING
        return SpineStage.INTENT

    def _announce(
        self, request: SpineRequest, resume: SpineStage, reconstructed: tuple[str, ...]
    ) -> None:
        if reconstructed:  # a restart — prior boundaries reconstructed, owners not re-invoked
            self._emit(request, pevents.PIPELINE_RESUMED, {"from_stage": resume.value})
            self._obs.resumed(resume)
        else:
            self._emit(
                request,
                pevents.PIPELINE_STARTED,
                {"request": request.identity, "stages": [s.value for s in ORDERED_STAGES]},
            )

    # -- stage dispatch ------------------------------------------------------ #

    def _run_stage(
        self, stage: SpineStage, ctx: _RunCtx, request: SpineRequest, control: SpineControl
    ) -> tuple[bool, Reference | None]:
        match stage:
            case SpineStage.INTENT:
                return self._stage_intent(ctx, request, control)
            case SpineStage.ENGINEERING:
                return self._stage_engineering(ctx, request, control)
            case SpineStage.CONTEXT:
                return self._stage_context(ctx, request, control)
            case SpineStage.PLANNING:
                return self._stage_planning(ctx, request, control)
            case SpineStage.ACTUATION:
                return self._stage_actuation(ctx, request, control)
            case SpineStage.VALIDATION:
                return self._stage_validation(ctx, request, control)
            case SpineStage.RECOVERY:
                return self._stage_recovery(ctx, request, control)
            case SpineStage.REFLECTION:
                return self._stage_reflection(ctx, request, control)
            case SpineStage.KNOWLEDGE:
                return self._stage_knowledge(ctx, request, control)

    def _stage_intent(
        self, ctx: _RunCtx, request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        analysis = self._intent.engine.resolve(
            request_from_text(
                request.identity, request.request_text, correlation_identifier=request.correlation
            )
        )
        goal = analysis.goal
        assert goal is not None, "Intent did not resolve a Goal"  # trust boundary — cannot proceed
        ctx.goal = goal
        ctx.goal_ref = Reference(target_type="goal", identifier=goal.identity)
        return True, ctx.goal_ref

    def _stage_engineering(
        self, ctx: _RunCtx, request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        assert ctx.goal is not None
        grounding = self._grounding(
            ctx, request
        )  # Knowledge → Engineering (P14/A; INV-26 indirect)
        strategy = self._engineering.strategize_for_goal(
            ctx.goal,
            estimation_engine=self._estimation.engine,
            policy_engine=self._policy.engine,
            knowledge=grounding.items,
        )
        ctx.strategy = strategy
        ctx.strategy_ref = Reference(
            target_type="engineering_strategy", identifier=strategy.identity
        )
        return True, ctx.strategy_ref

    def _stage_context(
        self, ctx: _RunCtx, request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        assert ctx.goal is not None
        grounding = self._grounding(
            ctx, request
        )  # Knowledge → Context (INV-06, read-only, provenance)
        result = self._grounded_context.assembler.assemble(
            GroundingInputs(
                goal=ctx.goal,
                engineering_strategy=ctx.strategy,
                knowledge=grounding.items,
            ),
            ContextRequest(
                fragments=request.context_fragments,
                correlation_identifier=request.correlation_identifier or None,
            ),
        ).result
        ctx.context_package = result.package
        ctx.context_ref = context_reference(result.package)
        return True, ctx.context_ref

    def _grounding(self, ctx: _RunCtx, request: SpineRequest) -> KnowledgeSelection:
        """Select governed prior Knowledge once per run (deterministic); record references-only provenance.

        Lazy + cached so both Engineering and Context consume the *same* selection, and a restart that
        resumes at Context (Engineering reconstructed) still grounds. With no selector wired, learning is
        off — an empty selection (the P13 behavior).
        """
        if ctx.knowledge_selection is not None:
            return ctx.knowledge_selection
        assert ctx.goal is not None
        if self._selector is None:
            ctx.knowledge_selection = _EMPTY_SELECTION
            return ctx.knowledge_selection
        selection = self._selector.select(
            goal=ctx.goal,
            subject=request.knowledge_subject,
            kind=request.knowledge_kind,
            correlation=request.correlation,
        )
        ctx.knowledge_selection = selection
        self._emit(request, pevents.PIPELINE_KNOWLEDGE_GROUNDED, selection.provenance())
        return selection

    def _stage_planning(
        self, ctx: _RunCtx, request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        assert ctx.goal is not None
        plan = self._planning.planner.plan(
            PlanningInputs(
                goal=ctx.goal,
                engineering_strategy=ctx.strategy,
                context_package=ctx.context_package,
                work_items=request.work_items,
            )
        )
        ctx.plan = plan
        ctx.plan_ref = Reference(target_type="plan", identifier=plan.plan.identity)
        return True, ctx.plan_ref

    def _stage_actuation(
        self, ctx: _RunCtx, request: SpineRequest, control: SpineControl
    ) -> tuple[bool, Reference | None]:
        actuation = build_execution_actuation(
            self._infra, adapter=self._adapter_factory(request), timestamps=self._timestamps
        )
        plan = ctx.plan
        assert plan is not None
        state = actuation.actuator.actuate(
            ActuationInputs(
                plan=plan.plan,
                execution_graph=plan.execution_graph,
                execution_strategy=plan.execution_strategy,
                work_packages=plan.work_packages,
                context_references=plan.context_references,
                granted_gates=control.granted_gates,  # P15: gates the Approval Exchange authorized
            ),
            control=control.actuation,
        )
        ctx.execution_state = state
        ref = Reference(target_type="execution_state", identifier=state.identity)
        # PAUSED = a resumable interruption (cancel/shutdown). BLOCKED with nodes still WAITING on an
        # ungranted approval is the P15 approval boundary — also resumable, so pause the pipeline and let
        # the Approval Exchange coordinate the decision (Actuation still owns the pause/resume, INV-23).
        # A COMPLETED run, or one BLOCKED purely by a failure, is terminal → hand on to Validation.
        paused = state.status is ActuationStatus.PAUSED or (
            state.status is ActuationStatus.BLOCKED and bool(state.waiting_nodes)
        )
        return not paused, ref

    def _stage_validation(
        self, ctx: _RunCtx, _request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        assert ctx.execution_state is not None and ctx.plan is not None
        events = tuple(self._infra.event_store.read_all())
        results = execution_results(ctx.execution_state, events)  # the F-3 seam
        ctx.execution_results = results
        wp_by_ref = {wp.identifier: wp for wp in ctx.plan.work_packages}
        reports = [
            self._validation.engine.validate(
                result, wp_by_ref[result.work_package_ref.identifier], events=events
            )
            for result in results
        ]
        ctx.validation_reports = reports
        ref = (
            Reference(target_type=_VALIDATION_TARGET_TYPE, identifier=reports[0].identity)
            if reports
            else None
        )
        return True, ref

    def _stage_recovery(
        self, ctx: _RunCtx, _request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        events = tuple(self._infra.event_store.read_all())
        ctx.recovery_plans = [
            self._recovery.engine.recover(report, result, events=events)
            for report, result in zip(ctx.validation_reports, ctx.execution_results, strict=True)
        ]
        return True, None

    def _stage_reflection(
        self, ctx: _RunCtx, request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        events = tuple(self._infra.event_store.read_all())
        report = self._reflection.engine.reflect(
            request.scope,
            execution_results=tuple(ctx.execution_results),
            validation_reports=tuple(ctx.validation_reports),
            recovery_plans=tuple(ctx.recovery_plans),
            events=events,
        )
        ctx.reflection = report
        return True, report.reference()

    def _stage_knowledge(
        self, ctx: _RunCtx, request: SpineRequest, _control: SpineControl
    ) -> tuple[bool, Reference | None]:
        assert ctx.reflection is not None
        ctx.knowledge_item_ids = self._write_knowledge(
            request, ctx.reflection, ctx.validation_reports
        )
        ref = (
            Reference(target_type="knowledge", identifier=ctx.knowledge_item_ids[0])
            if ctx.knowledge_item_ids
            else None
        )
        return True, ref

    def _write_knowledge(
        self,
        request: SpineRequest,
        reflection: ReflectionReport,
        reports: list[ValidationReport],
    ) -> tuple[str, ...]:
        evidence = tuple(
            Reference(target_type=_VALIDATION_TARGET_TYPE, identifier=r.identity) for r in reports
        )
        items: list[str] = []
        for advisory in reflection.knowledge_candidates:
            candidate = KnowledgeCandidate(
                identity=advisory.identity,
                kind=request.knowledge_kind,
                subject=request.knowledge_subject,
                statement=advisory.summary,
                confidence=ConfidenceLadder.OBSERVED,
                evidence_refs=evidence,
                originating_reflection_ref=reflection.reference(),
                source_pattern_ref=advisory.source_pattern_ref,
                correlation_identifier=reflection.correlation_identifier,
            )
            outcome = self._knowledge.engine.ingest(candidate)
            if outcome.item is not None:
                items.append(outcome.item.identity)
        return tuple(items)

    # -- outcome + events ---------------------------------------------------- #

    def _build_run(
        self,
        ctx: _RunCtx,
        session: PipelineSession,
        status: SpineStatus,
        reconstructed: tuple[str, ...],
        executed: tuple[str, ...],
        events: tuple[Event, ...],
    ) -> SpineRun:
        return SpineRun(
            pipeline_session=session,
            status=status,
            goal_ref=ctx.goal_ref,
            strategy_ref=ctx.strategy_ref,
            context_ref=ctx.context_ref,
            plan_ref=ctx.plan_ref,
            execution_state=ctx.execution_state,
            execution_outcomes=tuple(r.outcome.value for r in ctx.execution_results),
            validation_decisions=tuple(rep.decision.value for rep in ctx.validation_reports),
            recovery_decisions=tuple(pl.decision.value for pl in ctx.recovery_plans),
            reflection_ref=ctx.reflection.reference() if ctx.reflection is not None else None,
            knowledge_item_ids=ctx.knowledge_item_ids,
            knowledge_grounding=ctx.knowledge_selection,
            reconstructed_stages=reconstructed,
            executed_stages=executed,
            events=events,
        )

    def _emit(self, request: SpineRequest, event_type: str, payload: Struct) -> None:
        session = request.pipeline_session_id
        full: Struct = {"session": session, **payload}
        identifier = f"evt-{session}-{event_type.split('.')[-1]}-{content_hash(full)[:16]}"
        self._infra.emit(
            pevents.build_event(identifier, event_type, request.correlation, full, self._now())
        )


def _idx(stage: SpineStage) -> int:
    return ORDERED_STAGES.index(stage)
