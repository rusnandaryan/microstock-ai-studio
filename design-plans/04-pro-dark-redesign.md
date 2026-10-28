# Professional Dark Mode Studio Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Microstock AI Studio into a unified, high-precision dark workstation UI/UX (Linear / Figma / Blackmagic DaVinci caliber), eliminating light mode while preserving 100% of functional capabilities.

**Architecture:** Pure dark mode design system in `microstock/ui_components.py` with deep obsidian surfaces (`#0A0D14`, `#101622`, `#161F30`), crisp borders (`#1E2A42`), WCAG AAA typography, and streamlined multi-column layouts across all three studio tabs in `app.py`.

**Tech Stack:** Python 3.9+, Streamlit, Custom Studio CSS, Real-ESRGAN Vulkan NCNN, Google Gemini GenAI SDK.

**Spec:** Current codebase (`app.py`, `microstock/ui_components.py`), `PRODUCT.md`, `DESIGN.md`.

## Global Constraints

- **Strict Dark Theme Only:** Remove light-mode toggle and conditional theme code; lock to Dark Studio Palette.
- **Zero Functional Regressions:** All existing buttons, callbacks, session_state variables, prompt generation, vision SEO, upscaling, and export mechanisms must remain identical in behavior.
- **Microstock Compliance Standards:** Maintain clear labeling for Adobe Stock (≥ 4 MP / 300 DPI) and Freepik (≥ 4 MB).
- **A11y / Contrast:** All text must meet WCAG AA (≥ 4.5:1 for body, ≥ 3.0:1 for large/badges), with primary text exceeding 14:1 against dark surfaces.
- **Clean Copywriting:** Zero em dashes (`—`), zero generic AI marketing slop ("magic", "revolutionary"); crisp technical terminology only.

## Review Focus

1. **Sidebar API Key & Settings:** Verify key input, test status, model dropdowns, and cache clearing remain fully operational.
2. **Tab 1 Prompt Formulation:** Verify trend analyzer, 18-style selection, aspect ratios, prompt generation, and copy-prompt features work seamlessly.
3. **Tab 2 Vision SEO & Upscaler:** Verify Downloads folder scanning, drag-and-drop upload, Smart Microstock / Ultra 4x mode selection, batch vision analysis, ZIP/CSV export, and local disk save.
4. **Tab 3 Reverse Prompt:** Verify reference image upload, optical deconstruction via Gemini Vision, and text formula export.
5. **Layout Responsiveness:** Verify desktop (1280px+), laptop (1024px), and tablet/split-window layouts reflow gracefully with minimum 44px tap targets.

---

### Task 1: Refactor Design System to Pure Pro Dark Mode
**Files:**
- Modify: `microstock/ui_components.py`
- Modify: `DESIGN.md`

- [ ] **Step 1:** In `microstock/ui_components.py`, remove light mode conditional logic from `get_modern_css()`. Lock token variables to refined Dark Obsidian palette:
  - Global background: `#0A0D14`
  - Card / Panel background: `#101622`
  - Input / Sub-surface background: `#151E30`
  - Elevated card / hover: `#1A253C`
  - Borders: `#1E2A42` (default), `#2A3B5C` (hover), `#3B82F6` (focus)
  - Typography: `#F8FAFC` (primary, 17.5:1), `#94A3B8` (secondary, 6.8:1), `#60A5FA` (accent, 7.9:1)
  - Semantic status badges: Emerald `#10B981`, Amber `#F59E0B`, Rose `#EF4444`, Cyan `#06B6D4`
- [ ] **Step 2:** Refine component styling:
  - Sleek studio tabs with subtle top border indicator and active accent illumination.
  - Enhanced code blocks with custom dark surface (`#0D121D`), crisp monospaced font, and distinct copy buttons.
  - Card depth with subtle gradient border glow (`box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.45)`).
  - Explicit 44px touch targets on all interactive elements.
- [ ] **Step 3:** Replace `render_theme_toggle()` with a static, elegant studio status badge (`Studio Dark Pro · Hardware Accelerated`).
- [ ] **Step 4:** Update `DESIGN.md` to reflect pure Dark Mode Studio specification.

---

### Task 2: Redesign Sidebar & Global Studio Header
**Files:**
- Modify: `microstock/ui_components.py`
- Modify: `app.py`

- [ ] **Step 1:** In `microstock/ui_components.py`, modernize `render_header()`:
  - Transform hero banner into a sleek, compact studio command bar.
  - Display workstation status chips: `⚡ Vulkan NCNN Active`, `🎯 Adobe Stock & Shutterstock Compliant`, `🔒 100% Local RAM Processing`.
- [ ] **Step 2:** In `microstock/ui_components.py`, modernize `render_sidebar()`:
  - Clean visual grouping with section headers: `// ENGINE ACCESS`, `// HARDWARE & AI MODELS`, `// UTILITIES & EXPORTS`.
  - Polished API key status indicator (🟢 Connected / 🟡 Key Required).
  - Streamlined cache clearing and local export directory indicator.
- [ ] **Step 3:** In `app.py`, remove all references to `is_dark` toggle and pass static dark theme configuration.

---

### Task 3: Redesign Tab 1 (Prompt Generator Studio)
**Files:**
- Modify: `app.py`

- [ ] **Step 1:** Modernize layout composition:
  - Left column: Parameter controls organized in structured studio modules (Subject & Concept, Style Engine, Composition & Lighting).
  - Right column: Studio Trend Radar & Real-Time Prompt Output Card.
- [ ] **Step 2:** Redesign the Trend Discovery Radar:
  - Compact soundboard style with demand status chips (`🔥 High Demand`, `⭐ Rising Niche`).
  - Sleek 1-click apply trigger button with immediate visual feedback.
- [ ] **Step 3:** Redesign the Generated Prompt Display:
  - High-readability technical card with syntax-highlighted visual sections (Core Subject, Lighting/Camera Specs, Negative Prompt, Aspect Ratio chip).
  - Prominent 1-click copy action with tactile button styling.

---

### Task 4: Redesign Tab 2 (Inspection, Upscale & Vision SEO Studio)
**Files:**
- Modify: `app.py`

- [ ] **Step 1:** Reorganize the workflow into a logical 3-stage visual pipeline:
  - **Stage 1 (Source Input):** High-tech segmented controller for choosing between Auto-Scan Downloads and Manual File Dropzone.
  - **Stage 2 (Processing Matrix):** Consolidated microstock parameter card with upscale mode chips (`Smart Microstock ~8 MP` vs `Ultra 4x`) and Freepik 4MB toggle.
  - **Stage 3 (Batch Operations & Action Hub):** High-visibility batch start CTA button with real-time hardware status.
- [ ] **Step 2:** Modernize Results & Export Hub:
  - Card-based asset review grid with high-contrast metadata display (Title, Description, Category badges, 50-Keyword interactive cloud).
  - Unified Export Action Deck with quick buttons: Download Master ZIP, Download CSV, Open Local Export Folder.

---

### Task 5: Redesign Tab 3 (Reverse Prompt Studio)
**Files:**
- Modify: `app.py`

- [ ] **Step 1:** Modernize layout with a dual-pane studio layout:
  - Left: Reference image dropzone with instant RAM preview.
  - Right: Deconstructed prompt formula card with separated layers (Subject, Style, Optics, Commercial Formula).
- [ ] **Step 2:** Clean action buttons for 1-click prompt copying and direct transfer to Tab 1.

---

### Task 6: Verification & Automated Pipeline Tests
**Files:**
- Run: `tests/test_pipeline.py`
- Run: Manual smoke test of imports and Streamlit components

- [ ] **Step 1:** Execute test suite: `.venv/bin/python3 -m unittest discover tests` to ensure 100% of pipeline math and image processing functions pass.
- [ ] **Step 2:** Validate `app.py` compilation and import without errors.
- [ ] **Step 3:** Verify contrast compliance using WCAG AA/AAA checker formulas across all modified color tokens.
