# Align Dark Mode Primary Accent Token to #2563EB for WCAG AA Contrast Compliance

Written against: 2168402

## Evidence chain

- Surface: `microstock-ai-studio/microstock/ui_components.py:33` (Dark mode CSS injection `:root { --accent-blue: ... }`)
- Problem: In dark mode, primary CTA buttons and links render `#FFFFFF` text on background `#3B82F6`, yielding a contrast ratio of 3.68:1, failing the WCAG AA minimum 4.5:1 threshold for normal text.
- Design evidence: `microstock-ai-studio/DESIGN.md:30` binds `Accent Primary: #2563EB` (contrast 5.17:1 with `#FFFFFF`).
- Owner: `microstock-ai-studio/microstock/ui_components.py`
- Scope and affected surfaces: Primary buttons (`div.stButton > button[kind="primary"]`), link buttons (`div[data-testid="stLinkButton"] > a`), and download buttons (`div[data-testid="stDownloadButton"] > button[kind="primary"]`) across Tab 1, Tab 2, Tab 3, and Sidebar in Dark Mode.
- Uncertainty: None.

## Design decision

Set `accent_blue = "#2563EB"` and `accent_blue_hover = "#1D4ED8"` in the dark mode branch of `get_modern_css()`. This resolves the contrast failure by directly aligning runtime CSS with the documented token contract in `DESIGN.md:30`, elevating primary button text contrast from 3.68:1 to 5.17:1 (passing WCAG AA).

## Reuse

- `--accent-blue`, `--accent-blue-hover`
- Exemplar: Light mode branch in `microstock-ai-studio/microstock/ui_components.py:56-57`

## Changes

1. `microstock-ai-studio/microstock/ui_components.py` (lines 33-34)
   - Change: In the `if is_dark:` block of `get_modern_css()`, replace:
     ```python
     accent_blue = "#3B82F6"
     accent_blue_hover = "#2563EB"
     ```
     with:
     ```python
     accent_blue = "#2563EB"
     accent_blue_hover = "#1D4ED8"
     ```
   - Preserve: Focus indicator border token `border_focus = "#3B82F6"`, active tab border styling, and all surrounding theme variables.
   - Verify: In Dark Mode, inspect primary button background color (`#2563EB`) with white text (`#FFFFFF`) to confirm contrast ratio is 5.17:1.

## Scope

- Inherit: All primary buttons (`kind="primary"`), link buttons (`data-testid="stLinkButton"`), and download buttons (`data-testid="stDownloadButton"`) in Dark Mode.
- Verify: Tab 1 "Generate Prompt Komersial", Tab 2 "Mulai Analisis Gambar", Tab 3 "Analisis Gambar & Buat Prompt", Sidebar "Simpan Permanen".
- Exclude: Secondary buttons and light mode theme variables (already using `#2563EB`).

## Validation

- Product: Open application in Dark Mode; all primary interactive buttons display bold, readable white text on deep royal blue.
- Interface: Check Tab 1, Tab 2, Tab 3, and Sidebar in Dark Mode across desktop and mobile viewports.
- System: Confirm `--accent-blue` in `:root` evaluates to `#2563EB` when `is_dark=True`.
- Repository: `.venv/bin/python3 -c "import app; print('OK')"` → `OK`

## Stop conditions

- Stop if changing `accent_blue` creates unintended low-contrast pairings on dark container surfaces where blue text is used without a background.

## Design documentation

- After acceptance and validation: None required (already matches `microstock-ai-studio/DESIGN.md:30`).
