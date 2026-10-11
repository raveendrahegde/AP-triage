"""Run with: streamlit run app.py"""
from pathlib import Path
from datetime import datetime, timezone
import json

import streamlit as st

from triage import cached_triage

ROOT = Path(__file__).resolve().parent / "invoices"
for status in ("pending", "approved", "denied"):
    (ROOT / status).mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="InvoiceRadar", page_icon="📡", layout="wide")
st.markdown("""
<style>
.block-container { max-width: 1200px; padding-top: 4.5rem; }
.st-key-radar-header { padding: 1.8rem 2rem; border-radius: 24px; margin-bottom: .6rem;
    background: linear-gradient(115deg, #dce6c8, #cadbb5 60%, #e9dfaa);
    border: 1px solid #d3d9c6; }
.profile-avatar { width: 42px; height: 42px; border-radius: 50%; background: #faf8ee;
    color: #36543c; display: flex; align-items: center; justify-content: center;
    font-weight: 800; border: 2px solid #a8bc8f; }
.radar-hero h1 { color: #293d30; margin: 0; padding: 0; font-size: clamp(2rem, 4vw, 2.8rem); }
.radar-hero p { margin: .65rem 0 0; color: #4d624c; }
.radar-eyebrow { color: #516943; font-size: .75rem; letter-spacing: .16em; font-weight: 700; }
.confidence-panel { padding: .8rem 1rem; border: 1px solid #d3d9c6;
    border-radius: 14px; background: #fcfbf5; color: #293d30; }
@media (max-width: 640px) { .st-key-radar-header { padding: 1.2rem; } }
.confidence-heading { display: flex; justify-content: space-between;
    align-items: center; gap: .6rem; flex-wrap: wrap; margin-bottom: .65rem; }
.confidence-status { font-size: .75rem; font-weight: 800; padding: .2rem .55rem;
    border-radius: 6px; }
.confidence-inspect { background: #fef3c7; color: #92400e; }
.confidence-normal { background: #dcfce7; color: #166534; }
.confidence-track { height: 12px; background: #e2e8f0; border-radius: 999px;
    position: relative; overflow: hidden; }
.confidence-fill { position: absolute; inset: 0;
    background: linear-gradient(90deg, #dc2626 0%, #f59e0b 50%, #16a34a 100%); }
.confidence-scale { display: flex; justify-content: space-between;
    font-size: .7rem; color: #475569; margin-top: .35rem; }
.confidence-note { font-size: .72rem; color: #475569; margin-top: .4rem; }
[data-testid="stMetric"] { border: 1px solid #d3d9c6; border-radius: 14px; padding: 1rem; }
[data-testid="stButton"] button { cursor: pointer; transition: background .15s, box-shadow .15s; }
[data-testid="stButton"] button:hover { box-shadow: 0 0 0 3px #8fa77455; }
[data-testid="stButton"] button:focus-visible { outline: 3px solid #66834e; outline-offset: 3px; }
[class*="st-key-deny-action-"] button { background: #fff1f2; color: #9f1239; border: 1px solid #fda4af; }
[class*="st-key-deny-action-"] button:hover,
[class*="st-key-deny-action-"] button:focus-visible { background: #be123c; color: white;
    border-color: #be123c; box-shadow: 0 0 0 3px #fda4af66; }
[class*="st-key-deny-action-"] button:active { background: #881337; color: white; }
</style>
""", unsafe_allow_html=True)


def source(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lower().startswith("source:"):
            return line.split(":", 1)[1].strip()
    return "Unknown source"


def amount(result):
    value = result["amount"]
    return f"USD {value:,.2f}" if value is not None else "Unknown amount"


def confidence_meter(result):
    confidence = result["confidence"]
    inspect = result["recommendation"] == "INSPECT"
    status = "INSPECT" if inspect else "NORMAL"
    tone = "inspect" if inspect else "normal"
    icon = "🔎" if inspect else "✓"
    st.markdown(f"""
<div class="confidence-panel">
  <div class="confidence-heading">
    <span class="confidence-status confidence-{tone}">{icon} {status}</span>
    <strong>{confidence}% confidence</strong>
  </div>
  <div class="confidence-track" role="meter" aria-label="Confidence in extraction and triage assessment"
       aria-valuemin="0" aria-valuemax="100" aria-valuenow="{confidence}">
    <div class="confidence-fill" style="clip-path: inset(0 {100 - confidence}% 0 0)"></div>
  </div>
  <div class="confidence-scale"><span>0% · Low</span><span>100% · High</span></div>
  <div class="confidence-note">Confidence in the assessment · human decision required</div>
</div>
""", unsafe_allow_html=True)


def decide(path, status, reason=""):
    """Only called by explicit human buttons; move the pair without overwriting."""
    if status == "denied" and not reason.strip():
        st.error("Please enter a reason for denying this invoice.")
        return
    destination = ROOT / status / path.name
    sidecar = path.with_suffix(".json")
    target_sidecar = destination.with_suffix(".json")
    try:
        if destination.exists() or target_sidecar.exists():
            raise FileExistsError("An invoice with this filename already exists in the destination.")
        if not sidecar.exists():
            cached_triage(path)
        original = sidecar.read_text(encoding="utf-8")
        assessment = json.loads(original)
        if status == "pending":
            previous = assessment.pop("_decision", None)
            assessment.setdefault("_history", []).append({
                "action": "reverted", "by": "Ravee",
                "at": datetime.now(timezone.utc).isoformat(),
                "previous_status": path.parent.name, "previous_decision": previous,
            })
        else:
            assessment["_decision"] = {
                "by": "Ravee", "status": status, "reason": reason.strip(),
                "at": datetime.now(timezone.utc).isoformat(),
            }
        temporary = sidecar.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(assessment, indent=2), encoding="utf-8")
        temporary.replace(sidecar)
        try:
            sidecar.rename(target_sidecar)
        except OSError:
            sidecar.write_text(original, encoding="utf-8")
            raise
        try:
            path.rename(destination)
        except OSError:
            target_sidecar.rename(sidecar)
            sidecar.write_text(original, encoding="utf-8")
            raise
    except (OSError, ValueError) as error:
        st.error(f"Could not move invoice: {error}")
        return
    st.session_state.pop("inspecting", None)
    st.session_state.pop("denying", None)
    st.session_state["notice"] = f"Human decision saved: {path.name} → {status}."
    st.rerun()


def close_denial():
    st.session_state.pop("denying", None)


@st.dialog("Deny invoice", on_dismiss=close_denial)
def denial_popup(path):
    st.write(f"**Invoice:** {path.name}")
    st.caption("Decision recorded by Ravee · demo profile")
    with st.form(f"denial-form-{path.stem}"):
        reason = st.text_area("Reason for denial", placeholder="Explain why this invoice should be denied…",
                              key=f"denial-reason-{path.stem}", max_chars=2000)
        confirm, cancel = st.columns(2)
        submitted = confirm.form_submit_button("Confirm denial", type="primary")
        cancelled = cancel.form_submit_button("Cancel")
    if cancelled:
        close_denial()
        st.rerun()
    if submitted:
        decide(path, "denied", reason)


logged_in = st.session_state.get("mock_logged_in", True)
with st.container(key="radar-header"):
    brand, account = st.columns([3, 1.4], vertical_alignment="top")
    with brand:
        st.markdown("""
<div class="radar-hero">
  <div class="radar-eyebrow">YOUR ACCOUNTS PAYABLE CONTROL ROOM</div>
  <h1>📡 InvoiceRadar</h1>
  <p>Spot the signals in messy invoices. Keep every decision in human hands.</p>
</div>
""", unsafe_allow_html=True)
    with account:
        avatar, menu = st.columns([1, 4], vertical_alignment="center")
        avatar.markdown('<div class="profile-avatar" role="img" aria-label="Profile picture placeholder: RH">RH</div>',
                        unsafe_allow_html=True)
        with menu:
            with st.popover("Raveendra Hegde" if logged_in else "Demo login", width="stretch"):
                st.write("**Raveendra Hegde**")
                st.caption("Mock profile")
                st.write("Role: **AP Specialist**")
                if logged_in:
                    if st.button("Log out", key="mock-logout"):
                        st.session_state["mock_logged_in"] = False
                        st.session_state.pop("inspecting", None)
                        close_denial()
                        st.rerun()
                else:
                    if st.button("Log in as Raveendra Hegde", key="mock-login", type="primary"):
                        st.session_state["mock_logged_in"] = True
                        st.rerun()
        st.caption("AP Specialist · Demo workspace" if logged_in else "Sign in to the demo workspace")

if not logged_in:
    st.info("Open Demo login in the header to continue as Raveendra Hegde.")
    st.stop()

st.info("Higher confidence means clearer signals — not a payment recommendation.")
# st.caption("Local text-file prototype • USD demo invoices • no database")
if notice := st.session_state.pop("notice", None):
    st.success(notice)

files = {status: sorted((ROOT / status).glob("*.txt"))
         for status in ("pending", "approved", "denied")}
columns = st.columns(3)
for column, status in zip(columns, files):
    column.metric(status.title(), len(files[status]))

pending, approved, denied = st.tabs(["Pending", "Approved", "Denied"])
with pending:
    if not files["pending"]:
        st.success("All caught up. No pending invoices.")
    for path in files["pending"]:
        try:
            with st.spinner(f"Reading {path.name}…"):
                result = cached_triage(path)
        except (OSError, ValueError) as error:
            st.error(f"Could not read {path.name}: {error}")
            continue
        with st.container(border=True):
            heading, badge = st.columns([3, 2])
            heading.subheader(result["vendor"] or "Unknown vendor")
            with badge:
                confidence_meter(result)
            st.write(f"**{result['invoice_number'] or 'Unknown invoice number'}** · {amount(result)}")
            st.caption(f"{source(path)} · {result['_mode']}")
            st.caption(result["reasons"][0])
            inspecting = st.session_state.get("inspecting") == path.name
            if inspecting:
                st.divider()
                st.write("**Extracted fields**")
                st.json({key: result[key] for key in
                         ("vendor", "invoice_number", "amount", "due_date")})
                st.write("**Reasons**")
                for reason in result["reasons"]:
                    st.write(f"• {reason}")
                st.write("**Missing information**")
                for missing in result["missing_information"] or ["None identified in the supplied text."]:
                    st.write(f"• {missing}")
                st.warning(result["human_question"] or "Review the invoice before deciding.")
                st.write("**Original invoice / email text**")
                st.code(path.read_text(encoding="utf-8"), language=None, wrap_lines=True)
                a, b, c = st.columns(3)
                if a.button("Approve", key=f"detail-approve-{path.name}", type="primary"):
                    decide(path, "approved")
                with b:
                    with st.container(key=f"deny-action-{path.stem}"):
                        if st.button("Deny", key=f"deny-{path.name}",
                                     help="Record your decision and move this invoice to Denied."):
                            st.session_state["denying"] = path.name
                            st.rerun()
                if c.button("Back", key=f"back-{path.name}"):
                    st.session_state.pop("inspecting", None)
                    st.rerun()
            else:
                a, b = st.columns(2)
                if a.button("Approve", key=f"approve-{path.name}", type="primary"):
                    decide(path, "approved")
                if b.button("Inspect", key=f"inspect-{path.name}"):
                    st.session_state["inspecting"] = path.name
                    st.rerun()

for tab, status in ((approved, "approved"), (denied, "denied")):
    with tab:
        if not files[status]:
            st.caption(f"No {status} invoices yet.")
        rows = []
        archive_entries = []
        for path in files[status]:
            try:
                result = cached_triage(path)
                decision = result.get("_decision", {})
                row = {"Vendor": result["vendor"] or "Unknown",
                             "Amount": amount(result),
                             "Invoice number": result["invoice_number"] or "Unknown",
                             "Source": source(path),
                             "Approved by" if status == "approved" else "Denied by": decision.get("by", "Ravee")}
                if status == "denied":
                    row["Denial reason"] = decision.get("reason") or "Not recorded"
                rows.append(row)
                archive_entries.append((path, result))
            except (OSError, ValueError) as error:
                st.error(f"Could not read {path.name}: {error}")
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
            st.caption("Return an invoice to Pending for another review.")
            for path, result in archive_entries:
                label, action = st.columns([5, 1])
                label.write(f"**{result['vendor'] or 'Unknown vendor'}** · {result['invoice_number'] or path.name}")
                if action.button("Revert", key=f"revert-{status}-{path.name}",
                                 help="Move this invoice and its cached assessment back to Pending."):
                    decide(path, "pending")

if denying := st.session_state.get("denying"):
    path = ROOT / "pending" / Path(denying).name
    if path.exists():
        denial_popup(path)
    else:
        close_denial()
