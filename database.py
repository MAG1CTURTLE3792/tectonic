import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_hub.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT,
        region TEXT,
        author TEXT,
        upload_date TEXT,
        status TEXT DEFAULT 'PENDING_CHECKPOINT',
        content TEXT,
        summary TEXT,
        ai_confidence_score REAL,
        ai_audit_flags TEXT,
        credited_owner TEXT,
        expert_notes TEXT,
        verification_date TEXT,
        trust_badge TEXT
    );
    """)

    # Experts Directory for Smart Routing
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS experts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        domain TEXT NOT NULL,
        email TEXT NOT NULL,
        teams_channel TEXT
    );
    """)

    # RAG Query Audit & Escalation Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        query TEXT,
        answer TEXT,
        confidence REAL,
        routed_to_expert TEXT,
        status TEXT
    );
    """)

    conn.commit()

    # Seed initial Experts if empty
    cursor.execute("SELECT COUNT(*) FROM experts;")
    if cursor.fetchone()[0] == 0:
        seed_experts = [
            ("Marc Peeters", "Senior Payroll Legal Specialist", "Payroll & Tax Compliance (BE)", "marc.peeters@sdworx.com", "#be-payroll-legal"),
            ("Sophie Laurent", "HR Policy Lead", "Remote Work & Employee Benefits", "sophie.laurent@sdworx.com", "#hr-policies"),
            ("Jan Van Damme", "International Mobility Specialist", "Cross-Border Tax & Mobility", "jan.vandamme@sdworx.com", "#global-mobility"),
            ("Elena Rostova", "Data Compliance Officer", "GDPR & Document Governance", "elena.rostova@sdworx.com", "#compliance-governance")
        ]
        cursor.executemany(
            "INSERT INTO experts (name, role, domain, email, teams_channel) VALUES (?, ?, ?, ?, ?)",
            seed_experts
        )
        conn.commit()

    # Seed initial documents if empty
    cursor.execute("SELECT COUNT(*) FROM documents;")
    if cursor.fetchone()[0] == 0:
        seed_documents = [
            (
                "doc_001",
                "Belgium Statutory Remote Work Policy 2026.pdf",
                "Payroll & Tax",
                "Belgium",
                "Sarah Devos",
                "2026-01-15",
                "APPROVED",
                "Official 2026 statutory guidelines for Belgian employees performing structural telework. The maximum tax-exempt home office allowance is set to €154.00 per month starting January 1, 2026. Employers may additionally grant an internet allowance of up to €20.00 per month if specific telework agreements are registered.",
                "Official 2026 Belgian remote work tax allowance document (€154/mo office + €20/mo internet).",
                0.96,
                json.dumps([]),
                "Marc Peeters (Senior Legal Specialist)",
                "Verified against Belgian Federal Gazette Q1 2026.",
                "2026-01-18",
                "Verified Official Policy"
            ),
            (
                "doc_002",
                "Legacy 2024 Home Allowance Guidance.pdf",
                "Payroll & Tax",
                "Belgium",
                "Anonymous",
                "2024-03-10",
                "SUPERSEDED",
                "The monthly home office allowance for Belgian employees is €148.45 per month. Applicable for tax year 2024.",
                "Outdated 2024 home allowance rate of €148.45.",
                0.40,
                json.dumps(["SUPERSEDED_BY_DOC_001", "Rate change detected: €148.45 vs €154.00"]),
                "Marc Peeters",
                "Marked as superseded by Doc_001 (2026 updated rates).",
                "2026-01-18",
                "Superseded / Archival"
            ),
            (
                "doc_003",
                "Draft Flexible Work Arrangement Policy (Unverified).docx",
                "HR Policy",
                "EU General",
                "Alex Rivera",
                "2026-09-28",
                "PENDING_CHECKPOINT",
                "Proposed guidelines for flexible working hours across EU offices allowing 4-day work weeks subject to local management approval. Requires legal compliance check regarding overtime rules in France and Germany.",
                "Draft policy for 4-day work week in EU offices under review.",
                0.62,
                json.dumps(["Unverified author", "Potential legal conflict with local overtime laws in FR/DE", "Missing formal owner"]),
                None,
                None,
                None,
                "Unverified Ingestion"
            )
        ]
        cursor.executemany(
            """INSERT INTO documents 
            (id, title, category, region, author, upload_date, status, content, summary, ai_confidence_score, ai_audit_flags, credited_owner, expert_notes, verification_date, trust_badge)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            seed_documents
        )
        conn.commit()

    conn.close()

def add_document(doc_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO documents 
        (id, title, category, region, author, upload_date, status, content, summary, ai_confidence_score, ai_audit_flags, credited_owner, expert_notes, verification_date, trust_badge)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            doc_data["id"],
            doc_data["title"],
            doc_data.get("category", "General"),
            doc_data.get("region", "Global"),
            doc_data.get("author", "Unknown"),
            doc_data.get("upload_date", datetime.now().strftime("%Y-%m-%d")),
            doc_data.get("status", "PENDING_CHECKPOINT"),
            doc_data.get("content", ""),
            doc_data.get("summary", ""),
            doc_data.get("ai_confidence_score", 0.5),
            json.dumps(doc_data.get("ai_audit_flags", [])),
            doc_data.get("credited_owner", None),
            doc_data.get("expert_notes", None),
            doc_data.get("verification_date", None),
            doc_data.get("trust_badge", "Unverified")
        )
    )
    conn.commit()
    conn.close()

def update_document_checkpoint(doc_id, status, credited_owner, expert_notes, trust_badge):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE documents 
        SET status = ?, credited_owner = ?, expert_notes = ?, verification_date = ?, trust_badge = ?
        WHERE id = ?""",
        (status, credited_owner, expert_notes, datetime.now().strftime("%Y-%m-%d %H:%M"), trust_badge, doc_id)
    )
    conn.commit()
    conn.close()

def get_all_documents(status_filter=None):
    conn = get_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM documents WHERE status = ? ORDER BY upload_date DESC", (status_filter,))
    else:
        cursor.execute("SELECT * FROM documents ORDER BY upload_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_experts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM experts")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_query(query, answer, confidence, routed_to_expert, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO query_logs (timestamp, query, answer, confidence, routed_to_expert, status) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query, answer, confidence, routed_to_expert, status)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
