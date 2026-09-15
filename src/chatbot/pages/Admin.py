"""Admin page — review and decide on pending reservation approvals."""
import os

import httpx
import streamlit as st

_API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Admin — Approvals", page_icon="🔑", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 Admin Access")
    admin_token = st.text_input("Admin token", type="password", key="admin_token")
    st.divider()
    st.caption(f"API: `{_API_BASE}`")

if not admin_token:
    st.title("Admin — Pending Approvals")
    st.info("Enter your admin token in the sidebar to continue.")
    st.stop()

_headers = {"Authorization": f"Bearer {admin_token}"}


def _fetch_pending() -> tuple[list[dict] | None, str | None]:
    try:
        r = httpx.get(
            f"{_API_BASE}/admin/reservations/pending",
            headers=_headers,
            timeout=10,
        )
        if r.status_code == 401:
            return None, "Invalid admin token."
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, f"Cannot reach API at {_API_BASE}."
    except Exception as exc:
        return None, str(exc)


def _approve(request_id: str) -> bool:
    r = httpx.post(
        f"{_API_BASE}/admin/reservation/{request_id}/approve",
        headers=_headers,
        timeout=10,
    )
    return r.status_code == 204


def _reject(request_id: str, reason: str) -> bool:
    r = httpx.post(
        f"{_API_BASE}/admin/reservation/{request_id}/reject",
        headers=_headers,
        json={"reason": reason or None},
        timeout=10,
    )
    return r.status_code == 204


def _fetch_log() -> list[str] | None:
    try:
        r = httpx.get(
            f"{_API_BASE}/admin/reservations/log",
            headers=_headers,
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.title("🔑 Pending Approvals")
with col_refresh:
    st.write("")  # vertical spacing
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# ── Fetch ─────────────────────────────────────────────────────────────────────
pending, error = _fetch_pending()

if error:
    st.error(f"⚠️ {error}")
    st.stop()

if not pending:
    st.success("✅ No pending approvals — all clear.")
else:
    st.caption(f"{len(pending)} request(s) awaiting decision")
    st.divider()

# ── Cards ─────────────────────────────────────────────────────────────────────
for req in (pending or []):
    rid = req["request_id"]
    created = req["created_at"][:16].replace("T", " ")

    with st.container(border=True):
        info_col, action_col = st.columns([3, 2])

        with info_col:
            st.markdown(
                f"**{req['first_name']} {req['surname']}** &nbsp;·&nbsp; `{req['license_plate']}`"
            )
            st.markdown(f"🗓 **{req['start_datetime']}** → **{req['end_datetime']}**")
            st.caption(f"Submitted: {created} &nbsp;|&nbsp; ID: `{rid}`")

        with action_col:
            reason = st.text_input(
                "Reason",
                key=f"reason_{rid}",
                placeholder="Rejection reason (optional)",
                label_visibility="collapsed",
            )
            btn_approve, btn_reject = st.columns(2)
            with btn_approve:
                if st.button("✅ Approve", key=f"approve_{rid}", use_container_width=True, type="primary"):
                    if _approve(rid):
                        st.toast(f"Approved — {req['first_name']} {req['surname']}", icon="✅")
                        st.rerun()
                    else:
                        st.error("Failed — request may have already been decided.")
            with btn_reject:
                if st.button("❌ Reject", key=f"reject_{rid}", use_container_width=True):
                    if _reject(rid, reason):
                        st.toast(f"Rejected — {req['first_name']} {req['surname']}", icon="❌")
                        st.rerun()
                    else:
                        st.error("Failed — request may have already been decided.")

# ── Audit Log ─────────────────────────────────────────────────────────────────
st.divider()
with st.expander("📋 Approved Reservations Audit Log (MCP-written)", expanded=False):
    log_lines = _fetch_log()
    if log_lines is None:
        st.warning("Could not fetch audit log.")
    elif not log_lines:
        st.info("No approved reservations written yet.")
    else:
        rows = []
        for line in log_lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 4:
                rows.append({"Name": parts[0], "Plate": parts[1], "Period": parts[2], "Approved (UTC)": parts[3]})
            else:
                rows.append({"Name": line, "Plate": "", "Period": "", "Approved (UTC)": ""})
        st.dataframe(rows, use_container_width=True, hide_index=True)
