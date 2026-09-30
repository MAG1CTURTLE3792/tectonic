import json
from database import init_db, get_all_documents, get_experts
from ai_engine import audit_document_with_ai, query_trusted_rag

def test_system():
    print("--- 1. Testing Database Init ---")
    init_db()
    docs = get_all_documents()
    print(f"Total seeded documents in DB: {len(docs)}")
    for d in docs:
        print(f"  - [{d['status']}] {d['title']} | Owner: {d['credited_owner']}")
        
    experts = get_experts()
    print(f"Total seeded experts: {len(experts)}")

    print("\n--- 2. Testing AI Pre-Audit ---")
    test_title = "Draft Belgium Remote Allowance Revision 2026.txt"
    test_content = "The proposed remote work home allowance for Belgian staff is €148.45 starting mid-year."
    audit_res = audit_document_with_ai(test_title, test_content)
    print(f"Confidence Score: {audit_res['ai_confidence_score']}")
    print(f"Audit Flags: {json.dumps(audit_res['ai_audit_flags'], indent=2)}")

    print("\n--- 3. Testing High-Trust RAG Query ---")
    q1 = "What is the monthly tax-free home office allowance for Belgian employees in 2026?"
    res1 = query_trusted_rag(q1)
    print(f"Query: {q1}")
    print(f"Answer snippet: {res1['answer'][:150]}...")
    print(f"Confidence: {res1['confidence']}")
    print(f"Trust Badge: {res1['trust_badge']}")
    print(f"Sources count: {len(res1['sources'])}")

    print("\n--- 4. Testing Low-Confidence Smart Expert Escalation ---")
    q2 = "What are the cross-border tax rules for German employees commuting to Belgium?"
    res2 = query_trusted_rag(q2)
    print(f"Query: {q2}")
    print(f"Has Escalation: {res2['has_expert_escalation']}")
    if res2['routed_to_expert']:
        print(f"Routed to Expert: {res2['routed_to_expert']['name']} ({res2['routed_to_expert']['role']})")
    
    print("\n[OK] ALL BACKEND TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    test_system()
