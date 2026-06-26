# Nexus Email Component Library

The reusable building blocks. Every email is composed from these — authors
should reach for an existing component before writing bespoke HTML. Each entry
lists the import, signature, parameters, an example, variants, and rendering
notes.

> Import a partial once at the top of your `{% block content %}`:
> `{% import "partials/metric_card.html" as mc %}`
> Header and footer are auto-included by `base.html`; you don't import them.

---

## Layout & shell

### `base.html` — master layout
- **Blocks:** `title`, `preheader`, `accent` (top-bar hex = personality), `content`.
- **Provides:** `<head>`, dark-mode + responsive `<style>`, page→container→card
  scaffold, header/footer includes, preheader text.
- **Use:** `{% extends "base.html" %}` then override `accent` + `content`.

### `partials/header.html` — brand lockup
- **Renders:** monogram tile + "Nexus" wordmark, right-aligned `timestamp`,
  `eyebrow`, `subject` (`<h1>`), `subtitle`, hairline.
- **Context:** `eyebrow, subject, subtitle, timestamp, accent`.
- **Notes:** logo is a bulletproof CSS tile (no image). Emits `<tr>` rows.

### `partials/footer.html` — closer
- **Renders:** `brand_links`, brand line + `version`, automation note, generated-at.
- **Context:** `brand_links, version, footer_note, timestamp`.

---

## Content components

### Section — `section.html` → `sec`
Titled content block with accent tick + optional eyebrow. Call form.

```jinja
{% import "partials/section.html" as sec %}
{% call sec.section("Today's health", eyebrow="System", accent="#16A34A") %}
  ...inner html...
{% endcall %}
```
- **Params:** `title`, `eyebrow=None`, `accent="#4F46E5"`; body via `{{ caller() }}`.

### Panel — `section.html` → `sec.panel`
Soft tinted callout for info/success/warning/error/neutral.

```jinja
{% call sec.panel("warning", title="Throughput dip") %}−8% vs 7-day avg.{% endcall %}
```
- **Params:** `tone="info"` (`info·success·warning·error·neutral`), `title=None`.
- **Notes:** left accent bar + leading glyph; use for alerts, root cause, TL;DR.

### Code / artifact block — `section.html` → `sec.code_block`
Monospace dark surface for logs, stack traces, file lists, raw events.

```jinja
{{ sec.code_block(incident.stderr, label="stderr") }}
```
- **Params:** `content`, `label=None`. Wraps long lines; safe on mobile.

### Metric card — `metric_card.html` → `mc`
Single KPI, or a responsive row that stacks on mobile (**prefer the row**).

```jinja
{% import "partials/metric_card.html" as mc %}
{{ mc.metric_row([
   {"label":"Uptime","value":"99.98%","delta":"+0.04","trend":"up"},
   {"label":"Tasks","value":"24","trend":"flat"},
   {"label":"Failures","value":"1","delta":"-2","trend":"down-good","accent":"#DC2626"}
]) }}
```
- **`metric_card(label, value, delta=None, trend='flat', accent='#0F172A')`**
- **`metric_row(items)`** — up to 3 across; `.nx-stack` collapses to full-width rows ≤ 600px.
- **trend:** `up`(green▲) `down`(red▼) `flat`(→) `up-bad`(red▲) `down-good`(green▼).

### Timeline — `timeline.html` → `tl`
Vertical event sequence (scheduler runs, failure stages, audit, conversation).

```jinja
{% import "partials/timeline.html" as tl %}
{{ tl.timeline([
   {"time":"08:00","title":"Briefing dispatched","tone":"success","body":"3 channels"},
   {"time":"10:00","title":"Research run","tone":"info"}
]) }}
```
- **Params:** `events=[{time,title,body?,tone?}]`. tone → dot colour
  (`success·warning·danger·info·pending·neutral`).

### Data table — `table.html` → `tbl.data_table`
Bordered, header-styled table with per-column alignment.

```jinja
{% import "partials/table.html" as tbl %}
{{ tbl.data_table(columns=["Job","Status","Duration"],
                  rows=[["research","Succeeded","12s"],["sweep","Skipped","—"]],
                  aligns=["left","left","right"]) }}
```
- **Params:** `columns`, `rows` (list of cell lists), `aligns=None`.

### Key/value grid — `table.html` → `tbl.kv_grid`
Metadata block (definition-list style); label left, value right.

```jinja
{{ tbl.kv_grid([["Runtime","nexus"],["Repository","workspace_root"]]) }}
```
- **Params:** `pairs=[[key,value], ...]`.

### Progress bar — `table.html` → `tbl.progress`
Completion / budget / "chart bar". Bulletproof (table fill, no CSS gradients).

```jinja
{{ tbl.progress(72, "brand", "Step budget") }}
```
- **Params:** `pct`, `tone="brand"` (`brand·success·warning·danger·info`), `label=None`.
- **Notes:** clamps 0–100. Stacked bars approximate charts in email; real charts
  ship as pre-rendered images in the PDF export.

---

## Indicators & actions

### Badge — `badge.html` → `bdg.badge`
Static rounded label (tags, subsystem, IDs).

```jinja
{% import "partials/badge.html" as bdg %}
{{ bdg.badge("Governance", "brand") }}  {{ bdg.badge("CVE-2026-1", "danger", mono=True) }}
```
- **Params:** `text`, `tone="neutral"` (`neutral·brand·success·warning·danger·info·pending`), `mono=False`.

### Status chip — `status_chip.html` → `chip.status_chip`
A state with a leading status dot (liveness, task/job state, risk).

```jinja
{% import "partials/status_chip.html" as chip %}
{{ chip.status_chip("Healthy", "success") }}
{{ chip.status_chip("MEDIUM RISK", "warning") }}
```
- **Params:** `text`, `status="info"` (`success·warning·danger·info·pending·neutral`).

### Divider / spacer — `divider.html` → `rule`
Consistent vertical rhythm.

```jinja
{% import "partials/divider.html" as rule %}
{{ rule.divider() }}     {# hairline + 20px above/below #}
{{ rule.spacer(24) }}    {# invisible gap only #}
```
- **`divider(space=20)`**, **`spacer(space=16)`**.

### Button — `button.html` → `btn`
Bulletproof CTA (VML for Outlook), full-width-on-mobile, and a button group.

```jinja
{% import "partials/button.html" as btn %}
{{ btn.button("Open dashboard", url, "primary") }}
{{ btn.button_row([
   {"label":"✓ Approve","href":a,"variant":"success"},
   {"label":"✕ Reject","href":r,"variant":"danger-outline"}
]) }}
```
- **`button(label, href, variant='primary', full=False)`** — variants:
  `primary·neutral·success·danger·danger-outline·ghost`.
- **`button_row(buttons)`** — stacks vertically ≤ 600px.

---

## Higher-order patterns (compositions)

These aren't separate files — they're conventional compositions of the above,
used across templates and worth standardising:

| Pattern | Built from | Seen in |
|---|---|---|
| **Status card** | `panel` + `status_chip` + `kv_grid` | approval, security, completed |
| **Event card** | white card + title + `badge` + caption + link | morning digest (research) |
| **Task card** | `data_table` row or card + `badge` priority | todo, digest |
| **Approval card** | `panel` + risk `chip` + `kv_grid` + `code_block(files)` + `button_row` | approval_required |
| **Incident report** | `panel(error)` + `kv_grid` + `timeline` + `code_block` + numbered recovery | execution_failed |
| **Statistics panel** | `metric_row` + `progress` bars | operational, weekly, monthly |
| **Info/Alert/Warning/Error/Success panels** | `panel(tone)` | everywhere |
| **Link preview** | event card with title + source `badge` + "Read →" | research, digest |
| **Priority / severity indicator** | `status_chip` + `badge` | approval, security |
| **Key-value grid** | `kv_grid` | metadata blocks |
| **Chat bubble** | aligned table + tinted `<td>` | qa_transcript |

---

## Q&A / conversational family mapping

Four template files cover the whole conversational family; the rest are
**presets of these** (same structure, different `eyebrow`/`subject`/emphasis):

| Requested type | Use template | Notes |
|---|---|---|
| Q&A transcript | `conversations/qa_transcript.html` | chat bubbles, operator vs Dex |
| Conversation summary | `conversations/conversation_summary.html` | TL;DR + key points + decisions + actions |
| Meeting notes | `conversation_summary` | eyebrow "Meeting Notes"; topics = agenda |
| AI session recap | `conversation_summary` | eyebrow "Session Recap" |
| Knowledge capture | `conversation_summary` | lead with `key_points`; add `references` |
| Daily conversation digest | `conversation_summary` | eyebrow "Conversation Digest"; multiple topics |
| Research discussion | `conversation_summary` | accent `#0EA5E9`; emphasise insights |
| Decision summary | `conversations/decision_summary.html` | per-decision rationale + alternatives |
| Action items | `conversations/action_items.html` | checklist with owner/due/priority |
| Follow-ups | `action_items` | summary_line "Follow-ups"; lower priority tone |
| Operator notes | `conversation_summary` | free-form `key_points` only |

This keeps the surface small and consistent while covering every requested
conversational format. New conversational variants should reuse one of these
four rather than adding files.
