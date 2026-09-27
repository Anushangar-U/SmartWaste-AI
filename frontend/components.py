"""Presentation helpers. Every dynamic HTML value is escaped at this boundary."""
from datetime import datetime
from html import escape
import streamlit as st

STATUS_LABELS = {
    "submitted": "Submitted", "processing": "Processing",
    "awaiting_review": "Awaiting Staff Review", "reviewed": "Staff Reviewed",
    "assigned": "Assigned", "processing_failed": "Processing Failed", "resolved": "Resolved",
}
STATUS_TONES = {"awaiting_review": "attention", "processing_failed": "danger",
                "resolved": "success", "assigned": "info", "processing": "info"}


def label(value):
    return STATUS_LABELS.get(value, str(value or "Not available").replace("_", " ").title())


def timestamp(value):
    if not value:
        return "Not available"
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.strftime("%d %b %Y · %H:%M %Z").strip()
    except (ValueError, TypeError):
        return "Date unavailable"


def badges(*items):
    """Each item is (visible label, semantic tone); unknown tones stay neutral."""
    tags = []
    for text, tone in items:
        tone = tone if tone in {"success", "attention", "danger", "info"} else ""
        tags.append(f'<span class="sw-badge {tone}">{escape(str(text))}</span>')
    st.markdown('<div class="sw-badges">' + ''.join(tags) + '</div>', unsafe_allow_html=True)


def status_badge(status):
    badges((label(status), STATUS_TONES.get(status, "")))


def empty_state(title, description):
    st.markdown(f'<section class="sw-empty"><strong>{escape(title)}</strong>'
                f'<p>{escape(description)}</p></section>', unsafe_allow_html=True)


def timeline(events, *, current=None):
    if not events:
        st.caption("No status changes have been recorded yet.")
        return
    # Only actual recorded events appear; missing/skipped stages are never ticked off.
    entries = []
    for i, event in enumerate(events):
        suffix = " · Current status" if i == len(events) - 1 and event.get("status") == current else ""
        entries.append('<li><strong>' + escape(label(event.get("status")) + suffix) +
                       '</strong><time>' + escape(timestamp(event.get("at") or event.get("created_at"))) + '</time></li>')
    st.markdown('<ol class="sw-timeline" aria-label="Recorded complaint status history">' +
                ''.join(entries) + '</ol>', unsafe_allow_html=True)


def demo_notice(mode):
    if mode == "mock_demo":
        st.warning("DEMO MODE · AI outputs shown in this mode are synthetic examples.")


def evidence_card(number, item):
    with st.container(border=True):
        st.text(f"[{number}] {item.get('title') or 'Supporting document'}")
        st.text(" · ".join(str(v) for v in (item.get("issuer"), item.get("year")) if v))
        st.caption(f"PDF page {item.get('page', 'Unknown')} · Semantic similarity: {item.get('score', 0):.3f}")
        st.text(item.get("text", ""))
        with st.expander(f"Source details · passage {number}"):
            st.text("Filename: " + item.get("source", "Unknown"))
            st.text("Chunk: " + item.get("chunk_id", "Unknown"))


def field(name, value):
    st.caption(name)
    st.text(str(value) if value is not None and value != "" else "Not supplied")
