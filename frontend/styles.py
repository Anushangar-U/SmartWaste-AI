"""Static civic theme; no user content is interpolated into this stylesheet."""
import streamlit as st


def apply_styles():
    st.markdown("""<style>
    :root { --primary-color: #176448; --text-color: #182d26;
      --background-color: #f7f9f6; --secondary-background-color: #edf2ed; }
    .stApp { background: #f7f9f6; color: #182d26; }
    .block-container { max-width: 1200px; padding-top: 2rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: #153e2f; letter-spacing: -.025em; }
    p, label, li { line-height: 1.6; }
    [data-testid="stCaptionContainer"] { color: #486056; font-size: .9rem; }
    [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] > div {
      border-color: #d9e3db; border-radius: 16px; }
    [data-testid="stForm"] { background: #fff; padding: 1.5rem; }
    .stButton button, .stFormSubmitButton button {
      min-height: 46px; border-radius: 10px; font-weight: 600; }
    button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
      background: #176448; color: #fff; border-color: #176448; }
    button[kind="secondary"] { background: #fff; color: #184631; border-color: #b8cbbd; }
    button:focus-visible, input:focus-visible, textarea:focus-visible {
      outline: 3px solid #bd7400 !important; outline-offset: 3px; }
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
      background: #fff; color: #182d26; border-color: #9db3a5; }
    input, textarea { color: #182d26 !important; caret-color: #176448; }
    [data-testid="stMetric"] { background: #fff; border: 1px solid #d9e3db;
      border-radius: 14px; padding: 1.1rem; }
    [data-testid="stMetricValue"] { color: #153e2f; }
    .sw-brand { font-size: 1.45rem; font-weight: 750; color: #153e2f; }
    .sw-brand span { display: inline-grid; place-items: center; background: #176448;
      color: white; width: 36px; height: 36px; border-radius: 10px; margin-right: 9px; }
    .sw-eyebrow { color: #176448; font-size: .82rem; font-weight: 750;
      letter-spacing: .12em; text-transform: uppercase; margin-bottom: .7rem; }
    .sw-hero { background: #eaf2e9; border: 1px solid #d5e3d3; border-radius: 24px;
      padding: clamp(1.5rem, 5vw, 3.5rem); margin: .5rem 0 1rem; }
    .sw-hero h1 { font-size: clamp(2.3rem, 5vw, 4.4rem); line-height: 1.08;
      margin: 0 0 1.2rem; max-width: 760px; }
    .sw-hero p { font-size: 1.15rem; max-width: 650px; color: #354f40; }
    .sw-trust { border-left: 4px solid #176448; background: #edf3ee;
      padding: 1rem 1.2rem; border-radius: 0 12px 12px 0; margin: .6rem 0 1.2rem; }
    .sw-steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;
      margin: 1rem 0 2rem; }
    .sw-step, .sw-empty { background: #fff; border: 1px solid #d9e3db;
      border-radius: 16px; padding: 1.3rem; }
    .sw-step-number { display: inline-grid; place-items: center; width: 34px; height: 34px;
      background: #eaf2e9; border-radius: 50%; color: #176448; font-weight: 700; }
    .sw-step h3 { font-size: 1.1rem; margin: .7rem 0 .3rem; }
    .sw-badges { display: flex; flex-wrap: wrap; gap: .5rem; margin: .5rem 0 1rem; }
    .sw-badge { display: inline-block; border-radius: 30px; padding: .3rem .75rem;
      background: #e9efeb; color: #2d4b3b; font-size: .9rem; font-weight: 650; }
    .sw-badge.success { background: #e0f1e6; color: #18532e; }
    .sw-badge.attention { background: #fff0ce; color: #714809; }
    .sw-badge.danger { background: #fbe6e2; color: #8b2822; }
    .sw-badge.info { background: #e4eff9; color: #234e78; }
    .sw-timeline { list-style: none; padding-left: 0; }
    .sw-timeline li { position: relative; border-left: 2px solid #c8d9cc;
      margin-left: 10px; padding: 0 0 1.3rem 1.6rem; }
    .sw-timeline li::before { content: ''; position: absolute; left: -7px; top: 6px;
      width: 12px; height: 12px; border-radius: 50%; background: #176448; }
    .sw-timeline time { display: block; color: #486056; font-size: .9rem; }
    .sw-empty p { color: #486056; margin-bottom: 0; }
    @media (max-width: 760px) {
      .block-container { padding: 1rem .85rem 2rem; }
      .sw-steps { grid-template-columns: 1fr 1fr; }
      [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
      [data-testid="stColumn"] { min-width: min(100%, 260px); flex: 1 1 260px; }
      [data-testid="stForm"] { padding: 1rem; }
    }
    @media (max-width: 440px) { .sw-steps { grid-template-columns: 1fr; } }
    @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
    </style>""", unsafe_allow_html=True)
