# 🛡️ SD Worx — Trusted Knowledge Hub

> **Tectonic Hackathon 2026 Submission for SD Worx Challenge: "Unlock the Knowledge Within"**

## 🎯 Problem Statement & Core Concept

Inside large organizations like SD Worx, knowledge lives in fragmented policies, manuals, emails, and Teams chats. Searching often returns 10 answers, but employees struggle with **Trust**: *Is this answer reliable, current, and verified for my specific country or role?*

**Our Solution**: A centralized **Trusted Knowledge Hub** featuring:
1. **AI Document Pre-Audit**: Ingests files and automatically detects numerical rate changes, missing metadata, and conflicts with existing policies.
2. **Human-in-the-Loop Checkpoint Queue**: Enables HR and payroll experts to review AI audit flags, credit document ownership, assign trust badges, and mark superseded legacy guidance.
3. **Trust-Aware RAG Engine**: Generates answers strictly from human-verified documents, showing explicit credibility badges and expert citations.
4. **Smart Human Escalation & Expert Routing**: If AI confidence is low or information is undocumented, the system automatically routes the user to a credited subject-matter expert with direct Teams & email contacts.

---

## 🚀 3-Tab Streamlit Application Architecture

1. **🛑 1. Human Checkpoint Queue**: 
   - Upload new policy PDFs or text files.
   - Run AI conflict pre-audit (detects rate changes, unverified drafts).
   - Expert Verification Panel (Approve, Supersede, or Reject).
2. **🗄️ 2. Credited Database (Knowledge Vault)**:
   - Overview of all ingested & verified documents.
   - Trust scores, verification history, assigned expert owners, and lineage.
3. **💬 3. Trust-Aware Chatbot & Expert Routing**:
   - RAG search returning trusted answers + source citations + trust badges.
   - Automatic escalation card for low-confidence queries directing to the right employee.

---

## 🛠️ Quick Start / How to Run

### Prerequisites
- Python 3.10+ installed

### Step 1: Install Dependencies
```bash
pip install streamlit pypdf google-genai pandas
```

### Step 2: Run the Streamlit Web App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🛡️ Security & Aikido Compliance
- **Input Sanitization**: File uploads are pre-scanned and stripped of script vectors.
- **SQL Parameterization**: All SQLite queries use strict parameter binding to prevent SQL injection.
- **Role-Based Audit Trail**: Documents record credited owners and verification timestamps for compliance audits.
