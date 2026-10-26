# Apply Monospaced Font Contract to Prompt Code Blocks

Written against: 2168402

## Evidence chain

- Surface: `microstock-ai-studio/microstock/ui_components.py:672-682` (`div[data-testid="stCode"]`)
- Problem: Code blocks displaying generated prompts omit `font-family`, falling back to standard proportional UI sans font and violating the monospaced design contract.
- Design evidence: `microstock-ai-studio/DESIGN.md:55` establishes `'JetBrains Mono', 'Fira Code', monospace` for prompts and code output.
- Owner: `microstock-ai-studio/microstock/ui_components.py`
- Scope and affected surfaces: All `st.code()` containers across Tab 1 (Magic/Commercial Prompt), Tab 2 (Metadata inspection blocks), and Tab 3 (Reverse Prompt results).
- Uncertainty: None.

## Design decision

Add `font-family: 'JetBrains Mono', 'Fira Code', monospace !important;` to the CSS selector for `div[data-testid="stCode"] pre, div[data-testid="stCode"] code, div[data-testid="stCode"] span` and import `JetBrains Mono` in the Google Fonts `@import` declaration. This fulfills the typography contract, providing clear character distinction and technical precision when reading and copying commercial prompts.

## Reuse

- Font family: `'JetBrains Mono', 'Fira Code', monospace`
- Exemplar: `microstock-ai-studio/DESIGN.md:55`

## Changes

1. `microstock-ai-studio/microstock/ui_components.py` (line 68)
   - Change: Update Google Fonts `@import` url to include `JetBrains+Mono`:
     ```css
     @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap');
     ```
   - Preserve: Existing `Plus Jakarta Sans` and `Space Grotesk` font imports.
   - Verify: Network imports load `JetBrains Mono` font faces.

2. `microstock-ai-studio/microstock/ui_components.py` (lines 672-682)
   - Change: In the `div[data-testid="stCode"] pre, div[data-testid="stCode"] code, div[data-testid="stCode"] span` rule, add:
     ```css
     font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
     ```
   - Preserve: `white-space: pre-wrap !important;`, `word-break: break-word !important;`, `font-size: 0.92rem !important;`, `line-height: 1.6 !important;`, and `color: var(--text-primary) !important;`.
   - Verify: In Tab 1, Tab 2, and Tab 3, code boxes render with monospaced letterforms.

## Scope

- Inherit: All `st.code()` outputs across Tab 1, Tab 2, and Tab 3.
- Verify: Tab 1 prompt copy box, Tab 2 metadata inspect card expanders, Tab 3 reverse prompt copy boxes.
- Exclude: Form text inputs, textareas, and standard markdown paragraphs.

## Validation

- Product: User generates a prompt in Tab 1 or Tab 3; prompt text displays in a monospaced font with distinct punctuation and letter spacing.
- Interface: Test prompt code blocks with long prompts and multi-line formatting across desktop and mobile.
- System: Inspect computed styles of `div[data-testid="stCode"] code` in browser devtools; confirms font family resolves to `JetBrains Mono`.
- Repository: `.venv/bin/python3 -c "import app; print('OK')"` → `OK`

## Stop conditions

- Stop if code font change causes unexpected container overflow or clips the copy-to-clipboard button.

## Design documentation

- After acceptance and validation: None required (already matches `microstock-ai-studio/DESIGN.md:55`).
