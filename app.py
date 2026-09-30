import streamlit as st
import pandas as pd
import json
import uuid
import os
import shutil
import pypdf
import io
from database import (
    init_db, get_all_documents, add_document, 
    update_document_checkpoint, get_experts, log_query,
    reset_demo_environment, PENDING_DIR, APPROVED_DIR, REJECTED_DIR
)
from ai_engine import audit_document_with_ai, query_trusted_rag, get_accredited_authors

init_db()

st.set_page_config(
    page_title="SD Worx | Trusted Knowledge Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    
    .header-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .header-title { color: #f8fafc; font-size: 28px; font-weight: 700; margin: 0; }
    .header-subtitle { color: #94a3b8; font-size: 15px; margin-top: 6px; }
    
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .metric-val { font-size: 32px; font-weight: 800; color: #38bdf8; }
    .metric-label { font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
    
    .badge-approved { background-color: #064e3b; color: #34d399; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid #059669; }
    .badge-pending { background-color: #78350f; color: #fbbf24; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid #d97706; }
    .badge-superseded { background-color: #451a03; color: #f97316; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid #ea580c; }
    
    .conflict-box { background-color: #450a0a; border: 1px solid #991b1b; border-radius: 10px; padding: 12px 16px; color: #fca5a5; font-size: 14px; margin-top: 10px; }
    .success-box { background-color: #064e3b; border: 1px solid #059669; border-radius: 10px; padding: 12px 16px; color: #a7f3d0; font-size: 14px; margin-top: 10px; }
    .expert-card { background: linear-gradient(135deg, #1e1b4b 0%, #311b92 100%); border: 1px solid #6366f1; border-radius: 14px; padding: 18px; color: #e0e7ff; margin-top: 15px; }
    .source-card { background: #1e293b; border-left: 4px solid #38bdf8; padding: 12px; border-radius: 8px; margin-top: 10px; }
    .chunk-box { background: #0f172a; border: 1px dashed #475569; padding: 10px; border-radius: 6px; font-family: monospace; font-size: 13px; color: #cbd5e1; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown("""
<div class="header-box">
    <div class="header-title">🛡️ SD Worx — Trusted Knowledge Hub</div>
    <div class="header-subtitle">Verified Organizational Intelligence with AI Auto-Approve & Side-by-Side Human Checkpoint</div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/verified-account.png", width=64)
    st.subheader("System Status")
    st.success("🟢 Grounded RAG Engine: Active")
    st.success("🟢 Author Whitelist Check: Active")
    
    st.divider()
    st.markdown("### 🛠️ Debug & Testing Controls")
    if st.button("🔄 Reset Environment (Move all files back to Pending)", use_container_width=True):
        reset_demo_environment()
        st.success("Demo environment reset! All files moved back to pending_documents/.")
        st.rerun()

    st.divider()
    accredited = get_accredited_authors()
    st.markdown("### 📜 Accredited Authors Whitelist")
    for a in accredited:
        st.markdown(f"• `{a}`")

    st.divider()
    experts = get_experts()
    st.markdown("### 👥 Credited Experts Directory")
    for exp in experts:
        st.markdown(f"**{exp['name']}**  \n*{exp['role']}*  \n`📧 {exp['email']}`")
        st.caption(f"Domain: {exp['domain']}")
        st.markdown("---")


# 4 Distinct Tabs
tab_upload, tab_sidebyside, tab_database, tab_chatbot = st.tabs([
    "📥 1. Document Upload & Ingestion",
    "⚖️ 2. Side-by-Side Verification Checkpoint",
    "🗄️ 3. Credited Database (Knowledge Vault)",
    "💬 4. Trust-Aware Chatbot & Expert Routing"
])


def process_folder_batch(auto_approve_threshold=None):
    """
    Helper function to process pending files in pending_documents/ directory.
    If auto_approve_threshold is set (e.g., 0.80), documents with AI score >= threshold
    and accredited authors will be automatically approved!
    """
    pending_files = [f for f in os.listdir(PENDING_DIR) if os.path.isfile(os.path.join(PENDING_DIR, f))]
    auto_approved_cnt = 0
    imported_cnt = 0

    experts_list = get_experts()

    for fname in pending_files:
        fpath = os.path.join(PENDING_DIR, fname)
        content = ""
        if fname.endswith(".pdf"):
            try:
                with open(fpath, "rb") as pf:
                    reader = pypdf.PdfReader(pf)
                    for page in reader.pages:
                        content += page.extract_text() or ""
            except Exception as e:
                content = f"Error reading PDF: {e}"
        else:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as tf:
                content = tf.read()

        author_guess = "Jane Doe" if "jane" in content.lower() or "doe" in content.lower() else ("John Smith" if "john" in content.lower() else ("Chris Jordan" if "chris" in content.lower() else "Unknown"))
        audit_res = audit_document_with_ai(fname, content, author=author_guess)

        score = audit_res["ai_confidence_score"]
        is_accredited = audit_res["is_author_accredited"]

        # Check if high confidence auto-approval applies
        if auto_approve_threshold and score >= auto_approve_threshold and is_accredited:
            new_status = "APPROVED"
            badge = "Verified (AI High-Confidence Auto-Approved)"
            credited_owner = f"{author_guess} (Legal/HR Specialist)" if author_guess != "Unknown" else "Jane Doe (Senior Legal Specialist)"
            expert_notes = "Automatically approved by AI Batch Scanner due to High Confidence Score (>= 0.80) & Accredited Author match."

            # Move file to approved_documents/
            dest_path = os.path.join(APPROVED_DIR, fname)
            try:
                shutil.move(fpath, dest_path)
                fpath = dest_path
            except Exception:
                pass

            add_document({
                "id": f"doc_{uuid.uuid4().hex[:6]}",
                "title": fname,
                "file_path": fpath,
                "category": audit_res["suggested_category"],
                "region": "Belgium" if "belgium" in fname.lower() else "EU General",
                "author": author_guess,
                "status": "APPROVED",
                "content": content,
                "summary": audit_res["summary"],
                "ai_confidence_score": score,
                "ai_audit_flags": audit_res["ai_audit_flags"],
                "credited_owner": credited_owner,
                "expert_notes": expert_notes,
                "verification_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                "trust_badge": badge
            })
            auto_approved_cnt += 1
        else:
            add_document({
                "id": f"doc_{uuid.uuid4().hex[:6]}",
                "title": fname,
                "file_path": fpath,
                "category": audit_res["suggested_category"],
                "region": "Belgium" if "belgium" in fname.lower() else "EU General",
                "author": author_guess,
                "status": "PENDING_CHECKPOINT",
                "content": content,
                "summary": audit_res["summary"],
                "ai_confidence_score": score,
                "ai_audit_flags": audit_res["ai_audit_flags"],
                "trust_badge": audit_res["suggested_badge"]
            })
            imported_cnt += 1

    return len(pending_files), auto_approved_cnt, imported_cnt


# ==========================================
# TAB 1: DOCUMENT UPLOAD & INGESTION
# ==========================================
with tab_upload:
    st.markdown("### 📥 Document Ingestion & Folder Queue")
    st.caption("Upload new document files or drop them into `pending_documents/` folder. Run manual import or AI Batch Auto-Approve.")

    pending_files = [f for f in os.listdir(PENDING_DIR) if os.path.isfile(os.path.join(PENDING_DIR, f))]
    
    st.markdown(f"#### 📂 `pending_documents/` Folder Scanner ({len(pending_files)} files in folder)")

    b_col1, b_col2, b_col3 = st.columns([1, 1, 1])
    with b_col1:
        if st.button("🔄 Import Pending Files to Queue", use_container_width=True):
            total, auto_app, queued = process_folder_batch(auto_approve_threshold=None)
            st.success(f"Imported {total} files into Verification Queue!")
            st.rerun()

    with b_col2:
        if st.button("⚡ AI Batch Scan & Auto-Approve (Score >= 0.80)", use_container_width=True):
            with st.spinner("AI Batch Scanner evaluating folder documents..."):
                total, auto_app, queued = process_folder_batch(auto_approve_threshold=0.80)
                st.success(f"⚡ AI Batch Scan Complete! **{auto_app}** high-confidence docs auto-approved & indexed. **{queued}** doc(s) kept for human checkpoint.")
                st.rerun()

    with b_col3:
        if st.button("🗑️ Reset Environment", use_container_width=True):
            reset_demo_environment()
            st.success("Demo environment reset!")
            st.rerun()

    st.divider()

    st.markdown("#### 📤 Manual Upload Form")
    with st.form("ingest_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            doc_title = st.text_input("Document Title *", placeholder="e.g. Netherlands Remote Policy 2026.pdf")
            doc_author = st.text_input("Uploaded By / Author *", placeholder="e.g. Jane Doe, John Smith...")
        with f_col2:
            doc_category = st.selectbox("Category", ["Payroll & Tax", "HR Policy", "Legal Compliance", "Employee Benefits", "Global Mobility"])
            doc_region = st.selectbox("Applicable Region", ["Belgium", "Netherlands", "Germany", "France", "EU General", "Global"])
        
        uploaded_file = st.file_uploader("Attach PDF or Text File", type=["pdf", "txt", "md"])
        manual_text = st.text_area("Or Paste Raw Document Content", height=130, placeholder="Paste policy text here...")
        
        submit_ingest = st.form_submit_button("🚀 Ingest & Audit Document", use_container_width=True)

    if submit_ingest:
        if not doc_title:
            st.error("Please provide a document title.")
        else:
            content = ""
            file_dest_path = ""
            if uploaded_file is not None:
                file_dest_path = os.path.join(PENDING_DIR, uploaded_file.name)
                with open(file_dest_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if uploaded_file.name.endswith(".pdf"):
                    pdf_reader = pypdf.PdfReader(io.BytesIO(uploaded_file.getbuffer()))
                    for page in pdf_reader.pages:
                        content += page.extract_text() or ""
                else:
                    content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            elif manual_text:
                content = manual_text
            else:
                content = doc_title

            with st.spinner("AI Pre-Audit checking accredited_authors.txt & detecting rate conflicts..."):
                audit_res = audit_document_with_ai(doc_title, content, doc_region, doc_author or "Unknown")

                new_doc = {
                    "id": f"doc_{uuid.uuid4().hex[:6]}",
                    "title": doc_title,
                    "file_path": file_dest_path,
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
                st.success(f"✅ '{doc_title}' ingested! Switch to Tab 2 to verify side-by-side.")


# ==========================================
# TAB 2: SIDE-BY-SIDE VERIFICATION CHECKPOINT
# ==========================================
with tab_sidebyside:
    st.markdown("### ⚖️ Side-by-Side Expert Verification Checkpoint")
    st.caption("Read document contents on the left while reviewing AI audit flags and taking verification actions on the right.")

    # Batch Auto-Approve Button inside Tab 2
    sc1, sc2 = st.columns([2, 1])
    with sc1:
        st.markdown("#### Pending Verification Queue")
    with sc2:
        if st.button("⚡ Run AI Auto-Approve (Score >= 0.80)", key="batch_tab2", use_container_width=True):
            with st.spinner("AI Batch Scanner evaluating pending documents..."):
                # Also process pending DB items
                pending_db_docs = get_all_documents(status_filter="PENDING_CHECKPOINT")
                auto_approved_cnt = 0
                for d in pending_db_docs:
                    if d["ai_confidence_score"] >= 0.80:
                        # Move file if present
                        file_path = d.get("file_path")
                        if file_path and os.path.exists(file_path):
                            dest_path = os.path.join(APPROVED_DIR, os.path.basename(file_path))
                            try:
                                shutil.move(file_path, dest_path)
                            except Exception:
                                pass
                        update_document_checkpoint(
                            d["id"], "APPROVED", 
                            d["author"] + " (Specialist)", 
                            "Auto-Approved by AI Batch Scan (Score >= 0.80)", 
                            "Verified (AI High-Confidence Auto-Approved)"
                        )
                        auto_approved_cnt += 1
                st.success(f"⚡ Auto-Approved **{auto_approved_cnt}** document(s) with AI Score >= 0.80!")
                st.rerun()

    pending_docs = get_all_documents(status_filter="PENDING_CHECKPOINT")

    if not pending_docs:
        st.info("🎉 All documents in the queue have been reviewed! No pending items in the checkpoint queue.")
    else:
        selected_doc_title = st.selectbox(
            f"Select Document to Verify ({len(pending_docs)} Pending):",
            [d["title"] for d in pending_docs]
        )
        
        doc = next(d for d in pending_docs if d["title"] == selected_doc_title)

        st.divider()

        # Side-by-Side Split View Layout
        col_doc_reader, col_verify_action = st.columns([1.3, 1.0], gap="large")

        # LEFT COLUMN: Document Reader & AI Audit Inspection
        with col_doc_reader:
            st.markdown(f"#### 📖 Document Reader: `{doc['title']}`")
            
            acc_list = get_accredited_authors()
            is_acc = any(a.lower() in doc['author'].lower() or doc['author'].lower() in a.lower() for a in acc_list)
            
            if is_acc:
                st.markdown(f"<div class='success-box'>✅ Accredited Author Whitelist Match: <b>{doc['author']}</b></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='conflict-box'>⚠️ Unaccredited Author Notice: Author <b>'{doc['author']}'</b> is NOT in accredited_authors.txt</div>", unsafe_allow_html=True)

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f"**Category**: `{doc['category']}`")
            with m2:
                st.markdown(f"**Region**: `{doc['region']}`")
            with m3:
                st.markdown(f"**AI Score**: `{doc['ai_confidence_score']}`")

            st.markdown(f"**AI Summary**: {doc['summary']}")

            flags = json.loads(doc['ai_audit_flags']) if doc['ai_audit_flags'] else []
            if flags:
                st.markdown("**AI Pre-Audit Findings:**")
                for flag in flags:
                    if "ACCREDITED AUTHOR" in flag:
                        st.markdown(f"<div class='success-box'>{flag}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='conflict-box'>{flag}</div>", unsafe_allow_html=True)

            st.markdown("##### Full Document Content")
            st.text_area("Reader View", value=doc['content'], height=250, disabled=True, key=f"reader_{doc['id']}")

        # RIGHT COLUMN: Verification Actions
        with col_verify_action:
            st.markdown("#### ⚖️ Human Expert Action Panel")
            st.caption("Perform verification and credit the document owner.")

            with st.form(key=f"verify_form_side_{doc['id']}"):
                credited_owner = st.selectbox(
                    "Assign Credited Owner *",
                    [e["name"] + f" ({e['role']})" for e in experts],
                    key=f"owner_side_{doc['id']}"
                )
                
                expert_notes = st.text_area(
                    "Verification Notes & Justification", 
                    placeholder="Enter compliance verification details or rate confirmations...", 
                    height=120,
                    key=f"notes_side_{doc['id']}"
                )
                
                st.markdown("##### Select Action:")
                btn_approve = st.form_submit_button("✅ Approve Document", use_container_width=True)
                btn_supersede = st.form_submit_button("🔄 Approve & Supersede Legacy", use_container_width=True)
                btn_reject = st.form_submit_button("❌ Reject Document", use_container_width=True)

                if btn_approve or btn_supersede or btn_reject:
                    new_status = "APPROVED" if (btn_approve or btn_supersede) else "REJECTED"
                    badge = "Verified Official Policy" if btn_approve else ("Verified (Supersedes Legacy)" if btn_supersede else "Rejected / Invalid")
                    
                    file_path = doc.get("file_path")
                    if file_path and os.path.exists(file_path):
                        dest_dir = APPROVED_DIR if new_status == "APPROVED" else REJECTED_DIR
                        dest_path = os.path.join(dest_dir, os.path.basename(file_path))
                        try:
                            shutil.move(file_path, dest_path)
                        except Exception as e:
                            print(f"File move notice: {e}")

                    update_document_checkpoint(doc['id'], new_status, credited_owner, expert_notes, badge)
                    st.success(f"Document '{doc['title']}' updated to {new_status}!")
                    st.rerun()


# ==========================================
# TAB 3: CREDITED DATABASE (KNOWLEDGE VAULT)
# ==========================================
with tab_database:
    st.markdown("### 🗄️ Centralized Credited Database")
    st.caption("View all verified organizational documents, active trust scores, assigned placeholder owners, and lineage.")

    all_docs = get_all_documents()

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

    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        status_filter = st.multiselect("Filter Status", ["APPROVED", "PENDING_CHECKPOINT", "SUPERSEDED", "REJECTED"], default=["APPROVED", "PENDING_CHECKPOINT", "SUPERSEDED"])
    with f_col2:
        search_kw = st.text_input("🔍 Search Database by title, content, or owner", placeholder="e.g. Belgium allowance, Jane Doe...")

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
                st.markdown(f"**Credited Owner**: `{doc['credited_owner'] or 'Jane Doe'}`")
            with m2:
                st.markdown(f"**Category**: `{doc['category']}`")
                st.markdown(f"**Trust Badge**: `{doc['trust_badge'] or 'None'}`")
            with m3:
                st.markdown(f"**AI Trust Score**: `{doc['ai_confidence_score']}`")
                st.markdown(f"**Verification Date**: `{doc['verification_date'] or 'Pending'}`")

            st.markdown(f"**Summary**: {doc['summary']}")
            if doc['expert_notes']:
                st.info(f"💡 **Expert Note**: {doc['expert_notes']}")

            st.text_area("Full Document Text Content", value=doc['content'], height=120, disabled=True, key=f"vault_{doc['id']}")


# ==========================================
# TAB 4: TRUST-AWARE CHATBOT & EXPERT ROUTING
# ==========================================
with tab_chatbot:
    st.markdown("### 💬 Grounded RAG Chatbot & Smart Expert Escalation")
    st.caption("Retrieves semantic passage chunks from human-verified documents. Low similarity triggers direct expert routing.")

    st.markdown("**Sample queries:**")
    sample_q1, sample_q2, sample_q3 = st.columns(3)
    
    selected_query = ""
    with sample_q1:
        if st.button("📌 Belgian home office tax rate 2026?", use_container_width=True):
            selected_query = "What is the monthly tax-free home office allowance for Belgian employees in 2026?"
    with sample_q2:
        if st.button("📌 German cross-border tax rules?", use_container_width=True):
            selected_query = "What are the cross-border tax rules for German employees commuting to Belgium?"
    with sample_q3:
        if st.button("📌 Overtime laws in France?", use_container_width=True):
            selected_query = "What are the overtime compensation rules for teleworkers in France?"

    user_query = st.text_input("Ask a question about SD Worx policies & guidelines:", value=selected_query, placeholder="e.g. What is the home office allowance in 2026?")

    if user_query:
        with st.spinner("Chunking documents, running vector TF-IDF retrieval & synthesizing answer..."):
            rag_result = query_trusted_rag(user_query)
            log_query(
                user_query, 
                rag_result["answer"], 
                rag_result["confidence"], 
                rag_result["routed_to_expert"]["name"] if rag_result["routed_to_expert"] else None,
                "ROUTED_LOW_CONFIDENCE" if rag_result["has_expert_escalation"] else "ANSWERED_HIGH_TRUST"
            )

            st.divider()

            if rag_result["has_expert_escalation"]:
                st.warning("⚠️ **Low Vector Similarity / Unverified Query Escalation**")
            else:
                st.success(f"🛡️ **Grounded RAG Answer** | Vector Confidence Score: `{rag_result['confidence'] * 100}%` | Badge: `{rag_result['trust_badge']}`")

            st.markdown(f"### Answer\n{rag_result['answer']}")

            if rag_result.get("warnings"):
                for w in rag_result["warnings"]:
                    st.markdown(f"<div class='conflict-box'>⚠️ {w}</div>", unsafe_allow_html=True)

            if rag_result.get("retrieved_chunks"):
                st.markdown("#### 🔍 Grounded RAG Context Chunks Retrieved")
                for idx, chunk_info in enumerate(rag_result["retrieved_chunks"]):
                    st.markdown(f"**Chunk #{idx+1}** | Vector Similarity Score: `{round(chunk_info['score'], 2)}` | Source: `{chunk_info['doc_title']}` | Credited Owner: `{chunk_info['credited_owner']}`")
                    st.markdown(f"<div class='chunk-box'>{chunk_info['chunk_text']}</div>", unsafe_allow_html=True)

            if rag_result["has_expert_escalation"] and rag_result.get("routed_to_expert"):
                exp = rag_result["routed_to_expert"]
                st.markdown(f"""
                <div class="expert-card">
                    <h4>👤 Smart Human Escalation Checkpoint</h4>
                    <p>This query relates to unverified or undocumented procedures. Rather than guessing, the system has routed your question directly to the designated domain expert:</p>
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
