# DESIGN.md — Microstock AI Studio

> **Brand Identity:** Playful Neo-Pop Creative Studio  
> **Target Audience:** Microstock contributors, visual artists, and AI content creators selling on Adobe Stock, Shutterstock, and Freepik.  
> **Personality:** Joyful, tactile, high-energy, confident, crisp, and crafted.  
> **Core Rule:** Strictly governed by `antislop-ui` and `antislop.md` (no generic AI purple-blue gradients, no mushy floating shadows, no endless pulsing dots, no decorative emoji slop).

---

## 1. Dials Configuration

- **ENERGY: 3** — Bold graphic character, high-contrast borders, punchy warm color accents, tactile surfaces.
- **RHYTHM: 3** — Dynamic layout rhythm, asymmetrical tool panels, distinctive card elevations and focal zones.
- **MOTION: 2** — Purposeful interactive states only: tactile button depressions (`transform: translate(2px, 2px)`), crisp hover elevations, clean tab switches. Zero endless loops or dizzying background animations.

---

## 2. Color System

| Token | Hex Code | Role | Purpose & Usage |
| :--- | :--- | :--- | :--- |
| **Ink Base** | `#1A191E` | Typography & Borders | Ultra-sharp readability, 2px tactile outline borders, crisp contrast (15:1+ against light). |
| **Paper Canvas** | `#F8F6F0` | Global Background | Warm organic parchment tone, welcoming and easy on the eyes. |
| **Card Pure** | `#FFFFFF` | Component Surfaces | High-contrast content containers with solid 2px ink borders. |
| **Electric Coral** | `#FF5436` | Primary Action Core | Primary CTAs ("Generate Magic Prompt", "Analisis Gambar"), focal action points. |
| **Sunny Marigold** | `#FFC837` | Creative Accent | Visual style tags, tip callouts, highlight accents. |
| **Mint Lagoon** | `#00C48C` | Success & Utility | Ready status, export downloads, compliant resolution tags (>= 4MP). |
| **Cobalt Royal** | `#2962FF` | Link & Navigation | External links (gemini.google.com), code copy interactions. |

*Palette constraint:* No more than 3 core colors + 1 deliberate accent per view. Zero generic purple-cyan gradients.

---

## 3. Tactile Neo-Pop Component Geometry

- **Borders:** Crisp `2px solid #1A191E` on cards, inputs, and primary buttons.
- **Shadows:** Hard offset shadows (`3px 3px 0px #1A191E` and `5px 5px 0px #1A191E`) instead of blurred floating clouds.
- **Radius Scale:**
  - Cards & Containers: `16px`
  - Buttons & Inputs: `10px`
  - Tags & Badges: `8px` (never pill-everything 999px slop).
- **Interactive Feedback:**
  - Hover: Lift up `translate(-2px, -2px)` with shadow expanding to `6px 6px 0px #1A191E`.
  - Active / Click: Push down `translate(2px, 2px)` with shadow collapsing to `1px 1px 0px #1A191E`.

---

## 4. Purpose Test Matrix (antislop R-01, R-05, R-10, R-11, R-12, R-13, R-19)

| UI Component | Purpose & Job | Slop Pattern Banned | Neo-Pop Solution |
| :--- | :--- | :--- | :--- |
| **Header Banner** | Immediately communicate studio mission & 2-step workflow. | Generic purple gradient & blurry glowing badges. | Warm cream canvas, bold ink typography, clean badge pills with real count & status. |
| **Sidebar** | Manage Gemini API key safely on local machine and provide essential guidelines. | Monotonous grey box with decorative icons. | Crisp card with solid tactile save/delete buttons and clear masked status. |
| **Tab 1: Magic Prompt** | Input concept, dial in 4 photo parameters, copy prompt in 1-click. | Monotonous form, hidden outputs. | Asymmetric 2-column layout: tactile studio knobs on left, high-contrast prompt display with direct copy & Gemini link on right. |
| **Tab 2: Vision & SEO** | Upload generated images, inspect visual elements, download zip/csv. | Template dashboard cards with fake stats. | Visual upload dropzone, live thumbnail grid with actual MP resolution calculations and 1-click export hub. |
| **Result Cards** | Display generated image preview, resolution MP verification, and 50 SEO keywords. | Identical uniform cards with mushy drop-shadows. | Distinctive tactile frame with 300 DPI microstock compliance badges and expandable metadata tables. |
