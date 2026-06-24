# Hermes Reality Audit (AP-105)

> Evidence-based architectural audit of the Hermes runtime. **Audit only** — no implementation, no
> source change, no refactor, no redesign. The objective is truth, not optimism. Every claim cites
> source.
>
> **Release:** v1.0.1 "Alignment" · **Finding:** A-005 · **Subject:** `nexus/execution/runners/hermes.py`
> (`HermesRuntimeAdapter`). Companion artifacts: `hermes-capability-ledger.md`,
> `hermes-execution-trace-analysis.md`, `hermes-gap-analysis.md`, `hermes-roadmap-boundary.md`,
> `ADR-hermes-reality-audit.md`.

---

## 1. What Hermes actually is

Hermes is a **production-routable ReAct-style agent adapter** with **real database integration** wrapped
around **simulated intelligence and incomplete lifecycle controls**. It implements the
`AgentRuntimeAdapter` contract (`base.py:84-95`), is registered as `"hermes"` (`hermes.py:24`), and is
reachable in the live pipeline when a task sets `runtime_id="hermes"` (`orchestrator.py:143,168-216`).

It genuinely: validates goals through governance, runs an iterative tool loop (real LLM in production
config), executes real file and shell tools, and persists agent steps, checkpoints, heartbeats, and
artifacts. It does **not** genuinely: search the web, plan dynamically, report real success/failure,
terminate on demand, or resume after interruption.

## 2. The onboarding-audit concerns — confirmed or not

| Concern (from onboarding) | Verdict | Evidence |
|---|---|---|
| `AsyncMock` in production path | **Confirmed** | `hermes.py:7` import; `hermes.py:186-211` mock decision branch in the prod module |
| Hardcoded plans | **Confirmed** | `hermes.py:147-151` static 3-step plan, goal-independent, decorative |
| Simulated search results | **Confirmed** | `hermes.py:76-86` canned text; no provider call; runs in both branches |
| Limited termination behavior | **Confirmed (stronger)** | `hermes.py:312-314` `terminate()` is `pass` **and never invoked** in the agent path |
| Advertised vs actual capability mismatch | **Confirmed** | "planning/research agent" advertised; plan decorative + search canned + exit always 0 (`hermes.py:284-289`) |

All five concerns are substantiated by source.

## 3. Specific questions (answered with evidence)

1. **Planning — dynamic or predefined?** **Predefined/decorative.** The plan is a hardcoded literal
   (`hermes.py:147-151`), identical for any goal, and never drives the loop. Only *next-action*
   selection is dynamic (real LLM in prod, `hermes.py:213`). → Planning = **Simulated**.
2. **Tool use — executed or simulated?** **Mixed.** `read_file`, `write_file`, `execute_command` are
   **real** (`hermes.py:88-131`, real FS + `SandboxManager`). `web_search` is **simulated**
   (`hermes.py:76-86`).
3. **Search — real providers or canned?** **Canned.** No network/provider call anywhere in
   `_execute_tool`; returns fixed MCP text or `"No results found"`.
4. **Recovery — resumable or appears resumable?** **Appears only.** Checkpoints are written
   (`hermes.py:274-277`) but never read; `execute_goal` always restarts (`hermes.py:138-139`); no
   `resume_goal` exists (only `research.py:361`/`briefing.py:250` resume). → **Not Present**.
5. **Checkpointing — real or placeholder?** **Real persistence** to `workflow_checkpoints`
   (`hermes.py:301-310`; `test_hermes.py:116-122`) — but unused for recovery.
6. **Heartbeats — operational or synthetic?** **Operational** real DB writes (`hermes.py:291-299`),
   though no orphan-reaper consumes them.
7. **Termination — real cancellation or no-op?** **No-op** (`hermes.py:312-314`), and never called in
   the agent path.
8. **Agent steps — real trajectory or generated?** **Real capture & persistence** mechanism
   (`hermes.py:250-271`); in mock config the *content* is synthetic, in prod config it is genuine
   model output (over canned search observations).
9. **Runtime independence — could it run without mocks?** **Partially.** With a real client/key the
   mock branch is bypassed and the real LLM loop runs — but `AsyncMock` is still imported in the prod
   module, `web_search` stays canned, the plan stays decorative, and exit code stays `0`. It is not
   *clean* of mocks.
10. **Production readiness — what prevents deployment as a real agent runtime?** `AsyncMock` in prod
    (#4), simulated search (#8), always-`0` exit code masking failures (#18), no termination (#14), no
    resume (#12), decorative planning (#2), brittle action parsing (#3), unconfined file writes (#6).
    (See ledger numbering.)

## 4. What is genuinely good (do not lose this)

- **Governance-gated**: every run passes `GovernanceManager.validate_execution` (`hermes.py:57-72`).
- **Real, tested persistence**: `agent_steps`, `workflow_checkpoints`, `execution_artifacts`,
  heartbeats — all real schema, written every step, covered by tests.
- **Real tool execution** for file/command via the sandbox (subject to A-006).
- **Real summarization + artifact set** (plan/trajectory/summary/diff).
- **Clean contract + registry integration** — replaceable behind `AgentRuntimeAdapter`.

The skeleton is sound; the gaps are in *intelligence honesty* and *lifecycle control*, not architecture.

## 5. Final verdict — **Prototype**

**Evidence-supported verdict: Prototype** (degrading to **Concept Demonstration** in the default/no-key
configuration, where the entire decision path is the hardcoded mock branch).

- Not **Mock Runtime**: real governance, real persistence, and real file/command tool execution exist
  and are tested — it is more than a mock.
- Not **Experimental/Pilot/Production Ready**: an in-module `AsyncMock`, unconditionally simulated
  search, an always-success exit code that masks failure, and absent terminate/resume make it unsafe
  and dishonest for any governed pilot that represents it as an autonomous research/planning agent.

It is a **working, DB-integrated agent prototype**: the architecture and plumbing are real; the
autonomy (planning, search) and lifecycle safety (terminate, resume, honest exit status) are not.

## 6. Boundary note

This audit proposes **no implementation**. The "Required Work" columns in the ledger describe gaps only.
What is reality vs roadmap is separated in `hermes-roadmap-boundary.md`; remediation sequencing, if and
when authorized, would be a separate Action Point.
