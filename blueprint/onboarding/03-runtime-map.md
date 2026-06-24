# 03 — Runtime Map (Architecture Review: Runtime Registry, Runtime Selection, Sandbox Manager, Runners)

> Read-only audit of `nexus/execution/`. Each subsystem is reviewed with the standard framework:
> Purpose · Dependencies · Inputs · Outputs · Critical Invariants · Failure Modes · Recovery ·
> Extension Points. Evidence cited as `file:line`.

---

## Execution flow at a glance

```
orchestrator reads task.runtime_id ──► get_runtime_adapter() resolves from RuntimeRegistry
   ──► ExecutionService.start_execution (approval gate)  ──► adapter.validate() → GovernanceManager (11 checks)
   ──► adapter.execute() → SandboxManager → SandboxProvider → subprocess
   ──► artifacts/steps/audit persisted ──► finalize_execution
```
(`scheduling/orchestrator.py:143-246`, `execution/service.py`, `execution/governance.py`,
`execution/sandbox/*`, `execution/runners/*`.)

---

## A. Runtime Registry  (`execution/runners/__init__.py`)

**Purpose** — Decouple the orchestrator from concrete adapter classes; map a string `runtime_id`
to an adapter class (`runners/__init__.py:11-12`).

**Dependencies** — `BaseRuntimeAdapter` (`runners/base.py`); the three runner modules, imported
lazily inside `get_runtime_adapter` to trigger decorator registration (`runners/__init__.py:52-54`).

**Inputs** — `runtime_id` string (from `task.runtime_id`).
**Outputs** — an instantiated adapter via a fixed 5-arg constructor
(`db_session, execution_id, event_gateway, openrouter_client, settings`, `runners/__init__.py:58-64`).

**Mechanism** — Global singleton `runtime_registry = RuntimeRegistry()` (`runners/__init__.py:37`);
adapters self-register via class decorator `@runtime_registry.register("claude")` etc.
(`claude.py:24`, `gemini.py:24`, `hermes.py:24`). Keys are lowercased + stripped of `_`/`-`; one
hardcoded alias `claudecode → claude` (`runners/__init__.py:26-29`).

**Critical invariants** — All adapters share the same constructor signature; keys are normalized;
registration only happens on module import.

**Failure modes** — Unknown id → `KeyError` (`runners/__init__.py:33`); an adapter with a different
`__init__` would `TypeError` at instantiation (factory passes 5 fixed kwargs).

**Recovery** — None; `KeyError` propagates to the orchestrator (which would fail the task).

**Extension points** — New runtime = new module + one decorator line; matches the ADR goal of
"zero orchestrator changes" to add a runtime (`ADR-runtime-selection.md:44`).

**Notable gap** — The registry stores **no metadata** (no capabilities, permissions, timeouts, or
`runtime_type`). The design doc specifies a richer 2-tuple `(runtime_type, runtime_id)` key
(`runtime-registry-design.md:31-47`); the code uses a flat string map. Runtime "type" is inferred at
dispatch by `isinstance` against `CLIRuntimeAdapter`/`AgentRuntimeAdapter`
(`orchestrator.py:185,210`).

---

## B. Runtime Selection  (`scheduling/orchestrator.py:143-218`)

**Purpose** — Choose the adapter and derive the command/goal for a task.

**Dependencies** — `TaskRecord.runtime_id`/`.description`, the registry, the adapter base classes.

**Inputs** — `task.runtime_id` (default `"gemini"`, `orchestrator.py:143`), `task.description`.
**Outputs** — an adapter instance + a `command` (CLI) or `goal` (agent) string.

**Mechanism (actual)** — This is **direct field lookup, not scoring/capability matching**:
- `runner = task.runtime_id or "gemini"` (`orchestrator.py:143`).
- Command derived by string-prefix heuristic on the description: `cmd:` → command, `goal:` → goal,
  else raw/`echo` default (`orchestrator.py:145-152`).
- Dispatch by class: `CLIRuntimeAdapter` → `validate()/execute()`; `AgentRuntimeAdapter` →
  `validate_goal()/execute_goal()`; else `TypeError` (`orchestrator.py:185-218`).

**Critical invariants** — Adapter must subclass one of the two base types.

**Failure modes** — Null `runtime_id` silently routes to Gemini; empty description runs the
hardcoded `echo 'Hello from Nexus Control Plane!'` (`orchestrator.py:145`); description-prefix
parsing is brittle.

**Recovery** — Default-to-gemini only.

**Doc divergence** — ADR/Runtime-Selection design promises routing on `runtime_type`,
`execution_profile`, `runtime_policy` columns and the elimination of description string-matching
(`ADR-runtime-selection.md:7,20-45`). Those columns exist on the model and are read by *governance*
(`governance.py:113,224`) but **selection itself still uses `runtime_id` + description prefixes**.
A designed `ResearchRuntimeAdapter` path (`runtime-v2-design.md:42-48`) is not implemented.

---

## C. Sandbox Manager  (`execution/sandbox/`)

**Purpose** — Provision, limit, and audit process execution behind a provider abstraction
(`sandbox/manager.py:24-25`).

**Dependencies** — `SandboxAuditIntegration` (`sandbox/audit.py`), providers (`sandbox/provider.py`),
`NexusSettings.sandbox`, and the `docker` CLI on the Docker path.

**Inputs** — `command, cwd, timeout, correlation_id` (`manager.py:55-61`).
**Outputs** — a `SandboxProcess` handle whose `communicate()` is wrapped to emit terminal audit
events (`manager.py:120-170`).

**Providers** (`provider.py:57-79`):
- `LocalSandboxProvider` — host `asyncio.create_subprocess_shell`, **no isolation** (`provider.py:88-101`).
- `DockerSandboxProvider` — real isolation: `--cpus --memory --network -v host:/workspace[:ro]`
  (`provider.py:133-175`).
- `MockSandboxProvider` — keyword-driven simulated results (`provider.py:210-246`).

**Provider selection** — `Local` unless `settings.sandbox.enabled` and provider is `docker`/`mock`
(`manager.py:34-53`). **Default config is `enabled=False`, `provider="local"`**
(`config.py:101-102`) → the default real path executes commands **directly on the host with no
isolation**.

**Critical invariants** — Every run emits `sandbox.created` + `sandbox.started`; exactly one
terminal event (`terminated`/`timeout`/`failure`); container names prefixed `nexus_sandbox_`.

**Failure modes** — Default = zero isolation (the governance blacklist is the only barrier); Docker
`network="none"` blocks network tooling; `terminate()` is fire-and-forget
(`provider.py:45-48`, not awaited).

**Recovery** — `SandboxLifecycleService.cleanup_orphaned_sandboxes()` prunes leaked Docker
containers (`sandbox/lifecycle.py:15-53`); Docker `--rm` auto-removes on exit.

**Extension points** — Add a provider by subclassing `SandboxProvider` and extending
`_resolve_provider()`. **Dead code:** `SandboxArtifactCollector.collect_file` (`collector.py:16`) is
never invoked — Docker-produced artifacts are never copied back to host.

---

## D. Runners  (`execution/runners/{claude,gemini,hermes}.py`)

### Claude & Gemini — generic shell runners (CLI runtime)

**Purpose** — Run a CLI command under governance + sandbox, then persist logs/diff/summary.

**Reality** — Neither invokes a `claude-code` or `gemini` binary. Both pass the raw `command`
string to the shell via `SandboxManager` (`claude.py:107-112`, `gemini.py:112`). They are
byte-for-byte near-identical and differ only in the `runtime=` string they pass to governance
(`claude.py:67` vs `gemini.py:72`) and a Gemini-only `GEMINI_API_KEY` check used solely for the
optional summary (`gemini.py:51-57`). The PTY/interactive `claude-code` integration in
`runtime-adapter-design.md:67-73` does not exist.

**Output contract** — `{exit_code, duration_seconds, stdout_len, stderr_len}`
(`claude.py:150-155`). `persist()` writes `stdout.log`, `stderr.log`, an LLM `summary.md`, and
`changes.diff` if `.git` exists (`claude.py:213-288`).

**⚠ Timeout defect (confirmed independently)** — Both read
`getattr(self.settings.execution, "research_timeout_seconds", 300)` (`claude.py:83`, `gemini.py:88`),
but `ExecutionConfig` defines `research_timeout`/`gemini_timeout`/`claude_timeout`/`hard_limit`
(`config.py:83-86`) — there is **no `research_timeout_seconds` attribute** on the settings object
(the YAML key `settings.example.yaml:78` is dropped by pydantic `extra="ignore"`). So **every CLI
run silently uses the 300s fallback**, ignoring the ADR-010 tiers (Gemini 30m / Claude 45m / hard
60m, `ADR-010:21-27`). This is a real, high-priority correctness bug.

**Failure modes** — Failures are swallowed into `exit_code=-1` with a stderr string, but the step is
still marked `COMPLETED` (`claude.py:142`) — failure is visible only via the exit code.

### Hermes — agent runtime (partially simulated)

**Purpose** — Bounded ReAct-style agent loop (`max_steps=5`, `hermes.py:151-155`) with per-step
`AgentStepRecord` + `WorkflowCheckpointRecord` persistence (`hermes.py:248-275`).

**Reality** — Largely a stub: hardcoded MCP-research plan (`hermes.py:145-149`); `web_search`
returns canned text for "mcp" queries, else "No results" (`hermes.py:76-86`); a simulation branch
hardcodes the action sequence when there is no OpenRouter client, the client is an `AsyncMock`, or
the api_key contains `"test-key"` (`hermes.py:183-209`). **`from unittest.mock import AsyncMock` is
imported in production code** (`hermes.py:7`) and referenced in the runtime branch
(`hermes.py:186`) — confirmed. `terminate()` is a no-op `pass` (`hermes.py:310-312`), so a runaway
loop cannot be force-stopped. `write_file` writes to arbitrary `os.path.abspath(path)` outside
governance path containment (`hermes.py:96-105`).

---

## Runner comparison

| Runner | Base class | Real binary invoked? | Timeout source | Distinguishing logic |
|---|---|---|---|---|
| Claude | `CLIRuntimeAdapter` | No — raw shell (`claude.py:107`) | broken 300s fallback (`claude.py:83`) | `runtime="claude"` to governance |
| Gemini | `CLIRuntimeAdapter` | No — raw shell (`gemini.py:112`) | broken 300s fallback (`gemini.py:88`) | `runtime="gemini"` + key check for summary |
| Hermes | `AgentRuntimeAdapter` | n/a (agent loop) | hardcoded 300s (`hermes.py:121`) | hardcoded plan + `AsyncMock` branch |

---

## Runtime subsystem gap analysis

**Excellent** — Registry decoupling matches ADR intent (`runners/__init__.py:17-22`); clean provider
abstraction with a real Docker isolation implementation (`provider.py:133-175`); complete,
correlation-linked sandbox audit lifecycle (`manager.py:100-169`); adapter split
(`CLIRuntimeAdapter`/`AgentRuntimeAdapter`) cleanly separates CLI vs agent concerns
(`runners/base.py`, ratified by `ADR-runtime-abstraction-validation.md`).

**Missing** — Real CLI integration (Claude/Gemini); real web search + non-simulated Hermes;
`ResearchRuntimeAdapter`; artifact copy-back (`collector.py` is dead code); a 30s heartbeat driver
(ADR-010:49).

**Risky** — Timeout config bug (300s for everything); default = zero isolation
(`config.py:101`); substring command blacklist is bypassable (`governance.py:621`); `terminate()`
not awaited / Hermes terminate is a no-op; Hermes `write_file` bypasses path containment; steps
always marked `COMPLETED` on failure.

**Never change without extreme care** — Adapter constructor signature the factory depends on
(`runners/__init__.py:58-64`); the dispatch-by-base-class contract (`orchestrator.py:185-218`);
sandbox audit event symmetry.

**Monitor** — `lock_wait_ms`, `execution_start_latency_ms` (already emitted); sandbox
timeout/failure vs terminated ratios; orphaned `nexus_sandbox_*` containers; frequency of the
default-300s timeout path.

**Improve (opportunities, not directives)** — see `12-improvement-opportunities.md`: fix the
timeout field name; tokenize the blacklist; implement or rename the CLI runners; remove `AsyncMock`
from production; default to an isolating sandbox or require explicit host opt-in.
