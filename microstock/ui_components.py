"""Reusable Streamlit UI components (sidebar, header, cards, export hub, progress).
Designed with Playful Neo-Pop & Creative Studio aesthetic, strictly conforming to antislop-ui.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from . import config
from .image_generator import BatchItem, BatchSettings

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap');

/* ========================================================================= */
/* 1. UNIVERSAL LIGHT ENFORCEMENT & HIGH-CONTRAST CSS VARIABLES              */
/* ========================================================================= */
:root {
  color-scheme: light !important;
  --primary-color: #FF5436 !important;
  --background-color: #F8F6F0 !important;
  --secondary-background-color: #FFFFFF !important;
  --text-color: #1A191E !important;
}

html, body, .stApp {
  color-scheme: light !important;
  background-color: #F8F6F0 !important;
  color: #1A191E !important;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.block-container {
  padding-top: 1.2rem !important;
  padding-bottom: 3.5rem !important;
  max-width: 1360px !important;
}

/* ========================================================================= */
/* 2. STREAMLIT TOP BAR & HEADER (PREVENT BLACK HEADER & INVISIBLE ICONS)    */
/* ========================================================================= */
header[data-testid="stHeader"],
header[data-testid="stHeader"] > div {
  background-color: #F8F6F0 !important;
  background: #F8F6F0 !important;
  color: #1A191E !important;
}

header[data-testid="stHeader"] * {
  color: #1A191E !important;
  fill: #1A191E !important;
}

header[data-testid="stHeader"] button {
  background-color: transparent !important;
  color: #1A191E !important;
  border: none !important;
  box-shadow: none !important;
}

header[data-testid="stHeader"] button svg {
  fill: #1A191E !important;
  color: #1A191E !important;
  stroke: #1A191E !important;
}

div[data-testid="stDecoration"] {
  display: none !important;
  height: 0 !important;
}

div[data-testid="stToolbar"] {
  color: #1A191E !important;
}

/* ========================================================================= */
/* 3. UNIVERSAL HIGH-CONTRAST TYPOGRAPHY                                     */
/* ========================================================================= */
h1, h2, h3, h4, h5, h6,
[data-testid="stHeadingWithActionElements"] h1,
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
}

p, span, li, label, b, strong {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] b {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
}

/* Form labels */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] span {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 700 !important;
  font-size: 0.95rem !important;
}

/* Tooltip / Help Icons */
[data-testid="stTooltipIcon"] svg,
[data-testid="stTooltipIcon"] path {
  fill: #1A191E !important;
  color: #1A191E !important;
}

/* Captions (Muted slate with 8.2:1 contrast ratio) */
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] span,
.stCaption {
  color: #4A4853 !important;
  -webkit-text-fill-color: #4A4853 !important;
  font-weight: 600 !important;
}

/* ========================================================================= */
/* 4. PLAYFUL NEO-POP STUDIO HERO BANNER                                     */
/* ========================================================================= */
.ms-hero-pop {
  background-color: #FFD166 !important;
  background: #FFD166 !important;
  border: 2.5px solid #1A191E !important;
  border-radius: 16px !important;
  padding: 1.6rem 2rem !important;
  margin-bottom: 1.6rem !important;
  box-shadow: 4px 4px 0px #1A191E !important;
  position: relative !important;
  overflow: hidden !important;
}

.ms-hero-pop::after {
  content: "";
  position: absolute;
  top: -24px;
  right: -24px;
  width: 110px;
  height: 110px;
  background: #FF5436;
  border-radius: 50%;
  border: 2px solid #1A191E;
  opacity: 0.2;
  pointer-events: none;
}

.ms-hero-pop * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
}

.ms-hero-pop h1 {
  margin: 0 !important;
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-size: 2.2rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.6px !important;
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  line-height: 1.2 !important;
}

.ms-hero-tagline {
  margin: 0.45rem 0 0 !important;
  font-size: 1.02rem !important;
  font-weight: 600 !important;
  color: #2D2C34 !important;
  -webkit-text-fill-color: #2D2C34 !important;
  line-height: 1.5 !important;
}

.ms-badges-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.9rem;
}

.ms-step-badge-pop {
  display: inline-flex;
  align-items: center;
  padding: 0.3rem 0.8rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 700;
  border: 1.5px solid #1A191E;
  box-shadow: 2px 2px 0px #1A191E;
}

.ms-badge-coral, .ms-badge-coral * {
  background-color: #FFE3DC !important;
  color: #D9381E !important;
  -webkit-text-fill-color: #D9381E !important;
}

.ms-badge-mint, .ms-badge-mint * {
  background-color: #D3F9D8 !important;
  color: #1B7A32 !important;
  -webkit-text-fill-color: #1B7A32 !important;
}

.ms-badge-blue, .ms-badge-blue * {
  background-color: #E7F0FD !important;
  color: #1754CF !important;
  -webkit-text-fill-color: #1754CF !important;
}

.ms-badge-yellow, .ms-badge-yellow * {
  background-color: #FFF9DB !important;
  color: #8C6200 !important;
  -webkit-text-fill-color: #8C6200 !important;
}

/* ========================================================================= */
/* 5. TABS STYLING — PLAYFUL NEO-POP CARD TABS (ALWAYS VISIBLE & CRISP)      */
/* ========================================================================= */
div[data-testid="stTabs"] {
  margin-top: 0.6rem;
  margin-bottom: 1.5rem;
}

div[data-testid="stTabs"] [role="tablist"],
div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
  gap: 0.6rem !important;
  border-bottom: 2.5px solid #1A191E !important;
  padding-bottom: 0px !important;
  background-color: transparent !important;
}

div[data-testid="stTabs"] button[role="tab"],
div[data-testid="stTabs"] button[data-baseweb="tab"],
div[data-testid="stTabs"] button {
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-size: 1.05rem !important;
  font-weight: 700 !important;
  border-radius: 12px 12px 0 0 !important;
  padding: 0.65rem 1.6rem !important;
  margin-bottom: -2.5px !important;
  transition: all 0.15s ease !important;
  opacity: 1 !important;
  visibility: visible !important;
}

div[data-testid="stTabs"] button[role="tab"] *,
div[data-testid="stTabs"] button[data-baseweb="tab"] *,
div[data-testid="stTabs"] button * {
  opacity: 1 !important;
  visibility: visible !important;
}

/* INACTIVE TAB */
div[data-testid="stTabs"] button[role="tab"][aria-selected="false"],
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"],
div[data-testid="stTabs"] button[aria-selected="false"] {
  background-color: #EDE8DE !important;
  border: 2px solid #1A191E !important;
  border-bottom: 2.5px solid #1A191E !important;
  box-shadow: 2px 2px 0px #1A191E !important;
  color: #1A191E !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="false"] *,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"] *,
div[data-testid="stTabs"] button[aria-selected="false"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 700 !important;
}

/* INACTIVE TAB HOVER */
div[data-testid="stTabs"] button[role="tab"][aria-selected="false"]:hover,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"]:hover,
div[data-testid="stTabs"] button[aria-selected="false"]:hover {
  background-color: #FFE3DC !important;
  border-color: #1A191E !important;
  box-shadow: 3px 3px 0px #1A191E !important;
  color: #D9381E !important;
  transform: translate(-1px, -1px) !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="false"]:hover *,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="false"]:hover *,
div[data-testid="stTabs"] button[aria-selected="false"]:hover * {
  color: #D9381E !important;
  -webkit-text-fill-color: #D9381E !important;
  font-weight: 800 !important;
}

/* ACTIVE TAB */
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[aria-selected="true"] {
  background-color: #FFFFFF !important;
  border: 2.5px solid #1A191E !important;
  border-bottom: 2.5px solid #FFFFFF !important;
  box-shadow: 4px -2px 0px #1A191E !important;
  color: #1A191E !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] *,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] *,
div[data-testid="stTabs"] button[aria-selected="true"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 800 !important;
}

div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
  display: none !important;
}

/* ========================================================================= */
/* 6. SIDEBAR & API KEY INPUT MENU                                           */
/* ========================================================================= */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border-right: 2.5px solid #1A191E !important;
  color: #1A191E !important;
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 700 !important;
}

/* Sidebar & General Input Containers */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"],
div[data-testid="stTextInput"] div[data-baseweb="base-input"],
div[data-testid="stTextArea"] div[data-baseweb="base-input"],
section[data-testid="stSidebar"] div[data-baseweb="input"],
section[data-testid="stSidebar"] div[data-baseweb="base-input"] {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 2px 2px 0px rgba(26,25,30,0.12) !important;
}

input, textarea,
input[type="text"],
input[type="password"] {
  color: #1A191E !important;
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  -webkit-text-fill-color: #1A191E !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
}

input::placeholder, textarea::placeholder {
  color: #716E79 !important;
  -webkit-text-fill-color: #716E79 !important;
  opacity: 1 !important;
}

/* Password Eye Icon & Action Buttons inside Inputs */
div[data-baseweb="input"] button,
div[data-baseweb="input"] button:hover {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

div[data-baseweb="input"] button svg,
div[data-baseweb="input"] svg {
  fill: #1A191E !important;
  color: #1A191E !important;
  stroke: #1A191E !important;
}

.ms-tip-card {
  background: #FFF9DB;
  border: 2px solid #1A191E;
  border-radius: 12px;
  padding: 1rem;
  box-shadow: 3px 3px 0px #1A191E;
  margin-top: 1rem;
}

.ms-tip-card * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
}

/* ========================================================================= */
/* 7. TAB 2: FILE UPLOADER (DROPZONE, ICONS, BUTTONS, INSTRUCTIONS)          */
/* ========================================================================= */
div[data-testid="stFileUploader"] {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border: 2.5px dashed #1A191E !important;
  border-radius: 14px !important;
  padding: 1.2rem !important;
  box-shadow: 4px 4px 0px rgba(26,25,30,0.08) !important;
}

div[data-testid="stFileUploader"] section,
section[data-testid="stFileUploadDropzone"] {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border: none !important;
  text-align: center !important;
}

/* All text in file uploader */
div[data-testid="stFileUploader"] *,
section[data-testid="stFileUploadDropzone"] *,
[data-testid="stFileUploadDropzoneInstructions"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  opacity: 1 !important;
  visibility: visible !important;
}

/* Small instructions text ("Limit 200MB per file...") */
div[data-testid="stFileUploader"] small,
section[data-testid="stFileUploadDropzone"] small,
[data-testid="stFileUploadDropzoneInstructions"] small {
  color: #4A4853 !important;
  -webkit-text-fill-color: #4A4853 !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  margin-top: 0.3rem !important;
  display: block !important;
}

/* Upload Cloud Icon: High-contrast Electric Coral #FF5436 */
div[data-testid="stFileUploader"] svg,
section[data-testid="stFileUploadDropzone"] svg,
[data-testid="stFileUploadDropzoneInstructions"] svg {
  fill: #FF5436 !important;
  color: #FF5436 !important;
  stroke: #FF5436 !important;
  width: 44px !important;
  height: 44px !important;
  opacity: 1 !important;
  visibility: visible !important;
  display: inline-block !important;
}

/* "Browse files" button inside dropzone */
section[data-testid="stFileUploadDropzone"] button {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  color: #1A191E !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 2.5px 2.5px 0px #1A191E !important;
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
  padding: 0.5rem 1.3rem !important;
  cursor: pointer !important;
  transition: all 0.12s ease !important;
  margin: 0.6rem 0 !important;
}

section[data-testid="stFileUploadDropzone"] button:hover {
  background-color: #FFE3DC !important;
  color: #D9381E !important;
  transform: translate(-1px, -1px) !important;
  box-shadow: 3.5px 3.5px 0px #1A191E !important;
}

section[data-testid="stFileUploadDropzone"] button * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 700 !important;
}

/* Uploaded file preview list items */
div[data-testid="stFileUploaderFileData"] {
  background-color: #F8F6F0 !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  padding: 0.6rem 0.9rem !important;
  margin-top: 0.6rem !important;
  box-shadow: 2px 2px 0px #1A191E !important;
}

div[data-testid="stFileUploaderFileData"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 600 !important;
}

div[data-testid="stFileUploaderFileData"] button {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}

div[data-testid="stFileUploaderFileData"] button svg {
  fill: #D9381E !important;
  color: #D9381E !important;
  width: 20px !important;
  height: 20px !important;
}

/* ========================================================================= */
/* 8. CARDS & CONTAINERS                                                     */
/* ========================================================================= */
.ms-card-pop {
  background: #FFFFFF;
  border: 2px solid #1A191E;
  border-radius: 14px;
  padding: 1.3rem;
  box-shadow: 4px 4px 0px #1A191E;
  margin-bottom: 1.2rem;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.ms-card-pop:hover {
  transform: translate(-1px, -1px);
  box-shadow: 5px 5px 0px #1A191E;
}

/* ========================================================================= */
/* 9. TACTILE NEO-POP BUTTONS                                                */
/* ========================================================================= */
div.stButton > button {
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  border-radius: 10px !important;
  border: 2px solid #1A191E !important;
  box-shadow: 3px 3px 0px #1A191E !important;
  transition: all 0.12s ease !important;
  font-size: 0.95rem !important;
}

div.stButton > button:hover {
  transform: translate(-1px, -1px) !important;
  box-shadow: 4px 4px 0px #1A191E !important;
}

div.stButton > button:active {
  transform: translate(2px, 2px) !important;
  box-shadow: 1px 1px 0px #1A191E !important;
}

/* Primary Button (Electric Coral) */
div.stButton > button[kind="primary"] {
  background-color: #FF5436 !important;
  border: 2px solid #1A191E !important;
}
div.stButton > button[kind="primary"]:hover {
  background-color: #E84326 !important;
}
div.stButton > button[kind="primary"] p,
div.stButton > button[kind="primary"] span {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700 !important;
}

/* Secondary Button (Crisp White / Tactile) */
div.stButton > button[kind="secondary"] {
  background-color: #FFFFFF !important;
  border: 2px solid #1A191E !important;
}
div.stButton > button[kind="secondary"] p,
div.stButton > button[kind="secondary"] span {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 700 !important;
}

/* Link Button */
div[data-testid="stLinkButton"] > a {
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  border-radius: 10px !important;
  border: 2px solid #1A191E !important;
  box-shadow: 3px 3px 0px #1A191E !important;
  transition: all 0.12s ease !important;
  background-color: #2962FF !important;
  text-decoration: none !important;
}
div[data-testid="stLinkButton"] > a:hover {
  transform: translate(-1px, -1px) !important;
  box-shadow: 4px 4px 0px #1A191E !important;
  background-color: #1E51DB !important;
}
div[data-testid="stLinkButton"] > a p,
div[data-testid="stLinkButton"] > a span {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700 !important;
}

/* Download Button */
div[data-testid="stDownloadButton"] > button {
  font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  border-radius: 10px !important;
  border: 2px solid #1A191E !important;
  box-shadow: 3px 3px 0px #1A191E !important;
  transition: all 0.12s ease !important;
}
div[data-testid="stDownloadButton"] > button:hover {
  transform: translate(-1px, -1px) !important;
  box-shadow: 4px 4px 0px #1A191E !important;
}
div[data-testid="stDownloadButton"] > button p,
div[data-testid="stDownloadButton"] > button span {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 700 !important;
}
div[data-testid="stDownloadButton"] > button[kind="primary"] p,
div[data-testid="stDownloadButton"] > button[kind="primary"] span {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700 !important;
}

/* ========================================================================= */
/* 10. SELECTBOXES & DROPDOWNS                                               */
/* ========================================================================= */
div[data-baseweb="select"] > div {
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 2px 2px 0px rgba(26,25,30,0.12) !important;
  background-color: #FFFFFF !important;
}

div[data-baseweb="select"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 600 !important;
}

div[data-baseweb="select"] svg {
  fill: #1A191E !important;
  color: #1A191E !important;
}

div[data-baseweb="popover"],
ul[role="listbox"] {
  background-color: #FFFFFF !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 3px 3px 0px #1A191E !important;
}

li[role="option"] {
  background-color: #FFFFFF !important;
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 600 !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"] {
  background-color: #FFE3DC !important;
  color: #D9381E !important;
  -webkit-text-fill-color: #D9381E !important;
  font-weight: 700 !important;
}

/* ========================================================================= */
/* 11. METADATA PILLS & BADGES                                               */
/* ========================================================================= */
.ms-pill-pop {
  display: inline-block;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 700;
  border: 1.5px solid #1A191E;
  box-shadow: 1.5px 1.5px 0px #1A191E;
  margin: 0.2rem 0.3rem 0.2rem 0;
}

.ms-pill-adobe, .ms-pill-adobe * {
  background-color: #FFF3BF !important;
  color: #8C5700 !important;
  -webkit-text-fill-color: #8C5700 !important;
}

.ms-pill-ss, .ms-pill-ss * {
  background-color: #E7F5FF !important;
  color: #1864AB !important;
  -webkit-text-fill-color: #1864AB !important;
}

.ms-pill-res, .ms-pill-res * {
  background-color: #D3F9D8 !important;
  color: #2B8A3E !important;
  -webkit-text-fill-color: #2B8A3E !important;
}

/* ========================================================================= */
/* 12. CODE BLOCK, EXPANDERS, ALERTS & METRICS                               */
/* ========================================================================= */
div[data-testid="stCode"] {
  position: relative !important;
  border: 2px solid #1A191E !important;
  border-radius: 12px !important;
  box-shadow: 3px 3px 0px #1A191E !important;
  background-color: #FFFFFF !important;
}

div[data-testid="stCode"] pre,
div[data-testid="stCode"] code,
div[data-testid="stCode"] span {
  white-space: pre-wrap !important;
  word-break: break-word !important;
  font-size: 0.94rem !important;
  line-height: 1.55 !important;
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  background-color: #FFFFFF !important;
}

/* Selection highlight */
::selection {
  background-color: #FFD166 !important;
  color: #1A191E !important;
}
::-moz-selection {
  background-color: #FFD166 !important;
  color: #1A191E !important;
}

/* Copy button on code blocks — always visible, tactile, high-contrast Neo-Pop */
div[data-testid="stCode"] button,
div[data-testid="stCode"] [data-testid="stCodeCopyButton"],
div[data-testid="stCodeCopyButton"],
div[data-testid="stCodeCopyButton"] button,
button[title*="copy" i],
button[aria-label*="copy" i] {
  opacity: 1 !important;
  visibility: visible !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  position: absolute !important;
  top: 8px !important;
  right: 8px !important;
  width: 34px !important;
  height: 34px !important;
  min-width: 34px !important;
  min-height: 34px !important;
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border: 1.5px solid #1A191E !important;
  border-radius: 8px !important;
  box-shadow: 2px 2px 0px #1A191E !important;
  padding: 4px !important;
  cursor: pointer !important;
  z-index: 10 !important;
  transition: all 0.12s ease !important;
}

div[data-testid="stCode"]:hover button,
div[data-testid="stCode"] button:hover,
div[data-testid="stCodeCopyButton"]:hover,
div[data-testid="stCodeCopyButton"] button:hover,
button[title*="copy" i]:hover,
button[aria-label*="copy" i]:hover {
  background-color: #FFE3DC !important;
  background: #FFE3DC !important;
  transform: translate(-1px, -1px) !important;
  box-shadow: 3px 3px 0px #1A191E !important;
}

div[data-testid="stCode"] button svg,
div[data-testid="stCodeCopyButton"] svg,
div[data-testid="stCodeCopyButton"] button svg,
button[title*="copy" i] svg,
button[aria-label*="copy" i] svg {
  display: block !important;
  fill: #1A191E !important;
  color: #1A191E !important;
  stroke: #1A191E !important;
  width: 18px !important;
  height: 18px !important;
  opacity: 1 !important;
  visibility: visible !important;
}

div[data-testid="stCode"] button:hover svg,
div[data-testid="stCodeCopyButton"]:hover svg,
div[data-testid="stCodeCopyButton"] button:hover svg,
button[title*="copy" i]:hover svg,
button[aria-label*="copy" i]:hover svg {
  fill: #D9381E !important;
  color: #D9381E !important;
  stroke: #D9381E !important;
}

/* Expander */
div[data-testid="stExpander"] {
  border: 2px solid #1A191E !important;
  border-radius: 12px !important;
  background-color: #FFFFFF !important;
  box-shadow: 2px 2px 0px #1A191E !important;
  margin-top: 0.6rem !important;
}

div[data-testid="stExpander"] details summary {
  background-color: #FFFFFF !important;
  border-radius: 10px !important;
  padding: 0.5rem 0.8rem !important;
}

div[data-testid="stExpander"] details summary:hover {
  background-color: #F8F6F0 !important;
}

div[data-testid="stExpander"] details summary span,
div[data-testid="stExpander"] details summary p {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 700 !important;
}

div[data-testid="stExpander"] details summary svg {
  fill: #1A191E !important;
  color: #1A191E !important;
}

/* Alerts (info, warning, error, success) — Pastel Neo-Pop Cards, NEVER BLACK */
div[data-testid="stAlert"] {
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 2.5px 2.5px 0px #1A191E !important;
  font-weight: 600 !important;
}

div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] span {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
}

div[data-testid="stAlert"] svg {
  fill: #1A191E !important;
  color: #1A191E !important;
}

div[data-testid="stNotificationContentSuccess"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentSuccess"]) {
  background-color: #D3F9D8 !important;
}

div[data-testid="stNotificationContentInfo"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentInfo"]) {
  background-color: #E7F5FF !important;
}

div[data-testid="stNotificationContentWarning"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentWarning"]) {
  background-color: #FFF9DB !important;
}

div[data-testid="stNotificationContentError"],
div[data-testid="stAlert"]:has([data-testid="stNotificationContentError"]) {
  background-color: #FFE3DC !important;
}

/* Metric Cards */
div[data-testid="stMetric"] {
  background-color: #FFFFFF !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  padding: 0.75rem 1rem !important;
  box-shadow: 2.5px 2.5px 0px #1A191E !important;
}

div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] span {
  color: #4A4853 !important;
  -webkit-text-fill-color: #4A4853 !important;
  font-weight: 700 !important;
}

div[data-testid="stMetricValue"] {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  font-weight: 800 !important;
}

/* Progress Bar & Spinner */
div[data-testid="stProgress"] div[role="progressbar"] {
  background-color: #EDE8DE !important;
  border: 1.5px solid #1A191E !important;
  border-radius: 8px !important;
  overflow: hidden !important;
  height: 14px !important;
}

div[data-testid="stProgress"] div[role="progressbar"] > div {
  background-color: #FF5436 !important;
  background: #FF5436 !important;
  border-radius: 6px !important;
}

div[data-testid="stProgress"] p,
div[data-testid="stProgress"] span {
  color: #1A191E !important;
  font-weight: 700 !important;
}

div[data-testid="stSpinner"] p,
div[data-testid="stSpinner"] span {
  color: #1A191E !important;
  font-weight: 700 !important;
}

/* Dataframe & Tables */
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
  background-color: #FFFFFF !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 3px 3px 0px #1A191E !important;
  overflow: hidden !important;
}

/* ========================================================================= */
/* 13. TOOLTIPS & HELP POPOVERS (PREVENT BLACK / INVISIBLE TEXT)             */
/* ========================================================================= */
div[data-baseweb="tooltip"],
div[role="tooltip"],
div[data-baseweb="popover"]:not([role="listbox"]),
[data-testid="stTooltipContent"] {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 3px 3px 0px #1A191E !important;
  padding: 0.6rem 0.9rem !important;
}

div[data-baseweb="tooltip"] *,
div[role="tooltip"] *,
div[data-baseweb="popover"]:not([role="listbox"]) *,
[data-testid="stTooltipContent"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  background-color: transparent !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  line-height: 1.4 !important;
}

/* ========================================================================= */
/* 14. INLINE CODE TAGS & BACKTICKS (WARM YELLOW BADGES, NEVER BLACK)        */
/* ========================================================================= */
code,
code:not(pre code),
[data-testid="stMarkdownContainer"] code,
[data-testid="stExpander"] code,
p code,
li code,
span code {
  background-color: #FFF3BF !important;
  background: #FFF3BF !important;
  color: #8C5700 !important;
  -webkit-text-fill-color: #8C5700 !important;
  border: 1.5px solid #1A191E !important;
  border-radius: 6px !important;
  padding: 0.15rem 0.45rem !important;
  font-family: 'Space Grotesk', monospace !important;
  font-weight: 700 !important;
  font-size: 0.88em !important;
  box-shadow: 1.5px 1.5px 0px #1A191E !important;
}

/* ========================================================================= */
/* 15. TOAST NOTIFICATIONS (CRISP WHITE NEO-POP, NEVER BLACK)                */
/* ========================================================================= */
div[data-testid="stToast"],
[data-testid="stToastContainer"],
[data-testid="stToastContainer"] > div {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border: 2.5px solid #1A191E !important;
  border-radius: 12px !important;
  box-shadow: 4px 4px 0px #1A191E !important;
  color: #1A191E !important;
  width: fit-content !important;
  max-width: 350px !important;
}

div[data-testid="stToast"] *,
[data-testid="stToastContainer"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  background-color: transparent !important;
  font-weight: 700 !important;
}

div[data-testid="stToast"] svg {
  fill: #1A191E !important;
  color: #1A191E !important;
}

/* ========================================================================= */
/* 16. TOP TOOLBAR & MAIN MENU NEXT TO DEPLOY (NEVER BLACK)                  */
/* ========================================================================= */
div[data-testid="stToolbar"],
div[data-testid="stMainMenu"],
div[data-testid="stStatusWidget"],
[data-testid="stHeader"] [data-testid="stToolbarActions"],
[data-testid="stHeader"] [data-testid="stAppDeployButton"] {
  background-color: #F8F6F0 !important;
  background: #F8F6F0 !important;
  color: #1A191E !important;
}

div[data-testid="stToolbar"] *,
div[data-testid="stMainMenu"] *,
div[data-testid="stStatusWidget"] *,
[data-testid="stHeader"] [data-testid="stToolbarActions"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
}

div[data-testid="stToolbar"] button,
div[data-testid="stMainMenu"] button,
div[data-testid="stStatusWidget"] button {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  border: 1.5px solid #1A191E !important;
  border-radius: 8px !important;
  box-shadow: 2px 2px 0px #1A191E !important;
  color: #1A191E !important;
}

div[data-testid="stToolbar"] button svg,
div[data-testid="stMainMenu"] button svg,
div[data-testid="stStatusWidget"] svg {
  fill: #1A191E !important;
  color: #1A191E !important;
  stroke: #1A191E !important;
}

/* Hamburger dropdown menu popup when clicked */
ul[role="menu"],
div[data-baseweb="menu"],
li[role="menuitem"] {
  background-color: #FFFFFF !important;
  background: #FFFFFF !important;
  color: #1A191E !important;
  border: 2px solid #1A191E !important;
  border-radius: 10px !important;
  box-shadow: 3px 3px 0px #1A191E !important;
}

ul[role="menu"] *,
div[data-baseweb="menu"] *,
li[role="menuitem"] * {
  color: #1A191E !important;
  -webkit-text-fill-color: #1A191E !important;
  background-color: transparent !important;
  font-weight: 600 !important;
}

li[role="menuitem"]:hover {
  background-color: #FFE3DC !important;
}

li[role="menuitem"]:hover * {
  color: #D9381E !important;
  -webkit-text-fill-color: #D9381E !important;
}

/* ========================================================================= */
/* 17. CARET & AUTOFILL COLOR (ALWAYS CRISP BLACK CURSOR)                    */
/* ========================================================================= */
input, textarea, [contenteditable="true"] {
  caret-color: #1A191E !important;
}

input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
textarea:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 30px #FFFFFF inset !important;
  -webkit-text-fill-color: #1A191E !important;
  caret-color: #1A191E !important;
}

hr, [data-testid="stDivider"], div[data-testid="stDivider"] hr {
  border-color: #1A191E !important;
  opacity: 0.25 !important;
}
</style>
"""


def inject_css() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        """
        <div class="ms-hero-pop">
          <h1>Microstock AI Studio</h1>
          <p class="ms-hero-tagline">
            Studio prompt komersial & metadata SEO otomatis bertenaga <b>Google Gemini</b>.
            Dirancang khusus untuk kontributor <b>Adobe Stock, Shutterstock, & Freepik</b>.
          </p>
          <div class="ms-badges-container">
            <span class="ms-step-badge-pop ms-badge-coral">Magic Prompt Pro (80-160 Kata)</span>
            <span class="ms-step-badge-pop ms-badge-mint">Gemini Vision Visual SEO</span>
            <span class="ms-step-badge-pop ms-badge-blue">Resolusi Asli (300 DPI High-Quality)</span>
            <span class="ms-step-badge-pop ms-badge-yellow">Export ZIP & CSV Siap Upload</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def render_sidebar() -> Optional[str]:
    with st.sidebar:
        st.header("Studio Setup")

        saved_key = config.load_saved_api_key()

        if saved_key:
            masked = saved_key[:6] + "..." + saved_key[-4:] if len(saved_key) > 12 else "●●●●●●●●"
            st.markdown(
                f"""
                <div style="background:#D3F9D8; border:2px solid #1A191E; border-radius:10px; padding:0.85rem; margin-bottom:0.8rem; box-shadow:2px 2px 0px #1A191E;">
                  <b style="font-size:0.95rem; color:#1B7A32; display:block; margin-bottom:0.25rem;">💾 API Key Aktif & Tersimpan</b>
                  <p style="font-size:0.82rem; color:#1A191E; margin:0 0 0.45rem; font-weight:600;">
                    Tersimpan aman di komputer lokal Anda.
                  </p>
                  <div style="background:#FFFFFF; border:1.5px solid #1A191E; border-radius:6px; padding:0.25rem 0.55rem; font-size:0.84rem; font-weight:700; color:#1A191E; font-family:'Space Grotesk', monospace; display:inline-block;">
                    Status: Aktif ({masked})
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
                <div style="background:#FFF9DB; border:2px solid #1A191E; border-radius:10px; padding:0.8rem; margin-bottom:0.8rem; box-shadow:2px 2px 0px #1A191E;">
                  <b style="font-size:0.95rem; color:#1A191E; display:block; margin-bottom:0.2rem;">🔑 Masukkan Gemini API Key</b>
                  <p style="font-size:0.82rem; color:#4A4853; margin:0; font-weight:600; line-height:1.4;">
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
            <div class="ms-tip-card">
              <b style="font-size:0.95rem; color:#1A191E;">Tips Sukses Microstock:</b>
              <ol style="margin: 0.5rem 0 0 1.2rem; padding: 0; font-size: 0.88rem; line-height: 1.5; color:#1A191E;">
                <li><b>Gunakan Magic Prompt</b>: Rinci pencahayaan, lensa, dan ruang kosong untuk copyiklan.</li>
                <li><b>Generate di Gemini Web</b>: Buka <code>gemini.google.com</code> dan unduh gambarnya.</li>
                <li><b>Inspeksi di Tab 2</b>: Gemini Vision akan mendeteksi isi gambar nyata dan menyusun 50 keywords yang anti-reject!</li>
              </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        st.caption("Microstock Studio v2.0 · Playful Neo-Pop Edition")

    return api_key


# --------------------------------------------------------------------------- #
# Progress tracker
# --------------------------------------------------------------------------- #
class BatchProgress:
    """Live progress bar + log for N images and N metadata sets."""

    def __init__(self, n_items: int, image_jobs: Optional[int] = None,
                 meta_jobs: Optional[int] = None):
        self.n_img = n_items if image_jobs is None else image_jobs
        self.n_meta = n_items if meta_jobs is None else meta_jobs
        self.total = max(1, self.n_img + self.n_meta)
        self.img_done = self.meta_done = self.failures = 0
        self.t0 = time.perf_counter()
        self.status = st.status(f"Memproses {n_items} gambar...", expanded=True)
        with self.status:
            self.bar = st.progress(0.0, text="Menyiapkan...")
            self.log_area = st.container()

    def _refresh(self) -> None:
        done = self.img_done + self.meta_done
        elapsed = time.perf_counter() - self.t0
        self.bar.progress(
            min(done / self.total, 1.0),
            text=(f"Gambar {self.img_done}/{self.n_img} · "
                  f"Metadata {self.meta_done}/{self.n_meta} · {elapsed:.0f}s"),
        )

    def on_progress(self, event: str, item: BatchItem) -> None:
        n = item.index + 1
        with self.log_area:
            if event == "image":
                self.img_done += 1
                if item.ok:
                    st.write(f"Gambar #{n} siap: {item.width}×{item.height}px")
                else:
                    self.failures += 1
                    st.write(f"Gambar #{n} gagal: {item.image_error}")
            else:
                self.meta_done += 1
                if item.metadata:
                    st.write(f"Metadata #{n} siap: {len(item.metadata.keywords)} keywords")
                else:
                    self.failures += 1
                    st.write(f"Metadata #{n} gagal: {item.metadata_error}")
        self._refresh()

    def on_log(self, message: str) -> None:
        with self.log_area:
            st.caption(f"{message}")

    def finish(self) -> None:
        elapsed = time.perf_counter() - self.t0
        state = "complete" if self.failures == 0 else "error"
        label = (f"Selesai dalam {elapsed:.0f}s" if self.failures == 0
                 else f"Selesai dalam {elapsed:.0f}s dengan {self.failures} kendala")
        self.bar.progress(1.0, text=label)
        self.status.update(label=label, state=state, expanded=False)


# --------------------------------------------------------------------------- #
# Output grid
# --------------------------------------------------------------------------- #
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
                f"<span class='ms-pill-pop ms-pill-res'>{item.width}×{item.height}px ({mp:.1f} MP) · 300 DPI</span>"
                f"<span style='font-size:0.82rem; color:#4A4853; font-weight:700;'>{size_mb:.1f} MB · {item.filename}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.error(f"Gambar #{n} gagal diproses: {item.image_error or 'unknown error'}")

        md = item.metadata
        with st.expander("Detail Metadata Microstock", expanded=False):
            if md:
                _copy_block(f"Title ({len(md.title)}/{config.TITLE_MAX_CHARS})", md.title)
                _copy_block(f"Description ({len(md.description)} karakter)", md.description)
                _copy_block(f"Keywords ({len(md.keywords)}/{config.KEYWORD_COUNT})", md.keywords_csv)
                st.markdown(
                    f"<span class='ms-pill-pop ms-pill-adobe'>Adobe: {md.adobe_category} · {md.adobe_category_name}</span>"
                    + "".join(f"<span class='ms-pill-pop ms-pill-ss'>SS: {c}</span>" for c in md.shutterstock_categories),
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
        <div style="background:#FFFFFF; border:2.5px solid #1A191E; border-radius:14px; padding:1.4rem; box-shadow:4px 4px 0px #1A191E; margin-bottom:1.2rem;">
          <h3 style="margin:0 0 0.4rem; font-family:'Space Grotesk',sans-serif; font-size:1.4rem; font-weight:800; color:#1A191E;">
            Export Hub Siap Upload
          </h3>
          <p style="margin:0 0 1rem; color:#4A4853; font-size:0.92rem; font-weight:600;">
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


def download_image_from_url(url: str) -> Tuple[bytes, str]:
    """Download image bytes from direct URL with full browser headers."""
    import urllib.request
    clean_url = url.strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://gemini.google.com/",
        "Sec-Ch-Ua": '"Google Chrome";v="126", "Chromium";v="126", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    }
    req = urllib.request.Request(clean_url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        mime = resp.headers.get_content_type() or "image/jpeg"
        return data, mime
