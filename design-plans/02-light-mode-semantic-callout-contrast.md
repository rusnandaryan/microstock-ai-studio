# Replace Hardcoded Inline Callout Colors with Theme-Aware Semantic Badge Classes

Written against: 2168402

## Evidence chain

- Surface: `microstock-ai-studio/app.py:117` (Tab 1 trend period banner) and `microstock-ai-studio/app.py:650` (Tab 3 reference image notice)
- Problem: Inline style declarations hardcode text colors `color:#10B981` (yielding 2.42:1 contrast against light canvas `#F8FAFC`) and `color:#F59E0B` (yielding 2.05:1 contrast against light canvas `#F8FAFC`), failing the WCAG AA minimum 4.5:1 contrast requirement in Light Mode.
- Design evidence: `microstock-ai-studio/DESIGN.md:20` mandates that all text pairings exceed 4.5:1 contrast. `DESIGN.md:44-47` and `ui_components.py:265-275` define semantic classes `.ms-badge-green` (`#047857` in light mode, 5.24:1) and `.ms-badge-amber` (`#B45309` in light mode, 4.80:1).
- Owner: `microstock-ai-studio/app.py`
- Scope and affected surfaces: Tab 1 trend analysis period banner (`app.py:117`) and Tab 3 reference file callout box (`app.py:650`).
- Uncertainty: None.

## Design decision

Replace hardcoded inline color hexes with theme-aware classes `.ms-badge-green` and `.ms-badge-amber` (or dynamic theme tokens). This ensures that in Light Mode, green text renders as `#047857` (5.24:1 contrast) and amber text renders as `#B45309` (4.80:1 contrast), fully conforming to the WCAG AA contract.

## Reuse

- Classes: `.ms-badge-green`, `.ms-badge-amber`, `.ms-step-badge`
- Exemplar: `microstock-ai-studio/microstock/ui_components.py:261-275`

## Changes

1. `microstock-ai-studio/app.py` (lines 114-121)
   - Change: Replace the inline banner markup:
     ```python
     <div style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:0.5rem 0.8rem; margin-bottom:0.8rem; font-size:0.88rem; font-weight:700; color:#10B981;">
       📅 Periode Analisis: {period_str} (Berdasarkan Tren Pasar Global)
     </div>
     ```
     with:
     ```python
     <div class="ms-card-modern ms-badge-green" style="display:inline-block; padding:0.5rem 0.85rem; margin-bottom:0.8rem; font-size:0.88rem; font-weight:700;">
       📅 Periode Analisis: {period_str} (Berdasarkan Tren Pasar Global)
     </div>
     ```
   - Preserve: Message text and calendar emoji.
   - Verify: In Light Mode, text color is `#047857` (contrast $\ge$ 5.2:1). In Dark Mode, text color is `#34D399` (contrast $\ge$ 8.9:1).

2. `microstock-ai-studio/app.py` (lines 648-655)
   - Change: In the Tab 3 reference file callout container:
     Replace `<b style="color:#F59E0B;">📌 {len(ref_entries)} gambar referensi siap dianalisis.</b>`
     with `<b class="ms-step-badge ms-badge-amber" style="font-size:0.88rem; margin-bottom:0.3rem;">📌 {len(ref_entries)} gambar referensi siap dianalisis.</b>`
   - Preserve: File processing notice paragraph and surrounding container.
   - Verify: In Light Mode, heading text color is `#B45309` (contrast $\ge$ 4.8:1). In Dark Mode, heading text color is `#FBBF24` (contrast $\ge$ 10.2:1).

## Scope

- Inherit: Tab 1 trend banner, Tab 3 reference file notice.
- Verify: Tab 1 expander, Tab 3 file uploader.
- Exclude: Static badges already using `.ms-badge-green` / `.ms-badge-amber` in `render_header()` and `render_card()`.

## Validation

- Product: Switch to Light Mode; view Tab 1 trend analysis and Tab 3 file counter callouts. All text is sharp and clearly readable.
- Interface: Both Light Mode and Dark Mode toggled in Sidebar.
- System: Confirm no inline `color:#10B981` or `color:#F59E0B` remains in `app.py`.
- Repository: `.venv/bin/python3 -c "import app; print('OK')"` → `OK`

## Stop conditions

- Stop if callout layout breaks on mobile breakpoints or if CSS class inheritance is blocked by Streamlit parent container resets.

## Design documentation

- After acceptance and validation: None required (already matches `microstock-ai-studio/DESIGN.md:44-47`).
