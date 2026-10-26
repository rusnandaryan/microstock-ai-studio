# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Microstock contributors, visual artists, and AI creators producing and licensing commercial visual assets on international stock marketplaces, specifically:
- **Adobe Stock** (Contributor portal)
- **Shutterstock** (Contributor marketplace)
- **Freepik / Vecteezy** (Commercial vector and photography contributor tracks)

The primary user's job is transforming visual concepts into high-demand, commercial-grade stock assets, upscaling them to meet strict marketplace pixel/byte thresholds, and tagging them with 50 rejection-free SEO keywords without copyright or trademark rejections.

## Product Purpose

Microstock AI Studio streamlines and accelerates the end-to-end contributor pipeline. It eliminates marketplace rejections by automating commercial prompt formulation, providing local hardware-accelerated upscaling, and structuring 50 sorted, brand-sanitized metadata keywords ready for instant CSV/ZIP batch upload.

Success means zero review rejections on technical resolution, trademark violations, or spam keywords, while significantly reducing manual tagging time.

## Positioning

Unlike generic AI generators (which output 1024x1024 images lacking commercial metadata, containing recognizable brand trademarks and faces requiring releases), Microstock AI Studio is a dedicated commercial stock workflow engine that guarantees:
- Automated adherence to strict marketplace resolution standards (≥ 4 MP / 300 DPI) and physical file size options (≥ 4 MB).
- Hard commercial moderation rules (Zero-female commercial protocol, faceless angles, copy space reservation, and die-cut knolling cutlines).
- 50 rejection-free, brand-sanitized keywords sorted by commercial relevance in standard stock CSV format.
- Zero cloud upscaling costs via local GPU Vulkan execution.

## Operating Context

- **Workflow:** 3 isolated modular studios:
  1. *Prompt Generator Studio (Text to Prompt):* Dynamic Adobe Stock market trend discovery and multi-style prompt formulation.
  2. *Inspection, Upscale & SEO Studio (Vision & Auto-Cleanup):* Automated Downloads folder watcher, RAM-only previewing, Vulkan Real-ESRGAN NCNN upscaling, and 50-keyword CSV batch packaging.
  3. *Reverse Prompt Studio (Image to Prompt):* Optical deconstruction of reference imagery saving formulas directly to `.txt`.
- **Environment:** Local desktop workstation (macOS Apple Silicon & Intel / Windows) running a Streamlit interface paired with a high-conversion landing page.
- **Hardware Integration:** Real-ESRGAN Vulkan NCNN running directly on the user's local GPU without cloud transmission.

## Capabilities and Constraints

- **Local Execution First:** Heavy visual upscaling executes entirely on local GPU hardware; image inspection operates in memory (RAM-only) without filling disk space unless explicitly upscaled.
- **BYOK Architecture:** Bring-your-own Gemini API key for cost-efficient Google Gemini 2.5 Flash Vision calls.
- **Universal Compliance Armor:** 7 immutable commercial rules automatically applied across all prompt compiling modules (Zero-female prohibition, trademark suppression, faceless posing, copy space reservation, knolling symmetry, authentic physics, and tactile micro-textures).
- **Download Queue Automation:** Session-window filters (15m, 30m, 1h, today) with `.crdownload` file lock detection to prevent ingesting incomplete browser downloads.

## Brand Commitments

- **Tone & Voice:** Crisp, professional, utilitarian, focused, and honest. Industrial precision over decorative AI hype.
- **Forbidden Terminology:** Zero generic AI marketing slop ("Magic", "AI-Powered", "Revolutionary"); use specific technical terminology ("Prompt Komersial", "Gemini Vision SEO", "Real-ESRGAN Vulkan").
- **Copy Standards:** Zero em dash (`—`) characters in UI copy; strict punctuation clarity with commas, colons, or clean parentheses.

## Evidence on Hand

- **Existing Workstation Codebase:** Production Streamlit application (`microstock-ai-studio/app.py`), modular engine packages (`microstock/`), and local NCNN binaries (`microstock-ai-studio/upscayl_bin`).
- **Incumbent Design System:** Documented in `microstock-ai-studio/DESIGN.md` (Dual-theme Studio Midnight `#0B0F19` / Daylight `#F8FAFC`, Space Grotesk / Plus Jakarta Sans / JetBrains Mono).
- **Production Marketing Surface:** Standalone interactive landing page (`microstock-ai-studio/landing-page.html`).

## Product Principles

1. **Deterministic Compliance Over Creative Speculation:** Every generated output must satisfy commercial microstock reviewer criteria rather than generic artistic whim.
2. **Local Hardware Sovereignty:** High-resolution upscaling belongs on the user's local GPU; users must not be taxed with cloud token markups for pixel rendering.
3. **Zero Storage Waste:** Never write temporary preview assets to the contributor's disk. Inspect in RAM, export only on approval.
4. **Complete Output Utility:** Every interactive control, prompt, or keyword array must be exportable, copyable, and directly importable into Adobe Stock, Shutterstock, or Freepik.

## Accessibility & Inclusion

- Compliance with WCAG 2.1 AA (and WCAG 2.2 AAA area focus criteria) across all web surfaces.
- Mandatory visible focus indicators (`:focus-visible` with 2px solid outline and offset).
- Minimum contrast ratio ≥ 16:1 for primary headings and ≥ 4.5:1 for all secondary copy in both dark and light modes.
