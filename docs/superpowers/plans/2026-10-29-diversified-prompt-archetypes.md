# Diversified Prompt Archetypes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the prompt enhancement engine to generate 5 visually distinct, non-repetitive microstock prompts mapped to 5 commercial photography archetypes, eliminating duplicate-content rejections on Adobe Stock and Shutterstock.

---

## 1. Problem Statement & Architecture

### The Problem
Currently, `microstock/prompt_enhancer.py` supplies Gemini with a single uniform prompt instruction that asks for "5 alternative prompts" without enforcing variance in composition, distance, angle, or purpose. Gemini generates five near-identical variations of the same scene. When contributors generate images and upload them, microstock review algorithms flag and reject the batch as **"Similar Content / Spam"**.

### The Solution: 5 Commercial Visual Archetypes
We define 5 distinct microstock shot archetypes that every generation run MUST deliver:
1. **Shot 1: Wide Environmental Context** (`Wide Context & Environment`) – Subject situated in its realistic, wider setting or architectural context.
2. **Shot 2: Extreme Close-Up / Macro Craftsmanship** (`Macro & Material Detail`) – Tight detail, micro-textures, material grain, shallow depth of field (f/1.8 - f/2.8).
3. **Shot 3: Dynamic Interaction / In-Use Action** (`In-Use Interaction / Action`) – Dynamic function, active process, or practical interaction (strictly faceless, hands/tools only).
4. **Shot 4: Commercial Copy Space Layout** (`Clean Copy Space / Ad Layout`) – 40-50% uncluttered negative space reserved for graphic design headline copy.
5. **Shot 5: Geometric Composition / Top-Down Flat Lay** (`Flat Lay Knolling / Alternative Angle`) – 90° overhead flat lay with knolling props, or dramatic low-angle perspective.

---

## 2. Proposed File Changes

- **`microstock/prompt_enhancer.py`**:
  - Update `ENHANCER_SYSTEM_INSTRUCTION` to define the 5-shot diversification matrix.
  - Define `PROMPT_ARCHETYPES` constant with labels and badges.
  - Upgrade output schema to parse JSON with `archetype` and `prompt`, with backward-compatible fallback for string lists.
  - Update `build_enhancer_input` to mandate the 5 archetypes explicitly.
- **`app.py`**:
  - Update Tab 1 rendering to display archetype badges (e.g. `🌐 Wide Context`, `🔍 Macro Detail`, `⚡ In-Use Action`, `📐 Copy Space Ready`, `🧩 Flat Lay Knolling`) for each generated prompt card.
- **`tests/test_prompt_enhancer.py`**:
  - Add unit tests for prompt parsing, archetype fallback assignment, and aspect ratio formatting.

---

## 3. Tasks

### Task 1: Add Unit Tests for Prompt Enhancer Parser & Archetypes
**Files:**
- Create `tests/test_prompt_enhancer.py`
- Modify `microstock/prompt_enhancer.py` (add `PROMPT_ARCHETYPES` constant and parsing logic)

- [x] **Step 1.1:** Write unit tests in `tests/test_prompt_enhancer.py` covering:
  - Parsing structured JSON `[{"archetype": "...", "prompt": "..."}]`
  - Parsing legacy string JSON `["prompt1", "prompt2", ...]` with automatic fallback to the 5 archetypes.
  - Aspect ratio formatting verification (`[Aspect Ratio: 16:9]`).
- [x] **Step 1.2:** Run `python3 -m unittest discover tests` and verify tests fail or run as expected.
- [x] **Step 1.3:** Implement `PROMPT_ARCHETYPES` and parse helper in `microstock/prompt_enhancer.py`.
- [x] **Step 1.4:** Re-run unit tests and ensure they pass.

### Task 2: Implement 5-Shot Diversification Matrix in System Instructions
**Files:**
- Modify `microstock/prompt_enhancer.py`

- [x] **Step 2.1:** Update `ENHANCER_SYSTEM_INSTRUCTION` with explicit requirements for each of the 5 archetypes.
- [x] **Step 2.2:** Update `build_enhancer_input` to structure the request around the 5 archetypes.
- [x] **Step 2.3:** Ensure strict compliance with existing safety rules (zero women, faceless only, zero text, no brands).

### Task 3: Update Workstation UI in `app.py`
**Files:**
- Modify `app.py`

- [x] **Step 3.1:** Update Tab 1 prompt results display to show archetype name, visual badge, and copy button.
- [x] **Step 3.2:** Verify UI responsiveness and dark mode styling.

### Task 4: End-to-End Verification
**Files:**
- All touched files

- [x] **Step 4.1:** Run entire test suite `python3 -m unittest discover tests`.
- [x] **Step 4.2:** Test run `app.py` syntax and import check.
- [x] **Step 4.3:** Commit changes to git with conventional commit message.

