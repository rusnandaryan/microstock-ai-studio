# DESIGN.md — Microstock AI Studio

> **Brand Identity:** Modern Studio for Microstock Visual Artists & Contributors  
> **Target Audience:** Microstock contributors, visual artists, and AI creators selling on Adobe Stock, Shutterstock, and Freepik.  
> **Personality:** Clean, professional, focused, high-contrast, dependable, and crafted.  
> **Core Rule:** Strictly governed by `antislop-ui`, `antislop-human`, and `antislop.md` (WCAG 2.1 AA contrast compliance, zero generic AI slop, no fake terminal windows, full keyboard accessibility).

---

## 1. Dials Configuration

- **ENERGY: 2 (Balanced Studio)** — Refined professional aesthetic, clean surface hierarchy, purposeful blue accent, high information density without visual clutter.
- **RHYTHM: 2 (Structured with Functional Variation)** — Distinct two-column creative generator on Tab 1, automated scanner & download dropzone on Tab 2, side-by-side reverse prompt comparison on Tab 3.
- **MOTION: 1 (Precise & Purposeful)** — Subtle hover elevations (`translateY(-1px)`), smooth CSS variable transitions (`0.15s ease`), zero distracting continuous animations.

---

## 2. Pro Dark Color System (WCAG AAA Compliant)

The studio runs exclusively in high-precision Dark Mode, engineered for prolonged creative contributor sessions with zero eye strain and mathematical contrast rigor:

### Studio Obsidian Palette
| Token | Hex / Value | Role | Contrast Ratio |
| :--- | :--- | :--- | :--- |
| **Canvas Background** | `#080B11` | Deep obsidian base viewport | Base canvas |
| **Card Surface** | `#0F1623` | Container & panel cards | Elevated ground |
| **Input Surface** | `#141D2D` | Form inputs, selectboxes, dropdowns | 1.5px subtle border `#1D283E` |
| **Elevated Hover** | `#1A253A` | Hover states, active dropdown items | Smooth transition |
| **Primary Text** | `#F8FAFC` | Headings, titles, primary labels | **18.2:1** (Passes AAA) |
| **Secondary Text** | `#94A3B8` | Captions, instructions, metadata | **6.8:1** (Passes AA) |
| **Accent Text** | `#60A5FA` | Active tab text, inline code, status | **8.8:1** on canvas (Passes AAA) |
| **Accent Primary** | `#2563EB` | Primary CTA buttons, focus states | **5.2:1** with white text |
| **Focus Ring** | `#3B82F6` | Keyboard navigation `:focus-visible` | High visibility ring |

### Semantic Badges & Status Indicators
- **Emerald Green** (`rgba(16, 185, 129, 0.15)` / text `#34D399`): Validated resolution status (≥ 4 MP / 300 DPI) and successful export.
- **Amber Gold** (`rgba(245, 158, 11, 0.15)` / text `#FBBF24`): Freepik 4 MB file size requirement and trend demand indicators.
- **Royal Indigo** (`rgba(59, 130, 246, 0.15)` / text `#60A5FA`): Active queue badges and prompt tags.
- **Electric Cyan** (`rgba(6, 182, 212, 0.15)` / text `#38BDF8`): System hardware and status indicators.

---

## 3. Typography & Hierarchy

- **Headings (H1, H2, H3):** `'Space Grotesk', -apple-system, sans-serif` — Modern, geometric, distinctive personality without being decorative slop.
- **Body & Labels:** `'Plus Jakarta Sans', 'Inter', system-ui, sans-serif` — Crisp, legible, balanced letter-spacing.
- **Prompts & Code Output:** `'JetBrains Mono', 'Fira Code', monospace` — Standard monospaced presentation with line wrapping and direct copy actions.

---

## 4. Component Geometry & Accessibility Standards

- **Border Radius Scale:**
  - Cards & Hero Container: `14px`–`16px`
  - Form Inputs & Buttons: `10px`
  - Status Badges & Pills: `8px` (strict ban on pill-everything 999px slop)
- **Keyboard Navigation (R-32):**
  - All interactive buttons (`button`, `a`, tabs) implement explicit `:focus-visible` rings: `outline: 2px solid var(--accent-blue) !important; box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.45) !important;`
- **Copywriting Cleanliness (R-02, R-16):**
  - Zero em dashes (`—`) in UI copy; use clean parentheses or periods.
  - Zero AI buzzwords ("Magic", "AI-Powered", "Revolutionary"); use clear industrial terms ("Prompt Komersial", "Gemini Vision SEO").
- **UI State Robustness (R-27):**
  - Dedicated empty state containers with dashed borders on both Tab 1 and Tab 2 guiding the user when no data has been generated or scanned yet.
- **Responsive Layout & Motion Accessibility:**
  - Fluid breakpoints at `1024px` and `768px` for smooth scaling on laptops, tablets, and split-screen desktop windows.
  - Full support for `@media (prefers-reduced-motion: reduce)` to eliminate jarring transitions for motion-sensitive users.
  - Universal interactive cursor affordance (`cursor: pointer !important`) on all buttons, tabs, options, summaries, and cards.
