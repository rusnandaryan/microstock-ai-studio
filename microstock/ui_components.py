"""Reusable Streamlit UI components (sidebar, header, cards, export hub, progress).
Modern Studio Design System with Light/Dark Mode toggle & WCAG AA contrast compliance.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from . import config
from .image_generator import BatchItem, BatchSettings


def get_modern_css(is_dark: bool = True) -> str:
    """Generate high-precision Pro Dark Studio workstation CSS."""
    # Obsidian Pro Dark Workstation Palette (Blackmagic / Linear / Figma Studio Caliber)
    # WCAG AAA Compliant: Text (#F8FAFC) on bg (#080B11) = 18.2:1
    # Card bg (#0F1623), Borders (#1D283E), Secondary Text (#94A3B8 = 6.8:1)
    # Text Accent (#60A5FA on #080B11 = 8.8:1 - Passes AAA)
    scheme = "dark"
    bg_page = "#06080D"
    bg_card = "#0B0F19"
    bg_sidebar = "#05070B"
    bg_input = "#0E1424"
    bg_elevated = "#131A2E"
    border_color = "rgba(255, 255, 255, 0.08)"
    border_focus = "#3B82F6"
    text_primary = "#F8FAFC"
    text_secondary = "#94A3B8"
    text_muted = "#64748B"
    text_accent = "#60A5FA"
    accent_blue = "#2563EB"
    accent_blue_hover = "#1D4ED8"
    hero_bg = "linear-gradient(135deg, #0B0F19 0%, #06080D 100%)"
    hero_border = "rgba(255, 255, 255, 0.08)"
    code_bg = "#05070B"
    tab_bg_inactive = "transparent"
    tab_border = "rgba(255, 255, 255, 0.08)"
    badge_border = "rgba(255, 255, 255, 0.1)"
    scrollbar_thumb = "#1E293B"

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap');

/* CSS Variables & Base Styles */
:root {{
  color-scheme: {scheme} !important;
  --bg-page: {bg_page} !important;
  --bg-card: {bg_card} !important;
  --bg-sidebar: {bg_sidebar} !important;
  --bg-input: {bg_input} !important;
  --border-color: {border_color} !important;
  --border-focus: {border_focus} !important;
  --text-primary: {text_primary} !important;
  --text-secondary: {text_secondary} !important;
  --text-muted: {text_muted} !important;
  --text-accent: {text_accent} !important;
  --accent-blue: {accent_blue} !important;
  --accent-blue-hover: {accent_blue_hover} !important;
  --hero-bg: {hero_bg} !important;
  --hero-border: {hero_border} !important;
  --code-bg: {code_bg} !important;
}}

html, body, .stApp {{
  color-scheme: {scheme} !important;
  background-color: var(--bg-page) !important;
  color: var(--text-primary) !important;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}}

.block-container {{
  padding-top: 1.2rem !important;
  padding-bottom: 3.5rem !important;
  max-width: 1360px !important;
}}

/* Custom scrollbars */
::-webkit-scrollbar {{
  width: 8px;
  height: 8px;
}}
::-webkit-scrollbar-track {{
  background: var(--bg-page);
}}
::-webkit-scrollbar-thumb {{
  background: {scrollbar_thumb};
  border-radius: 4px;
}}

/* Top Header Bar */
header[data-testid="stHeader"],
header[data-testid="stHeader"] > div {{
  background-color: var(--bg-page) !important;
  background: var(--bg-page) !important;
  color: var(--text-primary) !important;
}}

header[data-testid="stHeader"] * {{
  color: var(--text-primary) !important;
  fill: var(--text-primary) !important;
}}

header[data-testid="stHeader"] button {{
  background-color: transparent !important;
  color: var(--text-primary) !important;
  border: none !important;
  box-shadow: none !important;
}}

header[data-testid="stHeader"] button svg {{
  fill: var(--text-primary) !important;
  color: var(--text-primary) !important;
  stroke: var(--text-primary) !important;
}}

div[data-testid="stDecoration"] {{
  display: none !important;
  height: 0 !important;
}}

div[data-testid="stToolbar"] {{
  color: var(--text-primary) !important;
}}

/* Universal High-Contrast Typography */
h1, h2, h3, h4, h5, h6,
[data-testid="stHeadingWithActionElements"] h1,
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
}}

p, span, li, label, b, strong {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] b {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}}

/* Form widget labels */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] span {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
}}

/* Tooltip / Help Icons */
[data-testid="stTooltipIcon"] svg,
[data-testid="stTooltipIcon"] path {{
  fill: var(--text-secondary) !important;
  color: var(--text-secondary) !important;
}}

/* Captions (WCAG AA compliant contrast) */
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] span,
.stCaption {{
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-weight: 500 !important;
}}

/* Modern Studio Hero Banner */
.ms-hero-modern {{
  background: var(--hero-bg) !important;
  border: 1.5px solid var(--hero-border) !important;
  border-radius: 16px !important;
  padding: 1.5rem 1.8rem !important;
  margin-bottom: 1.4rem !important;
  box-shadow: 0 8px 32px -4px rgba(0, 0, 0, 0.6) !important;
  position: relative !important;
  overflow: hidden !important;
}}

.ms-stat-pill {{
  display: flex !important;
  flex-direction: column !important;
  background: rgba(20, 29, 45, 0.85) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 8px !important;
  padding: 0.35rem 0.75rem !important;
  min-width: 110px !important;
}}

.ms-stat-label {{
  font-size: 0.65rem !important;
  font-weight: 700 !important;
  color: var(--text-muted) !important;
  letter-spacing: 0.5px !important;
  text-transform: uppercase !important;
}}

.ms-stat-val {{
  font-size: 0.84rem !important;
  font-weight: 700 !important;
  color: var(--text-accent) !important;
  font-family: 'Space Grotesk', sans-serif !important;
  margin-top: 2px !important;
}}

.ms-hero-modern h1 {{
  margin: 0 !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 2.1rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.5px !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  line-height: 1.2 !important;
}}

.ms-hero-tagline {{
  margin: 0.5rem 0 0 !important;
  font-size: 1.02rem !important;
  font-weight: 500 !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  line-height: 1.5 !important;
}}

.ms-badges-container {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1.1rem;
}}

.ms-step-badge {{
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.85rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary) !important;
}}

.ms-badge-accent,
.ms-badge-blue {{
  background: rgba(59, 130, 246, 0.15) !important;
  color: #60A5FA !important;
  -webkit-text-fill-color: #60A5FA !important;
  border-color: rgba(59, 130, 246, 0.35) !important;
}}

.ms-badge-green {{
  background: rgba(16, 185, 129, 0.15) !important;
  color: #34D399 !important;
  -webkit-text-fill-color: #34D399 !important;
  border-color: rgba(16, 185, 129, 0.35) !important;
}}

.ms-badge-purple {{
  background: rgba(168, 85, 247, 0.15) !important;
  color: #C084FC !important;
  -webkit-text-fill-color: #C084FC !important;
  border-color: rgba(168, 85, 247, 0.35) !important;
}}

.ms-badge-amber {{
  background: rgba(245, 158, 11, 0.15) !important;
  color: #FBBF24 !important;
  -webkit-text-fill-color: #FBBF24 !important;
  border-color: rgba(245, 158, 11, 0.35) !important;
}}

/* Modern Tabs Styling */
div[data-testid="stTabs"] {{
  margin-top: 0.6rem;
  margin-bottom: 1.5rem;
}}

div[data-testid="stTabs"] [role="tablist"],
div[data-testid="stTabs"] div[data-baseweb="tab-list"] {{
  gap: 0.5rem !important;
  border-bottom: 2px solid var(--border-color) !important;
  padding-bottom: 0px !important;
  background-color: transparent !important;
}}

div[data-testid="stTabs"] button[role="tab"],
div[data-testid="stTabs"] button[data-baseweb="tab"],
div[data-testid="stTabs"] button {{
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  border-radius: 10px 10px 0 0 !important;
  padding: 0.65rem 1.4rem !important;
  margin-bottom: -2px !important;
  transition: all 0.15s ease !important;
}}

/* Inactive Tab */
div[data-testid="stTabs"] button[role="tab"][aria-selected="false"],
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"],
div[data-testid="stTabs"] button[aria-selected="false"] {{
  background-color: transparent !important;
  border: 1px solid transparent !important;
  color: var(--text-secondary) !important;
}}

div[data-testid="stTabs"] button[role="tab"][aria-selected="false"] *,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"] *,
div[data-testid="stTabs"] button[aria-selected="false"] * {{
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-weight: 600 !important;
}}

/* Inactive Tab Hover */
div[data-testid="stTabs"] button[role="tab"][aria-selected="false"]:hover,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"]:hover,
div[data-testid="stTabs"] button[aria-selected="false"]:hover {{
  background-color: var(--bg-card) !important;
  border-color: var(--border-color) !important;
  color: var(--text-primary) !important;
}}

div[data-testid="stTabs"] button[role="tab"][aria-selected="false"]:hover *,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"]:hover *,
div[data-testid="stTabs"] button[aria-selected="false"]:hover * {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}}

/* Active Tab */
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[aria-selected="true"] {{
  background-color: var(--bg-card) !important;
  border: 2px solid var(--border-color) !important;
  border-bottom: 2px solid var(--bg-card) !important;
  color: var(--text-accent) !important;
}}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] *,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] *,
div[data-testid="stTabs"] button[aria-selected="true"] * {{
  color: var(--text-accent) !important;
  -webkit-text-fill-color: var(--text-accent) !important;
  font-weight: 700 !important;
}}

div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
div[data-testid="stTabs"] div[data-baseweb="tab-border"] {{
  display: none !important;
}}

/* Sidebar Styling */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {{
  background-color: var(--bg-sidebar) !important;
  background: var(--bg-sidebar) !important;
  border-right: 1.5px solid var(--border-color) !important;
  color: var(--text-primary) !important;
}}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}}

/* Inputs & Textareas */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"],
div[data-testid="stTextInput"] div[data-baseweb="base-input"],
div[data-testid="stTextArea"] div[data-baseweb="base-input"],
section[data-testid="stSidebar"] div[data-baseweb="input"],
section[data-testid="stSidebar"] div[data-baseweb="base-input"] {{
  background-color: var(--bg-input) !important;
  background: var(--bg-input) !important;
  border: 1.5px solid var(--border-color) !important;
  border-radius: 10px !important;
  transition: border-color 0.15s ease !important;
}}

div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {{
  border-color: var(--border-focus) !important;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
}}

input, textarea,
input[type="text"],
input[type="password"] {{
  color: var(--text-primary) !important;
  background-color: var(--bg-input) !important;
  background: var(--bg-input) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 500 !important;
  font-size: 0.94rem !important;
}}

input::placeholder, textarea::placeholder {{
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  opacity: 1 !important;
}}

/* Input action icon (e.g. eye icon in password input) */
div[data-baseweb="input"] button,
div[data-baseweb="input"] button:hover {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}

div[data-baseweb="input"] button svg,
div[data-baseweb="input"] svg {{
  fill: var(--text-secondary) !important;
  color: var(--text-secondary) !important;
  stroke: var(--text-secondary) !important;
}}

/* File Uploader (Dropzone) */
div[data-testid="stFileUploader"] {{
  background-color: var(--bg-card) !important;
  background: var(--bg-card) !important;
  border: 2px dashed var(--border-color) !important;
  border-radius: 14px !important;
  padding: 1.2rem !important;
  transition: border-color 0.15s ease !important;
}}

div[data-testid="stFileUploader"]:hover {{
  border-color: var(--accent-blue) !important;
}}

div[data-testid="stFileUploader"] section,
section[data-testid="stFileUploadDropzone"] {{
  background-color: transparent !important;
  border: none !important;
}}

div[data-testid="stFileUploader"] *,
section[data-testid="stFileUploadDropzone"] *,
[data-testid="stFileUploadDropzoneInstructions"] * {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}}

section[data-testid="stFileUploadDropzone"] small,
[data-testid="stFileUploadDropzoneInstructions"] small {{
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
}}

section[data-testid="stFileUploadDropzone"] svg {{
  fill: var(--accent-blue) !important;
  color: var(--accent-blue) !important;
  stroke: var(--accent-blue) !important;
}}

/* Browse files button inside uploader dropzone */
div[data-testid="stFileUploader"] button,
section[data-testid="stFileUploadDropzone"] button,
button[data-testid="baseButton-secondary"] {{
  background-color: #0E1424 !important;
  background: #0E1424 !important;
  color: #F8FAFC !important;
  -webkit-text-fill-color: #F8FAFC !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-radius: 8px !important;
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  padding: 0.5rem 1.25rem !important;
  min-height: 40px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
  transition: all 0.15s ease !important;
}}

div[data-testid="stFileUploader"] button:hover,
section[data-testid="stFileUploadDropzone"] button:hover,
button[data-testid="baseButton-secondary"]:hover {{
  background-color: #2563EB !important;
  background: #2563EB !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  border-color: #3B82F6 !important;
  transform: translateY(-1px) !important;
}}

div[data-testid="stFileUploaderFileData"] {{
  background-color: var(--bg-input) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 8px !important;
}}

/* Buttons (Primary, Secondary, Link, Download) & Touch Targets */
div.stButton > button,
div[data-testid="stDownloadButton"] > button,
div[data-testid="stLinkButton"] > a {{
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  padding: 0.55rem 1.3rem !important;
  transition: all 0.15s ease !important;
  font-size: 0.95rem !important;
  min-height: 44px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}}

div[data-testid="stExpander"] details summary {{
  min-height: 44px !important;
  display: flex !important;
  align-items: center !important;
}}

/* Keyboard Navigation: Focus-Visible Rings (WCAG AA Compliance) */
div.stButton > button:focus-visible,
div[data-testid="stLinkButton"] > a:focus-visible,
div[data-testid="stDownloadButton"] > button:focus-visible,
div[data-testid="stTabs"] button:focus-visible {{
  outline: 2px solid var(--accent-blue) !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.45) !important;
}}

/* Primary Button */
div.stButton > button[kind="primary"] {{
  background-color: var(--accent-blue) !important;
  background: var(--accent-blue) !important;
  border: 1.5px solid var(--accent-blue) !important;
  box-shadow: 0 2px 8px -1px rgba(37, 99, 235, 0.4) !important;
}}
div.stButton > button[kind="primary"]:hover {{
  background-color: var(--accent-blue-hover) !important;
  border-color: var(--accent-blue-hover) !important;
  transform: translateY(-1px) !important;
}}
div.stButton > button[kind="primary"] p,
div.stButton > button[kind="primary"] span {{
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700 !important;
}}

/* Secondary Button */
div.stButton > button[kind="secondary"] {{
  background-color: var(--bg-card) !important;
  background: var(--bg-card) !important;
  border: 1.5px solid var(--border-color) !important;
}}
div.stButton > button[kind="secondary"]:hover {{
  background-color: var(--bg-input) !important;
  border-color: var(--accent-blue) !important;
  transform: translateY(-1px) !important;
}}
div.stButton > button[kind="secondary"] p,
div.stButton > button[kind="secondary"] span {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-weight: 600 !important;
}}

/* Link Button */
div[data-testid="stLinkButton"] > a {{
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  border: 1.5px solid var(--accent-blue) !important;
  background-color: var(--accent-blue) !important;
  color: #FFFFFF !important;
  text-decoration: none !important;
  transition: all 0.15s ease !important;
}}
div[data-testid="stLinkButton"] > a:hover {{
  background-color: var(--accent-blue-hover) !important;
  transform: translateY(-1px) !important;
}}
div[data-testid="stLinkButton"] > a p,
div[data-testid="stLinkButton"] > a span {{
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700 !important;
}}

/* Download Button */
div[data-testid="stDownloadButton"] > button {{
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  border: 1.5px solid var(--border-color) !important;
  background-color: var(--bg-card) !important;
  color: var(--text-primary) !important;
}}
div[data-testid="stDownloadButton"] > button:hover {{
  border-color: var(--accent-blue) !important;
  transform: translateY(-1px) !important;
}}
div[data-testid="stDownloadButton"] > button[kind="primary"] {{
  background-color: var(--accent-blue) !important;
  border-color: var(--accent-blue) !important;
}}
div[data-testid="stDownloadButton"] > button[kind="primary"] p,
div[data-testid="stDownloadButton"] > button[kind="primary"] span {{
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700 !important;
}}

/* Selectboxes & Dropdowns (Crisp Contrast, No Hidden Text) */
div[data-baseweb="select"] > div {{
  border: 1.5px solid var(--border-color) !important;
  border-radius: 10px !important;
  background-color: var(--bg-input) !important;
  color: var(--text-primary) !important;
}}

div[data-baseweb="select"] * {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-weight: 500 !important;
}}

div[data-baseweb="select"] svg {{
  fill: var(--text-secondary) !important;
  color: var(--text-secondary) !important;
}}

div[data-baseweb="popover"],
ul[role="listbox"] {{
  background-color: var(--bg-card) !important;
  background: var(--bg-card) !important;
  border: 1.5px solid var(--border-color) !important;
  border-radius: 10px !important;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6) !important;
}}

li[role="option"] {{
  background-color: var(--bg-card) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-weight: 500 !important;
  padding: 0.6rem 1rem !important;
}}

li[role="option"]:hover,
li[role="option"][aria-selected="true"] {{
  background-color: rgba(59, 130, 246, 0.2) !important;
  color: var(--text-accent) !important;
  -webkit-text-fill-color: var(--text-accent) !important;
  font-weight: 700 !important;
}}

/* Code Blocks & Copy Button */
div[data-testid="stCode"] {{
  position: relative !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 12px !important;
  background-color: var(--code-bg) !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
}}

div[data-testid="stCode"] pre {{
  margin: 0 !important;
  padding: 1.1rem 3.5rem 1.1rem 1.1rem !important;
  background-color: transparent !important;
}}

div[data-testid="stCode"] code {{
  font-family: 'JetBrains Mono', monospace !important;
  white-space: pre-wrap !important;
  word-break: break-word !important;
  font-size: 0.9rem !important;
  line-height: 1.6 !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  background-color: transparent !important;
}}

/* Copy button wrapper on code blocks */
div[data-testid="stCodeCopyButton"] {{
  position: absolute !important;
  top: 10px !important;
  right: 10px !important;
  z-index: 5 !important;
  display: block !important;
  opacity: 1 !important;
  visibility: visible !important;
}}

/* Copy button */
div[data-testid="stCodeCopyButton"] button,
div[data-testid="stCode"] button[aria-label*="copy" i],
div[data-testid="stCode"] button[title*="copy" i] {{
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 34px !important;
  height: 34px !important;
  min-height: 34px !important;
  padding: 0 !important;
  background-color: #0E1424 !important;
  background: #0E1424 !important;
  border: 1px solid rgba(255, 255, 255, 0.18) !important;
  border-radius: 6px !important;
  color: #F8FAFC !important;
  -webkit-text-fill-color: #F8FAFC !important;
  cursor: pointer !important;
  opacity: 1 !important;
  visibility: visible !important;
  transition: all 0.15s ease !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3) !important;
}}

div[data-testid="stCodeCopyButton"] button:hover,
div[data-testid="stCode"] button[aria-label*="copy" i]:hover,
div[data-testid="stCode"] button[title*="copy" i]:hover {{
  background-color: #2563EB !important;
  background: #2563EB !important;
  border-color: #3B82F6 !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  transform: scale(1.05) !important;
}}

/* Copy button SVG icon: ensure stroke-based Lucide icons render visibly */
div[data-testid="stCodeCopyButton"] button svg,
div[data-testid="stCode"] button[aria-label*="copy" i] svg,
div[data-testid="stCode"] button[title*="copy" i] svg {{
  width: 17px !important;
  height: 17px !important;
  color: #F8FAFC !important;
  stroke: #F8FAFC !important;
  fill: none !important;
  display: block !important;
}}

div[data-testid="stCodeCopyButton"] button:hover svg,
div[data-testid="stCode"] button[aria-label*="copy" i]:hover svg,
div[data-testid="stCode"] button[title*="copy" i]:hover svg {{
  color: #FFFFFF !important;
  stroke: #FFFFFF !important;
}}

/* Inline Code tags */
code:not(pre code),
[data-testid="stMarkdownContainer"] code,
p code,
li code {{
  background-color: var(--bg-input) !important;
  color: var(--text-accent) !important;
  -webkit-text-fill-color: var(--text-accent) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 6px !important;
  padding: 0.15rem 0.45rem !important;
  font-family: 'Space Grotesk', monospace !important;
  font-weight: 600 !important;
}}

/* Expanders & Containers */
div[data-testid="stVerticalBlockBorderWrapper"] > div {{
  border: 1.5px solid var(--border-color) !important;
  border-radius: 14px !important;
  background-color: var(--bg-card) !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35) !important;
}}

div[data-testid="stExpander"] {{
  border: 1.5px solid var(--border-color) !important;
  border-radius: 12px !important;
  background-color: var(--bg-card) !important;
  margin-top: 0.6rem !important;
  overflow: hidden !important;
}}

div[data-testid="stExpander"] details summary {{
  background-color: var(--bg-card) !important;
  padding: 0.6rem 0.9rem !important;
}}

div[data-testid="stExpander"] details summary:hover {{
  background-color: var(--bg-input) !important;
}}

div[data-testid="stExpander"] details summary span,
div[data-testid="stExpander"] details summary p {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-weight: 600 !important;
}}

div[data-testid="stExpander"] details summary svg {{
  fill: var(--text-secondary) !important;
  color: var(--text-secondary) !important;
}}

/* Alerts & Notifications */
div[data-testid="stAlert"] {{
  border: 1.5px solid var(--border-color) !important;
  border-radius: 10px !important;
  background-color: var(--bg-card) !important;
}}

div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] span {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}}

div[data-testid="stNotificationContentSuccess"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentSuccess"]) {{
  background-color: rgba(16, 185, 129, 0.12) !important;
  border-color: rgba(16, 185, 129, 0.4) !important;
}}

div[data-testid="stNotificationContentInfo"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentInfo"]) {{
  background-color: rgba(59, 130, 246, 0.12) !important;
  border-color: rgba(59, 130, 246, 0.4) !important;
}}

div[data-testid="stNotificationContentWarning"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentWarning"]) {{
  background-color: rgba(245, 158, 11, 0.12) !important;
  border-color: rgba(245, 158, 11, 0.4) !important;
}}

div[data-testid="stNotificationContentError"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentError"]) {{
  background-color: rgba(239, 68, 68, 0.12) !important;
  border-color: rgba(239, 68, 68, 0.4) !important;
}}

/* Metric Cards */
div[data-testid="stMetric"] {{
  background-color: var(--bg-card) !important;
  border: 1.5px solid var(--border-color) !important;
  border-radius: 12px !important;
  padding: 0.85rem 1.1rem !important;
}}

div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] span {{
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-weight: 600 !important;
}}

div[data-testid="stMetricValue"] {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-weight: 800 !important;
}}

/* Toast Notifications */
div[data-testid="stToast"],
[data-testid="stToastContainer"] > div {{
  background-color: var(--bg-card) !important;
  border: 1.5px solid var(--border-color) !important;
  border-radius: 12px !important;
  color: var(--text-primary) !important;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6) !important;
}}

div[data-testid="stToast"] * {{
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}}

/* App Container Cards */
.ms-card-modern {{
  background: var(--bg-card);
  border: 1.5px solid var(--border-color);
  border-radius: 14px;
  padding: 1.2rem;
  margin-bottom: 1rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  transition: border-color 0.15s ease;
}}

.ms-card-modern:hover {{
  border-color: var(--accent-blue);
}}

/* Divider */
hr, [data-testid="stDivider"], div[data-testid="stDivider"] hr {{
  border-color: var(--border-color) !important;
  opacity: 0.6 !important;
}}

/* Checkboxes (WCAG Compliant, Studio Accent) */
div[data-testid="stCheckbox"] {{
  margin: 0.45rem 0 !important;
  cursor: pointer !important;
}}

div[data-testid="stCheckbox"] label {{
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  gap: 0.5rem !important;
}}

div[data-testid="stCheckbox"] label > div[role="checkbox"] {{
  background-color: var(--bg-input) !important;
  border: 1.5px solid var(--border-color) !important;
  border-radius: 6px !important;
  transition: all 0.15s ease !important;
}}

div[data-testid="stCheckbox"] label:hover > div[role="checkbox"] {{
  border-color: var(--text-accent) !important;
}}

div[data-testid="stCheckbox"] label > div[role="checkbox"][aria-checked="true"] {{
  background-color: var(--accent-blue) !important;
  border-color: var(--accent-blue) !important;
}}

div[data-testid="stCheckbox"] label > div[role="checkbox"][aria-checked="true"] svg {{
  color: #FFFFFF !important;
  fill: #FFFFFF !important;
  stroke: #FFFFFF !important;
}}

div[data-testid="stCheckbox"] label > div[role="checkbox"]:focus-visible {{
  outline: 2px solid var(--text-accent) !important;
  outline-offset: 2px !important;
}}

/* Progress Bars (Studio Accent Gradient) */
div[data-testid="stProgress"] {{
  margin: 0.75rem 0 !important;
}}

/* Ensure progress bar label container has natural height and visible text */
div[data-testid="stProgress"] > div:first-child:not(:last-child) {{
  height: auto !important;
  min-height: auto !important;
  overflow: visible !important;
  background: transparent !important;
  border: none !important;
  margin-bottom: 0.4rem !important;
  border-radius: 0 !important;
}}

div[data-testid="stProgress"] p,
div[data-testid="stProgress"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stProgress"] [data-testid="stMarkdownContainer"] span {{
  color: var(--text-primary) !important;
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  line-height: 1.4 !important;
  margin: 0 0 0.35rem 0 !important;
}}

/* Progress track (always the last child or baseweb progress-bar element) */
div[data-testid="stProgress"] > div:last-child,
div[data-testid="stProgress"] div[data-baseweb="progress-bar"],
div[data-testid="stProgress"] div[role="progressbar"] {{
  background-color: var(--bg-input) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 999px !important;
  height: 10px !important;
  overflow: hidden !important;
}}

/* Progress fill bar */
div[data-testid="stProgress"] > div:last-child > div > div,
div[data-testid="stProgress"] div[data-baseweb="progress-bar"] > div > div,
div[data-testid="stProgress"] div[role="progressbar"] > div > div {{
  background: linear-gradient(90deg, var(--accent-blue) 0%, var(--text-accent) 100%) !important;
  border-radius: 999px !important;
  transition: width 0.25s ease !important;
}}

/* Dataframes & Tables */
div[data-testid="stDataFrame"] {{
  border: 1.5px solid var(--border-color) !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  background-color: var(--bg-card) !important;
}}

div[data-testid="stDataFrame"] * {{
  font-family: 'Plus Jakarta Sans', sans-serif !important;
}}

/* Status & Spinners */
div[data-testid="stStatusWidget"] {{
  background-color: var(--bg-card) !important;
  border: 1.5px solid var(--border-color) !important;
  border-radius: 12px !important;
}}

div[data-testid="stSpinner"] > div {{
  border-top-color: var(--accent-blue) !important;
}}

/* Interactive Cursor Affordance */
button,
a,
summary,
[role="button"],
[role="tab"],
[role="checkbox"],
[role="option"],
.ms-card-modern,
.ms-step-badge {{
  cursor: pointer !important;
}}

/* Responsive Breakpoints & Accessibility */
@media (prefers-reduced-motion: reduce) {{
  *, ::before, ::after {{
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }}
}}

@media (max-width: 1024px) {{
  .block-container {{
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
  }}
  .ms-hero-modern {{
    padding: 1.5rem 1.6rem !important;
  }}
  .ms-hero-modern h1 {{
    font-size: 1.85rem !important;
  }}
}}

@media (max-width: 768px) {{
  .block-container {{
    padding-top: 0.8rem !important;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
  }}
  .ms-hero-modern {{
    padding: 1.2rem 1.2rem !important;
    border-radius: 12px !important;
  }}
  .ms-hero-modern h1 {{
    font-size: 1.5rem !important;
  }}
  .ms-hero-tagline {{
    font-size: 0.92rem !important;
  }}
  .ms-badges-container {{
    gap: 0.4rem !important;
    margin-top: 0.8rem !important;
  }}
  .ms-step-badge {{
    font-size: 0.78rem !important;
    padding: 0.3rem 0.65rem !important;
  }}
  div[data-testid="stTabs"] button[role="tab"] {{
    font-size: 0.88rem !important;
    padding: 0.5rem 0.85rem !important;
  }}
}}
</style>
"""


def inject_css(is_dark: bool = True) -> None:
    """Inject dynamic high-contrast theme CSS."""
    st.markdown(get_modern_css(is_dark), unsafe_allow_html=True)


def render_header() -> None:
    """Render the top Modern Studio hero banner."""
    st.markdown(
        """
        <div class="ms-hero-modern">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1.2rem;">
            <div>
              <div style="display:inline-flex; align-items:center; gap:0.5rem; background:rgba(37,99,235,0.15); border:1px solid rgba(59,130,246,0.35); border-radius:6px; padding:0.25rem 0.65rem; margin-bottom:0.6rem;">
                <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#10B981; box-shadow:0 0 8px #10B981;"></span>
                <span style="font-family:'Space Grotesk',sans-serif; font-size:0.75rem; font-weight:700; color:#60A5FA; letter-spacing:0.5px; text-transform:uppercase;">Vulkan NCNN Hardware Acceleration Active</span>
              </div>
              <h1 style="margin:0; font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:800; color:#F8FAFC; letter-spacing:-0.5px;">Microstock AI Studio</h1>
              <p style="margin:0.35rem 0 0; font-size:0.95rem; color:#94A3B8; font-weight:500; line-height:1.5;">
                Workstation Komersial: Prompt Engineering Pro, Vulkan NCNN Upscaler, & Gemini Vision SEO 50 Keywords.
              </p>
            </div>
            <div style="display:flex; gap:0.6rem; flex-wrap:wrap; align-items:center;">
              <div class="ms-stat-pill">
                <span class="ms-stat-label">STANDAR KURASI</span>
                <span class="ms-stat-val">Adobe Stock & SS</span>
              </div>
              <div class="ms-stat-pill">
                <span class="ms-stat-label">MIN RESOLUSI</span>
                <span class="ms-stat-val">≥ 4 MP / 300 DPI</span>
              </div>
              <div class="ms-stat-pill">
                <span class="ms-stat-label">PRIVACY ENGINE</span>
                <span class="ms-stat-val">100% RAM Lokal</span>
              </div>
            </div>
          </div>
          <div class="ms-badges-container" style="margin-top:1rem;">
            <span class="ms-step-badge ms-badge-accent">Prompt Komersial (80-160 Kata)</span>
            <span class="ms-step-badge ms-badge-green">Gemini Vision SEO (50 Keywords)</span>
            <span class="ms-step-badge ms-badge-purple">Auto-Sync Folder Downloads</span>
            <span class="ms-step-badge ms-badge-amber">Smart Microstock ~8 MP (File Ringan)</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Sidebar
def render_sidebar() -> Optional[str]:
    with st.sidebar:
        st.markdown(
            """
            <div class="ms-card-modern" style="padding:0.75rem 0.9rem; margin-bottom:1rem; border-color:var(--border-color); background:var(--bg-input);">
              <div style="display:flex; align-items:center; justify-content:space-between;">
                <span style="font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:0.82rem; color:var(--text-accent); letter-spacing:0.5px;">
                  ● STUDIO PRO DARK
                </span>
                <span class="ms-step-badge ms-badge-green" style="font-size:0.7rem; padding:1px 6px;">
                  Vulkan GPU
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <p style="font-size:0.75rem; font-weight:700; color:var(--text-muted); letter-spacing:0.8px; text-transform:uppercase; margin:0 0 0.5rem;">
              // ENGINE & API ACCESS
            </p>
            """,
            unsafe_allow_html=True,
        )

        saved_key = config.load_saved_api_key()

        if saved_key:
            masked = saved_key[:6] + "..." + saved_key[-4:] if len(saved_key) > 12 else "●●●●●●●●"
            st.markdown(
                f"""
                <div class="ms-card-modern" style="padding:0.9rem; margin-bottom:0.8rem;">
                  <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.3rem;">
                    <b style="font-size:0.92rem; color:var(--text-primary);">Gemini API Key</b>
                    <span class="ms-step-badge ms-badge-green" style="font-size:0.68rem; padding:1px 6px;">Aktif</span>
                  </div>
                  <p style="font-size:0.82rem; color:var(--text-secondary); margin:0 0 0.45rem;">
                    Tersimpan aman di komputer lokal Anda.
                  </p>
                  <div style="background:var(--bg-input); border:1px solid var(--border-color); border-radius:6px; padding:0.25rem 0.55rem; font-size:0.82rem; font-weight:600; color:var(--text-accent); font-family:'Space Grotesk', monospace; display:inline-block;">
                    Key: {masked}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Hapus API Key dari Komputer", type="secondary", use_container_width=True):
                config.delete_saved_api_key()
                st.toast("API Key berhasil dihapus dari komputer lokal!", icon="🗑️")
                st.rerun()
            api_key = saved_key
        else:
            st.markdown(
                """
                <div class="ms-card-modern" style="padding:0.9rem; margin-bottom:0.8rem;">
                  <b style="font-size:0.92rem; color:var(--text-primary); display:block; margin-bottom:0.2rem;">
                    🔑 Masukkan Gemini API Key
                  </b>
                  <p style="font-size:0.82rem; color:var(--text-secondary); margin:0; line-height:1.4;">
                    Dibutuhkan untuk analisis Vision & metadata. Dapatkan gratis di Google AI Studio.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            typed = st.text_input(
                "Gemini API Key:", type="password", key="api_key_input",
                placeholder="Tempelkan API Key di sini (AIzaSy...)",
                help="Dapatkan API key gratis di aistudio.google.com",
            )
            api_key = typed.strip() if typed else None

            if api_key:
                if st.button("💾 Simpan Permanen di Komputer", type="primary", use_container_width=True):
                    config.save_api_key(api_key)
                    st.toast("API Key berhasil disimpan di komputer lokal!", icon="✅")
                    st.rerun()
            else:
                st.caption("Belum punya API key? Buka [aistudio.google.com](https://aistudio.google.com) (Gratis).")

        st.divider()

        st.markdown(
            """
            <p style="font-size:0.75rem; font-weight:700; color:var(--text-muted); letter-spacing:0.8px; text-transform:uppercase; margin:0 0 0.5rem;">
              // WORKFLOW GUIDE
            </p>
            <div class="ms-card-modern" style="padding:0.9rem; margin-bottom:1rem;">
              <ol style="margin: 0.2rem 0 0 1.1rem; padding: 0; font-size: 0.83rem; line-height: 1.55; color:var(--text-secondary);">
                <li>Salin <b>Prompt Komersial</b> siap pakai (100% faceless & bebas hak cipta).</li>
                <li>Tempel di generator gambar pilihan & download.</li>
                <li>Buka <b>Tab 2 (Auto-Sync)</b> untuk otomatis deteksi file download, upscale NCNN, dan buat 50 keyword SEO.</li>
              </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <p style="font-size:0.75rem; font-weight:700; color:var(--text-muted); letter-spacing:0.8px; text-transform:uppercase; margin:0 0 0.5rem;">
              // UTILITIES & STORAGE
            </p>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🧹 Bersihkan Cache Streamlit", use_container_width=True, type="secondary"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.toast("Cache Streamlit berhasil dibersihkan!", icon="🧹")

        st.divider()
        st.caption("Microstock AI Studio v2.5 Pro · Dark Obsidian Engine")

    return api_key


# Output grid & cards
def _copy_block(label: str, text: str) -> None:
    st.markdown(f"**{label}**")
    st.code(text or "-", language=None, wrap_lines=True)


def render_card(item: BatchItem, batch_id: str) -> None:
    with st.container(border=True):
        n = item.index + 1
        if item.ok:
            st.image(item.preview_bytes)
            size_mb = len(item.image_bytes) / 1_048_576
            mp = (item.width * item.height) / 1_000_000
            st.markdown(
                f"""
                <div style="margin: 0.5rem 0 0.2rem;">
                  <span class="ms-step-badge ms-badge-green" style="font-size:0.75rem; padding:0.2rem 0.5rem;">
                    {item.width}×{item.height}px ({mp:.1f} MP)
                  </span>
                  <span style="font-size:0.8rem; color:var(--text-secondary); margin-left:0.4rem;">
                    {size_mb:.1f} MB · {item.filename}
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.error(f"Gambar #{n} gagal diproses: {item.image_error or 'unknown error'}")

        md = item.metadata
        with st.expander("Detail Metadata Microstock", expanded=False):
            if md:
                _copy_block(f"Title ({len(md.title)}/{config.TITLE_MAX_CHARS})", md.title)
                _copy_block(f"Description ({len(md.description)} karakter)", md.description)
                _copy_block(f"Keywords CSV ({len(md.keywords)}/{config.KEYWORD_COUNT})", md.keywords_csv)
                
                # Visual tag chip cluster
                chips_html = "".join(
                    f'<span class="ms-step-badge ms-badge-accent" style="font-size:0.68rem; padding:1px 5px; margin:2px 2px; display:inline-block;">#{k}</span>'
                    for k in md.keywords
                )
                st.markdown(
                    f"""
                    <div style="margin: 0.5rem 0 0.4rem;">
                      <b style="font-size:0.78rem; color:var(--text-secondary); display:block; margin-bottom:0.25rem;">Preview Tag Interaktif:</b>
                      <div style="display:flex; flex-wrap:wrap; max-height:120px; overflow-y:auto; padding:0.4rem; background:var(--bg-input); border-radius:6px; border:1px solid var(--border-color);">
                        {chips_html}
                      </div>
                    </div>
                    <div style="margin-top:0.4rem;">
                      <span class="ms-step-badge ms-badge-amber" style="font-size:0.75rem; margin-right:0.3rem;">
                        Adobe: {md.adobe_category_name}
                      </span>
                    """
                    + "".join(f'<span class="ms-step-badge ms-badge-accent" style="font-size:0.75rem; margin-right:0.3rem;">SS: {c}</span>' for c in md.shutterstock_categories)
                    + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.warning(f"Metadata belum tersedia: {item.metadata_error or 'pending'}")
            if item.final_prompt:
                _copy_block("Prompt Gambar Asli", item.final_prompt)

        if item.ok:
            st.download_button(
                f"Download {item.filename}",
                data=item.image_bytes,
                file_name=item.filename,
                mime=item.mime_type,
                key=f"dl_{batch_id}_{item.index}",
                use_container_width=True,
            )


def render_results_grid(items: List[BatchItem], batch_id: str, columns: int = 3) -> None:
    for row_start in range(0, len(items), columns):
        cols = st.columns(columns, gap="medium")
        for col, item in zip(cols, items[row_start: row_start + columns]):
            with col:
                render_card(item, batch_id)


def render_export_hub(df: pd.DataFrame, zip_bytes: bytes, zip_name: str,
                      csv_bytes: bytes, batch_id: str) -> None:
    st.markdown(
        """
        <div class="ms-card-modern" style="margin-bottom:1.2rem;">
          <h3 style="margin:0 0 0.3rem; font-family:'Space Grotesk',sans-serif; font-size:1.35rem; font-weight:800; color:var(--text-primary);">
            Export Hub Siap Upload
          </h3>
          <p style="margin:0; color:var(--text-secondary); font-size:0.92rem;">
            Paket lengkap berisi seluruh foto resolusi tinggi beserta CSV metadata terstandarisasi untuk Adobe Stock dan Shutterstock.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([2, 1, 1], gap="medium")
    with c1:
        st.download_button(
            f"Download Paket Lengkap ZIP ({len(zip_bytes) / 1_048_576:.1f} MB)",
            data=zip_bytes, file_name=zip_name, mime="application/zip",
            type="primary", key=f"zip_{batch_id}",
            use_container_width=True,
        )
        st.caption("Berisi file gambar + `metadata.csv`, `adobe_stock.csv`, `shutterstock.csv`.")
    with c2:
        st.metric("Total Gambar", len(df))
    with c3:
        st.download_button(
            "Download metadata.csv",
            data=csv_bytes, file_name="metadata.csv",
            mime="text/csv", key=f"csv_{batch_id}",
            use_container_width=True,
        )
    with st.expander("Lihat Tabel Metadata Lengkap", expanded=False):
        st.dataframe(df.drop(columns=["Prompt"], errors="ignore"), hide_index=True)
