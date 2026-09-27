"""Static civic theme; no user content is interpolated into this stylesheet."""
import streamlit as st
from frontend.theme import COLORS


def apply_styles():
    css = """<style>
    :root { __TOKENS__ --primary-color: var(--sw-action); --text-color: var(--sw-text);
      --background-color: var(--sw-background); --secondary-background-color: #f5f5f4; }
    .stApp { background: var(--sw-background); color: var(--sw-text); }
    .block-container { max-width: 1200px; padding-top: 4rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: var(--sw-text); letter-spacing: -.025em; }
    p, label, li { line-height: 1.6; }
    .stApp [data-testid="stText"], .stApp [data-testid="stWidgetLabel"] p,
    .stApp .stButton p, .stApp .stFormSubmitButton p { font-size: 1rem; }
    [data-testid="stText"] { white-space: pre-wrap; overflow-wrap: anywhere; }
    [data-testid="stColumn"] { min-width: 0; }
    [role="tablist"] { overflow-x: auto; }
    button[role="tab"] { min-height: 44px; }
    .st-key-public_header { padding: .2rem 0; }
    .st-key-login_panel { max-width: 580px; margin-inline: auto; }
    .st-key-hero_actions { max-width: 620px; }
    [data-testid="stHeader"] { background: var(--sw-background); }
    .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {
      color: var(--sw-metadata); font-size: .9rem; }
    .stApp hr { margin-block: .8rem; }
    [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] > div {
      border-color: var(--sw-border); border-radius: 16px; }
    [data-testid="stForm"] { background: #fff; padding: 1.5rem; }
    .stButton button, .stFormSubmitButton button {
      min-height: 46px; min-width: 44px; border-radius: 12px; font-weight: 600; }
    button[kind="primary"], button[kind="primaryFormSubmit"] {
      background: var(--sw-action); color: #fff; border-color: var(--sw-action); }
    button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
      background: var(--sw-hover); border-color: var(--sw-hover); }
    button[kind="secondary"] { background: #fff; color: var(--sw-text); border-color: #a8a29e; }
    button:focus-visible, input:focus-visible, textarea:focus-visible {
      outline: 3px solid #1d4ed8 !important; outline-offset: 3px; }
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
      background: #fff; color: var(--sw-text); border-color: #a8a29e; }
    input, textarea { color: var(--sw-text) !important; caret-color: var(--sw-action); }
    [data-testid="stTextInputRootElement"] { background: #fff; min-height: 46px; }
    [data-testid="stTextInputRootElement"] button,
    [data-testid="stSelectbox"] button,
    [data-testid="stTooltipIcon"] button { min-width: 44px; min-height: 44px; }
    [data-testid="stTooltipIcon"] button {
      display: inline-flex; align-items: center; justify-content: center; }
    [data-testid="stMetric"] { background: #fff; border: 1px solid var(--sw-border);
      border-radius: 14px; padding: 1.1rem; }
    [data-testid="stMetricValue"] { color: var(--sw-text); }
    .sw-brand { font-size: 1.45rem; font-weight: 750; color: var(--sw-text); }
    .sw-brand span { display: inline-grid; place-items: center; background: var(--sw-action);
      color: white; width: 36px; height: 36px; border-radius: 10px; margin-right: 9px; }
    .sw-eyebrow { color: var(--sw-action); font-size: .82rem; font-weight: 750;
      letter-spacing: .12em; text-transform: uppercase; margin-bottom: .7rem; }
    .sw-hero { background: var(--sw-surface); border: 1px solid var(--sw-border); border-top: 4px solid var(--sw-primary); border-radius: 16px;
      padding: clamp(1.3rem, 4vw, 2.5rem); margin: .5rem 0 1rem; }
    .sw-hero h1 { font-size: clamp(2rem, 4vw, 3.25rem); line-height: 1.08;
      margin: 0 0 1.2rem; max-width: 760px; }
    .sw-hero p { font-size: 1.15rem; max-width: 650px; color: var(--sw-metadata); }
    .sw-trust { border-left: 4px solid var(--sw-action); background: #f5f5f4;
      padding: 1rem 1.2rem; border-radius: 0 12px 12px 0; margin: .6rem 0 1.2rem; }
    .sw-steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;
      margin: 1rem 0 2rem; }
    .sw-step, .sw-empty { background: #fff; border: 1px solid var(--sw-border);
      border-radius: 16px; padding: 1.3rem; box-shadow: 0 3px 12px #1c191708; }
    .sw-step-number { display: inline-grid; place-items: center; width: 34px; height: 34px;
      background: #ecfdf5; border-radius: 50%; color: var(--sw-action); font-weight: 700; }
    .sw-step h3 { font-size: 1.1rem; margin: .7rem 0 .3rem; }
    .sw-badges { display: flex; flex-wrap: wrap; gap: .5rem; margin: .5rem 0 1rem; }
    .sw-badge { display: inline-block; border-radius: 12px; padding: .3rem .75rem;
      background: #f5f5f4; color: #44403c; font-size: .9rem; font-weight: 650; }
    .sw-badge.success { background: #e0f1e6; color: #18532e; }
    .sw-badge.attention { background: #fff0ce; color: #714809; }
    .sw-badge.danger { background: #fbe6e2; color: #8b2822; }
    .sw-badge.info { background: #e4eff9; color: #234e78; }
    .sw-timeline { list-style: none; padding-left: 0; }
    .sw-timeline li { position: relative; border-left: 2px solid #d6d3d1;
      margin-left: 10px; padding: 0 0 1.3rem 1.6rem; }
    .sw-timeline li::before { content: ''; position: absolute; left: -7px; top: 6px;
      width: 12px; height: 12px; border-radius: 50%; background: var(--sw-action); }
    .sw-timeline time { display: block; color: var(--sw-metadata); font-size: .9rem; }
    .sw-empty p { color: var(--sw-metadata); margin-bottom: 0; }
    @media (max-width: 760px) {
      .block-container { padding: 4rem .85rem 2rem; }
      .sw-steps { grid-template-columns: 1fr 1fr; }
      [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
      [data-testid="stColumn"] { min-width: min(100%, 260px); flex: 1 1 260px; }
      [data-testid="stForm"] { padding: 1rem; }
      .st-key-public_header [data-testid="stColumn"] { min-width: 0; flex: 1 1 135px; }
      .st-key-public_header [data-testid="stColumn"]:first-child { flex-basis: 100%; }
      .st-key-hero_actions [data-testid="stColumn"] { min-width: 0; flex: 1 1 180px; }
      [data-testid="stButtonGroup"] { flex-wrap: wrap; }
      [data-testid="stMetricValue"] { font-size: 1.7rem; }
    }
    @media (max-width: 440px) { .sw-steps { grid-template-columns: 1fr; } }
    @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
    </style>"""
    variables = "; ".join(f"--sw-{name.replace('_', '-')}: {value}" for name, value in COLORS.items())
    variables += "; --sw-action: var(--sw-primary-action); --sw-hover: var(--sw-primary-hover);"
    st.markdown(css.replace("__TOKENS__", variables), unsafe_allow_html=True)
