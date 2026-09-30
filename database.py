import sqlite3
import json
import os
import shutil
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_hub.db")
BASE_DIR = os.path.dirname(__file__)

PENDING_DIR = os.path.join(BASE_DIR, "pending_documents")
APPROVED_DIR = os.path.join(BASE_DIR, "approved_documents")
REJECTED_DIR = os.path.join(BASE_DIR, "rejected_documents")

def init_folders():
    for d in [PENDING_DIR, APPROVED_DIR, REJECTED_DIR]:
        os.makedirs(d, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    init_folders()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        file_path TEXT,
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

    # Migration check for existing DB files
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN file_path TEXT;")
        conn.commit()
    except Exception:
        pass

    # Experts Directory
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

    # Query Logs
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

    # Re-seed Experts
    cursor.execute("DELETE FROM experts;")
    seed_experts = [
        ("Jane Doe", "Senior Payroll Legal Specialist", "Payroll & Tax Compliance (BE)", "jane.doe@example.com", "#payroll-legal-help"),
        ("John Smith", "HR Policy Lead", "Remote Work & Employee Benefits", "john.smith@example.com", "#hr-policy-help"),
        ("Chris Jordan", "International Mobility Specialist", "Cross-Border Tax & Mobility", "chris.jordan@example.com", "#global-mobility"),
        ("Morgan Lee", "Data Compliance Officer", "GDPR & Document Governance", "morgan.lee@example.com", "#compliance-governance")
    ]
    cursor.executemany(
        "INSERT INTO experts (name, role, domain, email, teams_channel) VALUES (?, ?, ?, ?, ?)",
        seed_experts
    )
    conn.commit()
    conn.close()

def reset_demo_environment():
    """
    Resets the demo environment:
    1. Moves all files from approved_documents/ and rejected_documents/ back into pending_documents/.
    2. Clears documents and query logs tables.
    3. Re-creates initial sample text files in pending_documents/.
    """
    init_folders()
    
    # 1. Move files back to pending_documents/
    for src_dir in [APPROVED_DIR, REJECTED_DIR]:
        if os.path.exists(src_dir):
            for fname in os.listdir(src_dir):
                src_file = os.path.join(src_dir, fname)
                if os.path.isfile(src_file):
                    dest_file = os.path.join(PENDING_DIR, fname)
                    try:
                        shutil.move(src_file, dest_file)
                    except Exception as e:
                        print(f"Move reset notice: {e}")

    # 2. Reset database tables
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents;")
    cursor.execute("DELETE FROM query_logs;")
    conn.commit()
    conn.close()

    # 3. Create sample pending documents in pending_documents/
    doc1 = os.path.join(PENDING_DIR, "Belgium_Statutory_Remote_Work_Policy_2026.txt")
    with open(doc1, "w", encoding="utf-8") as f:
        f.write(
            "Official 2026 statutory guidelines for Belgian employees performing structural telework.\n"
            "Author: Jane Doe\n"
            "The maximum tax-exempt home office allowance is set to €154.00 per month starting January 1, 2026.\n"
            "Employers may additionally grant an internet allowance of up to €20.00 per month if specific telework agreements are registered."
        )

    doc2 = os.path.join(PENDING_DIR, "Draft_Flexible_Work_Policy_2026.txt")
    with open(doc2, "w", encoding="utf-8") as f:
        f.write(
            "Draft Flexible Work & Remote Work Policy (2026 Revision)\n"
            "Author: John Smith\n"
            "Region: EU General / Belgium\n\n"
            "Overview:\n"
            "This draft proposes allowing employees to choose a 4-day work week (38 hours compressed) subject to department head approval.\n"
            "Overtime rules in France and Germany require specific opt-in agreements prior to working compressed hours."
        )

    doc3 = os.path.join(PENDING_DIR, "Proposed_Germany_CrossBorder_Tax_Guide.txt")
    with open(doc3, "w", encoding="utf-8") as f:
        f.write(
            "Proposed Germany-Belgium Cross-Border Tax Guide 2026\n"
            "Author: Chris Jordan\n"
            "Region: Germany / Belgium\n\n"
            "For employees residing in Germany and commuting to work in Belgium, double taxation treaties dictate that salary tax is withheld in the state where activity is physically performed."
        )

    doc4 = os.path.join(PENDING_DIR, "Legacy_2024_Home_Allowance_Guidance.txt")
    with open(doc4, "w", encoding="utf-8") as f:
        f.write(
            "Legacy 2024 Home Allowance Guidance\n"
            "Author: Anonymous\n"
            "The monthly home office allowance for Belgian employees is €148.45 per month. Applicable for tax year 2024."
        )

def add_document(doc_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO documents 
        (id, title, file_path, category, region, author, upload_date, status, content, summary, ai_confidence_score, ai_audit_flags, credited_owner, expert_notes, verification_date, trust_badge)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            doc_data["id"],
            doc_data["title"],
            doc_data.get("file_path", ""),
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
    print("Database initialized.")
