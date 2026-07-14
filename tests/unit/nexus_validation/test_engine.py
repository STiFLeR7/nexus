"""Unit tests for the Validation Engine — verdicts, events, determinism, persistence."""

from __future__ import annotations

from nexus_execution.signals import TerminalOutcome
from nexus_infra import InMemoryObservability, build_infrastructure
from nexus_runtime import FixedTimestampSource
from nexus_validation import ValidationEngine, build_validation
from nexus_validation.vocabulary import ValidationDecision, ValidationStage
from tests.unit.nexus_validation.helpers import (
    artifact_events,
    execution_result,
    val_work_package,
)


def _infra():  # type: ignore[no-untyped-def]
    return build_infrastructure(observability=InMemoryObservability())


def _validation_events(infra):  # type: ignore[no-untyped-def]
    return [e for e in infra.event_store.read_all() if e.type.startswith("validation.")]


# --- verdict paths ---------------------------------------------------------- #


def test_clean_corroborated_run_passes() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    report = ctx.engine.validate(
        execution_result(), val_work_package(), events=artifact_events(("a.py",))
    )
    assert report.decision is ValidationDecision.PASSED
    assert report.stage is ValidationStage.PASSED
    assert report.passed is True


def test_failed_execution_fails_validation() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    report = ctx.engine.validate(
        execution_result(outcome=TerminalOutcome.FAILED, error_class="provider-failure"),
        val_work_package(),
        events=artifact_events(("a.py",)),
    )
    assert report.decision is ValidationDecision.FAILED
    assert "validation.failed" in [e.type for e in _validation_events(infra)]


def test_completed_without_corroboration_is_partial() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    # No artifact events → no independent corroboration → Partial (INV-20 policy).
    report = ctx.engine.validate(execution_result(), val_work_package(), events=())
    assert report.decision is ValidationDecision.PARTIAL


def test_cancelled_run_requires_review() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    report = ctx.engine.validate(
        execution_result(outcome=TerminalOutcome.CANCELLED),
        val_work_package(),
        events=artifact_events(("a.py",)),
    )
    assert report.decision is ValidationDecision.REQUIRES_REVIEW


# --- events ----------------------------------------------------------------- #


def test_emits_full_validation_event_sequence() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    ctx.engine.validate(execution_result(), val_work_package(), events=artifact_events(("a.py",)))
    types = [e.type for e in _validation_events(infra)]
    assert types[0] == "validation.started"
    assert types[1] == "validation.evidence_collected"
    assert types.count("validation.rule_evaluated") == 5
    assert types[-1] == "validation.completed"


def test_terminal_event_payload_carries_decision_and_confidence() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    ctx.engine.validate(execution_result(), val_work_package(), events=artifact_events(("a.py",)))
    completed = next(e for e in _validation_events(infra) if e.type == "validation.completed")
    assert completed.payload["decision"] == "passed"
    assert completed.payload["confidence"] == 1.0


# --- determinism ------------------------------------------------------------ #


def test_two_runs_produce_identical_reports_and_events() -> None:
    infra1, infra2 = _infra(), _infra()
    ctx1 = build_validation(infra1, timestamps=FixedTimestampSource())
    ctx2 = build_validation(infra2, timestamps=FixedTimestampSource())
    events = artifact_events(("a.py",))
    r1 = ctx1.engine.validate(execution_result(), val_work_package(), events=events)
    r2 = ctx2.engine.validate(execution_result(), val_work_package(), events=events)
    assert r1 == r2
    triples1 = [(e.identifier, e.type, e.payload) for e in _validation_events(infra1)]
    triples2 = [(e.identifier, e.type, e.payload) for e in _validation_events(infra2)]
    assert triples1 == triples2


# --- persistence ------------------------------------------------------------ #


def test_report_and_evidence_are_persisted() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    report = ctx.engine.validate(
        execution_result(), val_work_package(), events=artifact_events(("a.py",))
    )
    assert ctx.repositories.reports.get(report.identity) == report
    for ref in report.evidence_refs:
        assert ctx.repositories.evidence.get(ref.identifier) is not None


def test_engine_without_repositories_still_returns_report() -> None:
    infra = _infra()
    engine = ValidationEngine(infra, timestamps=FixedTimestampSource())  # no repositories
    report = engine.validate(
        execution_result(), val_work_package(), events=artifact_events(("a.py",))
    )
    assert report.decision is ValidationDecision.PASSED


def test_report_references_evidence_and_does_not_duplicate() -> None:
    infra = _infra()
    ctx = build_validation(infra, timestamps=FixedTimestampSource())
    report = ctx.engine.validate(
        execution_result(), val_work_package(), events=artifact_events(("a.py",))
    )
    # The report carries Evidence references, not Evidence objects.
    assert all(ref.target_type == "evidence" for ref in report.evidence_refs)
    assert report.correlation_identifier != ""
