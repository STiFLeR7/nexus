# Nexus Email Design System

> The visual identity of Nexus v2, expressed through email.
> **Design-first artifact.** Nothing here is wired into `EmailService`, business
> logic, or the runtime. These are pure design assets (Jinja2 + HTML) plus the
> documentation that governs them.

---

## 1. Philosophy

Nexus is an **AI Orchestration Control Plane** — mission control for autonomous
work. Its email must read like an instrument panel, not a newsletter. Every
message should communicate **operational intelligence, reliability, and calm
authority**.

The reference points are product surfaces, never marketing ones:

| We aim for | We avoid |
|---|---|
| Stripe · Linear · GitHub · Vercel · Notion · OpenAI · Anthropic | Promotional newsletters |
| Restraint, whitespace, hierarchy | Gradient-heavy hero banners |
| Soft borders, rounded cards, soft shadows | Glassmorphism, neon, drop-shadow stacks |
| Semantic colour with meaning | Decorative colour |
| Data density that stays scannable | Bootstrap email kits |

**Design principles**

1. **Signal over decoration.** Colour, weight, and space carry meaning. If a
   pixel doesn't help the operator decide or act, remove it.
2. **One language, many personalities.** Every email shares the same shell,
   type scale, and components. Each *type* gets a single **accent colour** and a
   tailored composition — that is its entire personality budget.
3. **Bulletproof first.** It must render in Gmail, Outlook (Word engine), and
   Apple Mail before it is allowed to be beautiful. Progressive enhancement, not
   graceful degradation.
4. **Dark-mode native.** Light is the source of truth; dark is a first-class
   peer, not an afterthought.
5. **Accessible by construction.** Contrast, semantics, and real text are
   defaults, not add-ons.

---

## 2. Architecture

```
templates/
  base.html                  Master layout (the shell every email extends)
  partials/                  Reusable component macros + header/footer includes
    header.html  footer.html
    section.html  metric_card.html  badge.html  status_chip.html
    divider.html  button.html  timeline.html  table.html
  emails/                    One file per email TYPE (extends base.html)
    morning_digest.html  operational_intelligence.html  research_report.html
    todo_digest.html  reminder.html  approval_required.html
    execution_completed.html  execution_failed.html  security_alert.html
    scheduler_report.html  weekly_review.html  monthly_executive.html
    conversations/           The Q&A / conversational family
      qa_transcript.html  conversation_summary.html
      action_items.html  decision_summary.html
  previews/                  Rendered HTML examples (open in a browser)
  sample_context.json        Concrete placeholder payloads (the data schema)
  EMAIL_DESIGN_SYSTEM.md  EMAIL_STYLE_GUIDE.md
  EMAIL_COMPONENT_LIBRARY.md  EMAIL_TEMPLATE_GUIDELINES.md
```

**Templating engine: Jinja2** (already a dependency, `3.1.x`). Chosen over MJML
or a hand-rolled string builder because it is native to the Python stack, needs
no new toolchain, supports `{% extends %}` / `{% block %}` / `{% macro %}` /
`{% include %}`, and the rendered output is plain inline-styled HTML.

**Inheritance model**

- `base.html` owns the `<head>`, the non-inlinable `<style>` block (dark mode +
  responsive only), the page/container/card scaffolding, and the header/footer
  includes.
- Each email **extends** `base.html`, overrides `{% block accent %}` (its
  personality colour) and `{% block content %}` (its composition).
- Components are **macros** imported inside the content block, e.g.
  `{% import "partials/metric_card.html" as mc %}`.

---

## 3. Colour system

Colour is **semantic**. A colour is only used when it means something.

### 3.1 Neutrals (the 95%)

| Token | Light | Dark | Use |
|---|---|---|---|
| `page` | `#F1F5F9` | `#0B0F19` | Outer canvas behind the card |
| `surface` | `#FFFFFF` | `#111827` | Card / panel background |
| `surface-muted` | `#F8FAFC` | `#0F1623` | Metric cards, kv grids, code labels |
| `border` | `#E2E8F0` | `#1F2937` | Hairlines, card edges |
| `border-strong` | `#CBD5E1` | `#374151` | Emphasis dividers |
| `ink` (heading) | `#0F172A` | `#F9FAFB` | Titles, key values |
| `body` | `#334155` | `#CBD5E1` | Paragraph text |
| `muted` | `#64748B` | `#9CA3AF` | Secondary text, labels |
| `faint` | `#94A3B8` | `#6B7280` | Timestamps, captions |

### 3.2 Brand

| Token | Hex | Use |
|---|---|---|
| `brand-navy` | `#0F172A` | Logo tile, executive reports, wordmark |
| `brand-accent` (indigo) | `#4F46E5` | Primary CTA, links, default accent |
| `brand-accent-soft` | `#EEF2FF` | Accent backgrounds, brand badges |

### 3.3 Semantic states

| State | Solid | Text-on-soft | Soft bg | Soft border |
|---|---|---|---|---|
| Success | `#16A34A` | `#15803D` | `#ECFDF5` | `#A7F3D0` |
| Warning | `#D97706` | `#B45309` | `#FFFBEB` | `#FDE68A` |
| Danger | `#DC2626` | `#B91C1C` | `#FEF2F2` | `#FECACA` |
| Info | `#2563EB` | `#1D4ED8` | `#EFF6FF` | `#BFDBFE` |
| Pending | `#7C3AED` | `#6D28D9` | `#F5F3FF` | `#EDE9FE` |
| Neutral | `#64748B` | `#475569` | `#F1F5F9` | `#E2E8F0` |

### 3.4 Subsystem hues (accents per Nexus domain)

Used as section accents and email accent bars so a glance maps to a subsystem.

| Subsystem | Hex | | Subsystem | Hex |
|---|---|---|---|---|
| Communication | `#4F46E5` | | Memory | `#7C3AED` |
| Research | `#0EA5E9` | | Sandbox | `#059669` |
| Execution | `#6366F1` | | Runtime | `#D97706` |
| Governance | `#DC2626` | | Scheduler | `#0891B2` |

> **Contrast.** All text/background pairs above meet WCAG AA for their size class
> (≥ 4.5:1 body, ≥ 3:1 large/bold). See the Accessibility Checklist in
> `EMAIL_STYLE_GUIDE.md`.

---

## 4. Typography

System font stack — zero web-font dependency, native rendering everywhere:

```
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
```

Monospace (code, IDs, metrics-detail):

```
ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace
```

### Type scale

| Role | Size / Line | Weight | Tracking | Colour | Notes |
|---|---|---|---|---|---|
| Hero | 32 / 40 | 700 | −0.6 | ink | Rare; landing-style headers |
| Title | 24 / 32 | 600 | −0.4 | ink | Email subject line in header |
| Subtitle | 15 / 24 | 400 | 0 | muted | One supporting sentence |
| Section | 16 / 22 | 600 | −0.2 | ink | `section()` heading |
| Eyebrow | 11–12 / 16 | 700 | +1.1 uppercase | faint/accent | Category label above a title |
| Body | 15 / 24 | 400 | 0 | body | Default reading text |
| Body-sm | 14 / 21 | 400 | 0 | body | Panels, cards |
| Caption | 13 / 20 | 400 | 0 | muted | Supporting detail |
| Metric | 28 / 34 | 600 | −0.6 | ink | KPI value (mobile → 24) |
| Status | 12 / 16 | 600 | +0.2 | semantic | Chips, badges |
| Timestamp | 11–12 / 16 | 500 | +0.2 | faint | Header, footer, timeline |

Responsive: Hero/Title/Metric step down one level at ≤ 600px (see `base.html`
`.nx-hero`, `.nx-title`, `.nx-metric-value`).

---

## 5. Spacing, radius, elevation

**Spacing scale (px):** `4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 64`
Section gutter is `32px` (desktop) → `20px` (mobile, via `.nx-px`).
Section rhythm uses `divider(space=20)` between blocks and `spacer(n)` for tuned gaps.

**Radius:** `sm 6 · md 8 (buttons) · lg 10 (cards/panels) · xl 14 (outer card) · pill 999 (chips)`

**Elevation:** one soft card shadow only —
`box-shadow: 0 1px 2px rgba(16,24,40,.06), 0 1px 3px rgba(16,24,40,.10)`.
No stacked shadows, no glow. Depth comes from borders + surface contrast.

**Layout grid:** single 600px column, 32px side gutters → 536px content width.
Multi-up rows (metrics, buttons) use equal-width cells that **stack** at ≤ 600px
via the `.nx-stack` class.

---

## 6. Iconography

No external icon libraries, no remote images (privacy + reliability). Icons are:

- **Unicode glyphs** for inline marks: `→ ● ▪ ★ ✓ ✕ ▲ ▼ ☐ ☑ ⏰ ↗ ↻ ℹ`.
- **CSS shapes** for status dots and the brand tile (rounded `<td>`s).
- The logo is a **bulletproof monogram** — a `#0F172A` rounded tile with a white
  "N" — rendering identically across all clients and dark mode. (An optional
  hosted PNG/retina logo can replace it later without structural change; see
  `EMAIL_TEMPLATE_GUIDELINES.md` §Logo.)

Glyph usage is consistent: `→` = next/recommendation, `✓` = done/success,
`✕` = reject/fail, `★` = importance/highlight, `●` = insight bullet,
`▪` = architecture note, `☐/☑` = action item.

---

## 7. Email type catalogue

Each type = base shell + one accent + a composition. Personality summary:

| # | Template | Accent | Personality |
|---|---|---|---|
| 1 | `morning_digest` | Indigo `#4F46E5` | Confident daily briefing, action-first |
| 2 | `operational_intelligence` | Navy `#0F172A` | Dense executive report |
| 3 | `research_report` | Sky `#0EA5E9` | Sharp analyst briefing |
| 4 | `todo_digest` | Indigo `#4F46E5` | Productivity checklist |
| 5 | `reminder` | Purple `#7C3AED` | Minimal, single-focus |
| 6 | `approval_required` | Amber `#D97706` | High-stakes, unmistakable CTAs |
| 7 | `execution_completed` | Green `#16A34A` | Reassuring, evidence-backed |
| 8 | `execution_failed` | Red `#DC2626` | Calm forensic incident report |
| 9 | `security_alert` | Red `#DC2626` | Authoritative, action-first |
| 10 | `scheduler_report` | Teal `#0891B2` | Job run summary |
| 11 | `weekly_review` | Navy `#0F172A` | Executive dashboard |
| 12 | `monthly_executive` | Navy `#0F172A` | CEO-style narrative |
| Q&A | `conversations/*` | Indigo `#4F46E5` | Transcript / summary / actions / decisions |

Full per-type specifications are in `EMAIL_TEMPLATE_GUIDELINES.md` §Specifications.

---

## 8. Placeholder data schema

Every template is driven by a plain context dict (no ORM types). Concrete,
copy-pasteable payloads for **all** templates live in
[`sample_context.json`](./sample_context.json). Shared keys consumed by the
shell (header/footer):

| Key | Type | Meaning |
|---|---|---|
| `eyebrow` | str | Uppercase category label in the header |
| `subject` | str | Header title (and the email Subject; see Style Guide) |
| `subtitle` | str | One supporting sentence + inbox preheader |
| `timestamp` | str | Pre-formatted, e.g. `"Jun 26, 2026 · 08:00 IST"` |
| `version` | str | Footer build tag, e.g. `"v1.2.0"` |
| `brand_links` | list[{label, href}] | Footer navigation |
| `footer_note` | str? | Override the automation disclaimer |

Type-specific keys are documented at the top of each template file and in
`sample_context.json`.

---

## 9. Future extension strategy

This is a **design language**, not just an email kit. The same tokens and
component semantics translate to every future Nexus channel:

| Channel | How the language maps |
|---|---|
| **Discord embeds** | Accent → embed colour bar; `status_chip` → field with dot emoji; `metric_card` → inline fields; `code_block` → fenced block. Roles already map via the channel harness. |
| **Web dashboard cards** | Same tokens as CSS variables; macros become React/Vue components 1:1 (MetricCard, StatusChip, Timeline, Panel). |
| **Slack** | Block Kit: `section`→section block, `button_row`→actions block, `kv_grid`→fields, accent→context/colour. |
| **Microsoft Teams** | Adaptive Cards: panels→Containers with `style`, metrics→ColumnSet, chips→`TextBlock` + colour. |
| **Mobile push** | `subject` + `subtitle` are already the title/body; accent → notification colour. |
| **PDF reports** | The HTML renders to PDF (WeasyPrint/Chromium) as-is; charts swap from progress bars to embedded vector images. |

**Token portability:** §3–§5 are the contract. Keep one source of truth for the
palette/scale; every channel implementation references these names, never raw
hex re-invented per surface. When a token changes here, it changes everywhere.

**Governance:** new email types must (a) extend `base.html`, (b) pick exactly one
accent from §3.4, (c) reuse existing components before inventing new ones, and
(d) ship a `sample_context.json` entry + a preview. See the QA checklist in
`EMAIL_TEMPLATE_GUIDELINES.md`.
