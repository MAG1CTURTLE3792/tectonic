import streamlit as st
import pandas as pd
import json
import uuid
import pypdf
import io
from database import (
    init_db, get_all_documents, add_document, 
    update_document_checkpoint, get_experts, log_query
)
from ai_engine import audit_document_with_ai, query_trusted_rag

# Initialize DB on start
init_db()

# Page configuration
st.set_page_config(
    page_title="SD Worx | Trusted Knowledge Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design & Visual Polish
st.markdown("""
<style>
    /* Global Styles */
    .main {
        background-color: #0e1117;
    }
    
    /* Header Container */
    .header-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .header-title {
        color: #f8fafc;
        font-size: 28px;
        font-weight: 700;
        margin: 0;
    }
    .header-subtitle {
        color: #94a3b8;
        font-size: 15px;
        margin-top: 6px;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .metric-val {
        font-size: 32px;
        font-weight: 800;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Trust Badges */
    .badge-approved {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #059669;
    }
    .badge-pending {
        background-color: #78350f;
        color: #fbbf24;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #d97706;
    }
    .badge-superseded {
        background-color: #451a03;
        color: #f97316;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #ea580c;
    }
    
    /* Conflict Alert Box */
    .conflict-box {
        background-color: #450a0a;
        border: 1px solid #991b1b;
        border-radius: 10px;
        padding: 12px 16px;
        color: #fca5a5;
        font-size: 14px;
        margin-top: 10px;
    }

    /* Expert Card */
    .expert-card {
        background: linear-gradient(135deg, #1e1b4b 0%, #311b92 100%);
        border: 1px solid #6366f1;
        border-radius: 14px;
        padding: 18px;
        color: #e0e7ff;
        margin-top: 15px;
    }

    /* Chat bubble source card */
    .source-card {
        background: #1e293b;
        border-left: 4px solid #38bdf8;
        padding: 12px;
        border-radius: 8px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_class_immutably=True)

# Application Header
st.markdown("""
<div class="header-box">
    <div class="header-title">🛡️ SD Worx — Trusted Knowledge Hub</div>
    <div class="header-subtitle">Verified Organizational Intelligence with Human-in-the-Loop Credibility & Smart RAG</div>
</div>
""", unsafe_allow_html=True)

# Sidebar — System Info & Stats
with st.sidebar:
    st.image("https://img.icons8.com/color/96/verified-account.png", width=64)
    st.subheader("System Status")
    st.success("🟢 AI Pre-Audit Engine: Active")
    st.success("🟢 Vector RAG Search: Operational")
    st.info("💡 Hackathon Mode: Dual AI + Heuristic Fallback")
    
    st.divider()
    st.markdown("### 🏆 SD Worx Challenge Focus")
    st.caption("**Trust & Verification**: Turning fragmented files into credited, expert-approved answers with human oversight.")
    
    st.divider()
    experts = get_experts()
    st.markdown("### 👥 Credited Experts Directory")
    for exp in experts:
        st.markdown(f"**{exp['name']}**  \n*{exp['role']}*  \n`📧 {exp['email']}`")
        st.caption(f"Domain: {exp['domain']}")
        st.markdown("---")


# Main Tabs
tab_checkpoint, tab_database, tab_chatbot = st.tabs([
    "🛑 1. Human Checkpoint Queue",
    "🗄️ 2. Credited Database (Knowledge Vault)",
    "💬 3. Trust-Aware Chatbot & Expert Routing"
])


# ==========================================
# TAB 1: HUMAN CHECKPOINT QUEUE
# ==========================================
with tab_checkpoint:
    st.markdown("### 🛑 Document Ingestion & Human Checkpoint")
    st.caption("Upload new policies, manuals, or emails. AI performs an automated pre-audit to flag conflicts before expert verification.")

    col_ingest, col_queue = st.columns([1, 1], gap="large")

    with col_ingest:
        st.markdown("#### 📥 Document Ingestion Form")
        with st.form("ingest_form", clear_on_submit=True):
            doc_title = st.text_input("Document Title *", placeholder="e.g. Belgium Payroll Guidelines 2026.pdf")
            doc_category = st.selectbox("Category", ["Payroll & Tax", "HR Policy", "Legal Compliance", "Employee Benefits", "Global Mobility"])
            doc_region = st.selectbox("Applicable Region", ["Belgium", "Netherlands", "Germany", "France", "EU General", "Global"])
            doc_author = st.text_input("Uploaded By / Author", placeholder="e.g. Sarah Devos")
            
            uploaded_file = st.file_uploader("Attach PDF or Text File", type=["pdf", "txt", "md"])
            manual_text = st.text_area("Or Paste Raw Document Content", height=150, placeholder="Paste text contents here...")
            
            submit_ingest = st.form_submit_button("🚀 Submit to AI Pre-Audit", use_container_width=True)

        if submit_ingest:
            if not doc_title:
                st.error("Please provide a document title.")
            else:
                content = ""
                if uploaded_file is not None:
                    if uploaded_file.name.endswith(".pdf"):
                        pdf_reader = pypdf.PdfReader(io.BytesIO(uploaded_file.read()))
                        for page in pdf_reader.pages:
                            content += page.extract_text() or ""
                    else:
                        content = uploaded_file.read().decode("utf-8", errors="ignore")
                elif manual_text:
                    content = manual_text
                else:
                    content = doc_title # Fallback if empty

                with st.spinner("AI Engine is auditing document for conflicts & trust flags..."):
                    audit_res = audit_document_with_ai(doc_title, content, doc_region)

                    new_doc = {
                        "id": f"doc_{uuid.uuid4().hex[:6]}",
                        "title": doc_title,
                        "category": doc_category,
                        "region": doc_region,
                        "author": doc_author or "Unknown",
                        "status": "PENDING_CHECKPOINT",
                        "content": content,
                        "summary": audit_res["summary"],
                        "ai_confidence_score": audit_res["ai_confidence_score"],
                        "ai_audit_flags": audit_res["ai_audit_flags"],
                        "trust_badge": audit_res["suggested_badge"]
                    }
                    add_document(new_doc)
                    st.success(f"✅ '{doc_title}' ingested! Sent to Human Checkpoint Queue.")

    with col_queue:
        st.markdown("#### 📋 Pending Human Checkpoint Queue")
        pending_docs = get_all_documents(status_filter="PENDING_CHECKPOINT")

        if not pending_docs:
            st.info("🎉 All documents are reviewed! No pending items in the checkpoint queue.")
        else:
            for doc in pending_docs:
                with st.expander(f"⚠️ {doc['title']} (Score: {doc['ai_confidence_score']})", expanded=True):
                    st.markdown(f"**Category**: `{doc['category']}` | **Region**: `{doc['region']}` | **Author**: `{doc['author']}`")
                    st.markdown(f"**AI Summary**: {doc['summary']}")
                    
                    # Audit Flags
                    flags = json.loads(doc['ai_audit_flags']) if doc['ai_audit_flags'] else []
                    if flags:
                        st.markdown("**AI Conflict & Warning Flags:**")
                        for flag in flags:
                            st.markdown(f"<div class='conflict-box'>🚨 {flag}</div>", unsafe_allow_html=True)
                    else:
                        st.caption("🟢 AI detected no immediate rate conflicts.")

                    st.divider()
                    st.markdown("##### 👩‍⚖️ Expert Verification Checkpoint")
                    
                    with st.form(key=f"verify_form_{doc['id']}"):
                        credited_owner = st.selectbox(
                            "Assign Credited Owner *",
                            [e["name"] + f" ({e['role']})" for e in experts],
                            key=f"owner_{doc['id']}"
                        )
                        expert_notes = st.text_area("Verification Notes / Justification", placeholder="Add reason for approval or rate verification...", key=f"notes_{doc['id']}")
                        
                        action_col1, action_col2, action_col3 = st.columns(3)
                        with action_col1:
                            approve_btn = st.form_submit_button("✅ Approve", use_container_width=True)
                        with action_col2:
                            supersede_btn = st.form_submit_button("🔄 Approve & Supersede", use_container_width=True)
                        with action_col3:
                            reject_btn = st.form_submit_button("❌ Reject", use_container_width=True)

                        if approve_btn:
                            update_document_checkpoint(doc['id'], "APPROVED", credited_owner, expert_notes, "Verified Official Policy")
                            st.success("Document approved & indexed into Centralized Credited Database!")
                            st.rerun()
                        elif supersede_btn:
                            update_document_checkpoint(doc['id'], "APPROVED", credited_owner, expert_notes, "Verified (Supersedes Legacy)")
                            st.success("Document approved as official replacement!")
                            st.rerun()
                        elif reject_btn:
                            update_document_checkpoint(doc['id'], "REJECTED", credited_owner, expert_notes or "Rejected at checkpoint", "Rejected / Invalid")
                            st.warning("Document rejected.")
                            st.rerun()


# ==========================================
# TAB 2: CREDITED DATABASE (KNOWLEDGE VAULT)
# ==========================================
with tab_database:
    st.markdown("### 🗄️ Centralized Credited Database")
    st.caption("View all verified organizational documents, active trust scores, assigned expert owners, and lineage.")

    all_docs = get_all_documents()

    # Metric summary row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-val'>{len(all_docs)}</div><div class='metric-label'>Total Ingested Docs</div></div>", unsafe_allow_html=True)
    with c2:
        approved_cnt = len([d for d in all_docs if d['status'] == 'APPROVED'])
        st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#34d399;'>{approved_cnt}</div><div class='metric-label'>Approved & Credited</div></div>", unsafe_allow_html=True)
    with c3:
        pending_cnt = len([d for d in all_docs if d['status'] == 'PENDING_CHECKPOINT'])
        st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#fbbf24;'>{pending_cnt}</div><div class='metric-label'>Pending Checkpoint</div></div>", unsafe_allow_html=True)
    with c4:
        superseded_cnt = len([d for d in all_docs if d['status'] in ['SUPERSEDED', 'REJECTED']])
        st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#f97316;'>{superseded_cnt}</div><div class='metric-label'>Superseded / Archival</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter controls
    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        status_filter = st.multiselect("Filter Status", ["APPROVED", "PENDING_CHECKPOINT", "SUPERSEDED", "REJECTED"], default=["APPROVED", "PENDING_CHECKPOINT", "SUPERSEDED"])
    with f_col2:
        search_kw = st.text_input("🔍 Search Database by title, content, or owner", placeholder="e.g. Belgium allowance, Marc Peeters...")

    filtered_docs = [d for d in all_docs if d["status"] in status_filter]
    if search_kw:
        sk = search_kw.lower()
        filtered_docs = [d for d in filtered_docs if sk in d["title"].lower() or sk in d["content"].lower() or (d["credited_owner"] and sk in d["credited_owner"].lower())]

    st.markdown("#### Document Registry")
    for doc in filtered_docs:
        status_class = "badge-approved" if doc['status'] == 'APPROVED' else ("badge-pending" if doc['status'] == 'PENDING_CHECKPOINT' else "badge-superseded")
        
        with st.expander(f"[{doc['status']}] {doc['title']} — Region: {doc['region']}"):
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f"**Status**: <span class='{status_class}'>{doc['status']}</span>", unsafe_allow_html=True)
                st.markdown(f"**Credited Owner**: `{doc['credited_owner'] or 'Unassigned'}`")
            with m2:
                st.markdown(f"**Category**: `{doc['category']}`")
                st.markdown(f"**Trust Badge**: `{doc['trust_badge'] or 'None'}`")
            with m3:
                st.markdown(f"**AI Trust Score**: `{doc['ai_confidence_score']}`")
                st.markdown(f"**Verification Date**: `{doc['verification_date'] or 'Pending'}`")

            st.markdown(f"**Summary**: {doc['summary']}")
            if doc['expert_notes']:
                st.info(f"💡 **Expert Note**: {doc['expert_notes']}")

            with st.container():
                st.text_area("Full Document Text Content", value=doc['content'], height=120, disabled=True, key=f"text_{doc['id']}")


# ==========================================
# TAB 3: TRUST-AWARE CHATBOT & EXPERT ROUTING
# ==========================================
with tab_chatbot:
    st.markdown("### 💬 Trust-Aware AI Search & Chatbot")
    st.caption("Ask operational questions. Answers are derived ONLY from human-verified documents. Low confidence triggers direct expert routing.")

    # Preset Sample Queries for Hackathon Testing
    st.markdown("**Try sample questions:**")
    sample_q1, sample_q2, sample_q3 = st.columns(3)
    
    selected_query = ""
    with sample_q1:
        if st.button("📌 Belgian home office tax rate 2026?", use_container_width=True):
            selected_query = "What is the monthly tax-free home office allowance for Belgian employees in 2026?"
    with sample_q2:
        if st.button("📌 4-Day Work Week policy rules?", use_container_width=True):
            selected_query = "What is the policy for 4-day flexible work week in EU offices?"
    with sample_q3:
        if st.button("📌 Cross-border German tax rules?", use_container_width=True):
            selected_query = "What are the cross-border tax rules for German employees commuting to Belgium?"

    # Chat input
    user_query = st.text_input("Ask a question about SD Worx policies & guidelines:", value=selected_query, placeholder="e.g. What is the home office allowance in 2026?")

    if user_query:
        with st.spinner("Searching credited knowledge base & calculating trust score..."):
            rag_result = query_trusted_rag(user_query)
            log_query(
                user_query, 
                rag_result["answer"], 
                rag_result["confidence"], 
                rag_result["routed_to_expert"]["name"] if rag_result["routed_to_expert"] else None,
                "ROUTED_LOW_CONFIDENCE" if rag_result["has_expert_escalation"] else "ANSWERED_HIGH_TRUST"
            )

            st.divider()

            # Answer Header with Trust Badge
            if rag_result["has_expert_escalation"]:
                st.warning("⚠️ **Low Confidence / Unverified Domain Alert**")
            else:
                st.success(f"🛡️ **Trust Verified Answer** | Confidence Score: `{rag_result['confidence'] * 100}%` | Badge: `{rag_result['trust_badge']}`")

            # Display main answer text
            st.markdown(f"### Answer\n{rag_result['answer']}")

            # Display Warnings / Conflict Notices if any
            if rag_result.get("warnings"):
                for w in rag_result["warnings"]:
                    st.markdown(f"<div class='conflict-box'>⚠️ {w}</div>", unsafe_allow_html=True)

            # Display Credited Sources
            if rag_result.get("sources"):
                st.markdown("#### 📑 Credited Sources & Lineage")
                for src in rag_result["sources"]:
                    st.markdown(f"""
                    <div class="source-card">
                        <strong>📄 {src['title']}</strong><br/>
                        <span style="color:#94a3b8; font-size:13px;">
                            Credited Expert Owner: <b>{src['credited_owner']}</b> | Verified: {src['verification_date']} | Region: {src['region']}
                        </span><br/>
                        <span style="color:#cbd5e1; font-size:14px; margin-top:4px; display:block;">
                            Summary: {src['summary']}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

            # SMART EXPERT ROUTING CARD (If low confidence or unverified)
            if rag_result["has_expert_escalation"] and rag_result.get("routed_to_expert"):
                exp = rag_result["routed_to_expert"]
                st.markdown(f"""
                <div class="expert-card">
                    <h4>👤 Smart Human Escalation Checkpoint</h4>
                    <p>This query relates to unverified or undocumented procedures. Rather than guessing, the system has routed your question directly to the designated SD Worx expert:</p>
                    <hr style="border-color:#6366f1; margin:10px 0;"/>
                    <p><b>Expert Name</b>: {exp['name']}<br/>
                    <b>Role</b>: {exp['role']}<br/>
                    <b>Domain Expertise</b>: {exp['domain']}<br/>
                    <b>Direct Email</b>: <code>{exp['email']}</code><br/>
                    <b>Teams Channel</b>: <code>{exp['teams_channel']}</code></p>
                    <button style="background:#4f46e5; color:white; border:none; padding:8px 16px; border-radius:6px; font-weight:600; cursor:pointer;">
                        📩 Contact {exp['name'].split()[0]} on Teams
                    </button>
                </div>
                """, unsafe_allow_html=True)

st.divider()
st.caption("Tectonic Hackathon 2026 — Built for SD Worx Challenge: 'Unlock the Knowledge Within'")
