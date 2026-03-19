"""Fortuna — Logs page for viewing and exporting error logs."""

import streamlit as st
import database as db


def render():
    st.markdown("# Logs")

    logs = db.get_logs(limit=200)

    if not logs:
        st.info("No logs yet.")
        return

    col_clear, col_copy = st.columns([1, 5])
    with col_clear:
        if st.button("Clear Logs", key="clear_logs"):
            db.clear_logs()
            st.rerun()

    with col_copy:
        export = _format_logs_for_export(logs)
        st.download_button(
            "Export Logs",
            data=export,
            file_name="fortuna_logs.txt",
            mime="text/plain",
            key="export_logs",
        )

    for log in logs:
        ts = log["timestamp"]
        level = log["level"].upper()
        source = log["source"]
        message = log["message"]

        if level == "ERROR":
            icon = "red"
        elif level == "WARNING":
            icon = "orange"
        else:
            icon = "gray"

        header = f'<span style="color:{icon}; font-weight:600;">[{level}]</span> {ts} — {source}'
        st.markdown(header, unsafe_allow_html=True)
        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{message}")

        if log.get("detail"):
            with st.expander("Full details"):
                st.code(log["detail"], language="text")

        st.markdown("---")


def _format_logs_for_export(logs: list[dict]) -> str:
    lines = []
    for log in logs:
        lines.append(f"[{log['level'].upper()}] {log['timestamp']} | {log['source']}")
        lines.append(f"  {log['message']}")
        if log.get("detail"):
            lines.append(f"  Detail: {log['detail']}")
        lines.append("")
    return "\n".join(lines)
