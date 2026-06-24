# H-2 — Implementation Plan (Track H, v1.1.0)

> **Design only — a plan, not implementation.** The gated, minimal-diff sequence to deliver the six P0
> items (Prototype → **Experimental**), and where the P1/P2 work lands afterward. No code is written or
> committed here. Execution begins only on explicit approval. Grounded at commit `b734c13`.

---

## 1. Scope of this plan

- **In H-2 (the next implementation AP, when authorized):** the **six P0 gaps** →
  Hermes **Experimental**. (`H-2-gap-prioritization.md` §2.)
- **Designed, deferred to later gated APs:** P1 (terminate, resume, fail-fast init, budget/TIMED_OUT) →
  H-4; P2 → future. R-05 file-confinement **floor is already done (S-4)**.
- **Branch:** `v1.1.0-planning` (continues). **Method:** strict TDD, minimal diff, no opportunistic
  refactoring. **No migrations.**

## 2. Sequenced steps (dependency-ordered, each RED→GREEN→regression)

> Order honors the dependency graph: the injection **seams** must precede the **mock-branch removal** so
> the existing tests never go uncovered.

### Step H-2.1 — Tool-call contract & structured parsing (P0-2)
- Add a small `ToolCall`/`ToolResult` contract (new `hermes_tools.py`, additive) + a strict validator in
  the decision path; malformed → explicit error `ToolResult` (no silent `finish`).
- **RED:** `test_structured_toolcall_parsed`, `test_malformed_toolcall_is_error_not_finish`.
- **Touches:** `hermes.py` (decision section `hermes.py:224-246`), new `hermes_tools.py`.
- **No mock removal yet** — both branches still present.

### Step H-2.2 — `SearchProvider` port + test double (P0-5, seam half)
- Add `SearchProvider` protocol (new `search_provider.py`) + constructor injection
  (`hermes.py:29-42`, additive param, default `None`); `web_search` calls the port; canned text moves to
  a `FakeSearchProvider` in tests.
- **RED:** `test_web_search_calls_provider`, `test_no_canned_search_in_runtime`,
  `test_search_egress_respects_policy`.
- **Touches:** `hermes.py` (`__init__`, `_execute_tool` web_search), new `search_provider.py`,
  `test_hermes.py`.

### Step H-2.3 — Remove `AsyncMock` + `is_mocked` branch (P0-1)
- Delete `hermes.py:7` import and `hermes.py:198-223` branch; keep only the real-model branch.
- Migrate the 4 existing `test_hermes.py` tests to inject `FakeLLMClient` + `FakeSearchProvider`.
- **RED:** `test_no_mock_import_in_runtime`, `test_real_branch_drives_loop` (+ migrated tests).
- **Touches:** `hermes.py`, `test_hermes.py`. **Depends on:** H-2.1, H-2.2 (seams exist).

### Step H-2.4 — Goal-derived planning (P0-3)
- Replace the literal (`hermes.py:159-163`) with a model-derived advisory plan; persist as existing
  `agent_plan` artifact.
- **RED:** `test_plan_derived_from_goal`, `test_no_hardcoded_plan_literal`.
- **Touches:** `hermes.py` (`execute_goal` plan formulation).

### Step H-2.5 — Real exit-status fidelity (P0-4)
- Derive `exit_code`/status from real loop outcome; failed steps persist non-COMPLETED status; fix
  summary artifact `exit_code` (`hermes.py:385`). Replace swallow-as-finished (`hermes.py:254-259`) with
  a real FAILED transition.
- **RED:** `test_failure_yields_nonzero_exit`, `test_failed_step_status_truthful`,
  `test_success_yields_zero`.
- **Touches:** `hermes.py` (`execute_goal` return + step status). **Orchestrator untouched**
  (already maps exit_code→status).

### Step H-2.6 — Real-branch coverage consolidation (P0-6)
- Ensure the matrix in `H-2-test-strategy.md` §4 is fully covered; add the honesty **guard tests**.
- **Touches:** `test_hermes.py` / new test module only.

### Step H-2.7 — Verification & closure
- Full suite (target ≥ 178 + new), `ruff`, `mypy` all green; write H-2 implementation + validation
  reports; reclassify Caps 2/3/4/8/18 with evidence. **Stop; do not commit unless instructed.**

## 3. Files touched (whole H-2, P0 only)

| File | Nature | Notes |
|---|---|---|
| `nexus/execution/runners/hermes.py` | modify | mock removal, structured parse, plan, exit status, search call |
| `nexus/execution/runners/hermes_tools.py` | **new** | `ToolCall`/`ToolResult` contract + validator (additive) |
| `nexus/execution/runners/search_provider.py` | **new** | `SearchProvider` port (additive) |
| `tests/unit/execution/test_hermes.py` | modify | migrate to injection; add honesty tests |
| (optional) `tests/unit/execution/test_hermes_honesty.py` | **new** | real-branch/guard tests |

**Not touched in H-2:** `base.py` (no contract change for P0), `orchestrator.py`, scheduler, governance,
memory schema, events, config (budget config is P1), `confinement.py` (S-4, done). **No migrations.**

## 4. Post-H-2 sequence (designed, separately gated)

```
H-2  P0 honesty  ──► Experimental  (this plan)
H-3  (optional)  real search provider hardening / planning depth   [if split from H-2]
H-4  P1 lifecycle: terminate() wired (orchestrator) + resume_goal + fail-fast init + budget/TIMED_OUT
                  └─► Pilot (with R-05 floor already done by S-4, one audited real run)
H-5  P2 + R-05 in-container ceiling (with Track S) + test depth
```

> `ADR-hermes-v1.1-foundation` sequencing names H-2 (honesty) → H-3 (search+planning) → H-4 (lifecycle+
> resume) → H-5 (hardening). This plan folds **search+structured planning into H-2's P0** (they are
> Experimental-gating per the ADR's Experimental gate) and concentrates lifecycle (terminate/resume) in
> **H-4 (P1)**. The split is a sequencing choice for the implementation AP; either grouping satisfies the
> gates. Each AP is **separately approved**.

## 5. Constraints reaffirmed

Design only ✅ · no source/test changes in this AP ✅ · no migrations ✅ · no runtime behavior change ✅ ·
no opportunistic refactoring ✅ · no new tools/agents/backends ✅ · Runtime V2 contract, governance,
scheduler, memory schema, events preserved ✅. Implementation is **gated** — H-2 begins only on explicit
approval.

## 6. Definition of done (H-2 implementation, when authorized)

Six P0 gaps closed with RED-first tests; mock path absent and proven so; real search/plan/exit-status
honest; full suite + ruff + mypy green, zero regressions; Caps 2/3/4/8/18 reclassified with evidence;
Hermes meets the **Experimental** gate. Lifecycle safety (Pilot) remains for H-4.
