# Visual-First Media Studio Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely rebuild the front-end interface of Microstock AI Studio from the ground up using the **Visual-First Media Studio** design system (Behance Pro / Figma Studio aesthetic) while preserving 100% of the underlying business logic, state handling, and processing pipelines.

**Reference Specification:** [docs/superpowers/specs/2026-10-29-visual-first-media-studio-design.md](file:///Users/ryanrusnanda/Documents/Antigravity/microstock-ai-studio/docs/superpowers/specs/2026-10-29-visual-first-media-studio-design.md)

---

## 1. File Structure & Responsibilities

- **`microstock/ui_components.py`**:
  - `get_modern_css()`: Complete CSS design token rewrite for OLED Dark Studio (`#06080D` canvas, `#0B0F19` cards, frosted glass accents, high-contrast typography, styled buttons, responsive containers).
  - `render_header()`: Cinematic studio title, hardware status pill, and commercial compliance badges.
  - `render_sidebar()`: Sleek creator sidebar with API key input, live engine status badges, and microstock cheat sheet.
  - `render_results_grid()`: Redesigned visual inspection cards with image thumbnails, dimension metrics, and 50 interactive SEO tag chips.
- **`app.py`**:
  - Tab 1: Commercial Prompt Studio layout (two-column formulation workbench & 5-archetype prompt cards).
  - Tab 2: Visual Inspection & Microstock Pack layout (Auto-Sync card, upload dropzone, upscale panel, and download hub).
  - Tab 3: Reverse Prompt layout (side-by-side deconstruction cards).
- **`tests/test_pipeline.py` & `tests/test_prompt_enhancer.py`**:
  - Regression verification across all 13 existing unit tests.

---

## 2. Tasks

### Task 1: Rebuild CSS Design System & Core Components in `microstock/ui_components.py`
**Files:**
- Modify `microstock/ui_components.py`

- [ ] **Step 1.1:** Write the new OLED Visual-First CSS tokens and styling in `get_modern_css()`.
- [ ] **Step 1.2:** Update `render_header()` with the new cinematic branding header and hardware status indicators.
- [ ] **Step 1.3:** Update `render_sidebar()` with the sleek creator configuration drawer.
- [ ] **Step 1.4:** Update `render_results_grid()` to format output inspection cards with thumbnail previews and tag pills.
- [ ] **Step 1.5:** Run unit tests to verify no regressions in helper functions.

### Task 2: Redesign Tab 1 (Commercial Prompt Studio) in `app.py`
**Files:**
- Modify `app.py`

- [ ] **Step 2.1:** Rebuild Tab 1 banner and layout into a balanced two-column canvas.
- [ ] **Step 2.2:** Structure the left panel (concept textarea, style pills, camera/lighting/ratio controls, and primary action button).
- [ ] **Step 2.3:** Structure the right panel (5 visual archetype cards with colored badges, code containers, and quick Gemini Web link).
- [ ] **Step 2.4:** Verify all existing session state keys remain identical (`tab1_base_idea`, `enhanced_prompt`, etc.).

### Task 3: Redesign Tab 2 (Visual Inspection & Microstock Pack) in `app.py`
**Files:**
- Modify `app.py`

- [ ] **Step 3.1:** Rebuild Tab 2 header card with inspection summary and status pills.
- [ ] **Step 3.2:** Rebuild Section 1: Auto-Sync Folder Watcher card and drag-and-drop manual uploader.
- [ ] **Step 3.3:** Rebuild Section 2: Microstock Resolution & Upscale Panel (Smart Microstock ~8 MP vs Ultra 4x, Freepik 4MB checkbox).
- [ ] **Step 3.4:** Rebuild Section 3: Processing progress tracker, master ZIP/CSV download hub, and dataframe table view.
- [ ] **Step 3.5:** Verify all existing session state keys and callback routines remain intact.

### Task 4: Redesign Tab 3 (Reverse Prompt Studio) in `app.py`
**Files:**
- Modify `app.py`

- [ ] **Step 4.1:** Rebuild Tab 3 header card and image dropzone.
- [ ] **Step 4.2:** Rebuild reverse prompt result cards (original visual thumbnail on the left, commercial prompt code block on the right, and 1-click "Kirim ke Tab 1" button).
- [ ] **Step 4.3:** Verify state handoff between Tab 3 and Tab 1.

### Task 5: End-to-End Verification & Suite Testing
**Files:**
- All touched files

- [ ] **Step 5.1:** Run entire test suite `python3 -m unittest discover tests` (must pass 13/13 tests).
- [ ] **Step 5.2:** Test run `app.py` import and syntax check (`python3 -c "import app"`).
- [ ] **Step 5.3:** Commit changes to git with conventional commit message.
