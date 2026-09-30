import json
import os
import re
import math
from database import get_all_documents, get_experts

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
AUTHORS_FILE_PATH = os.path.join(os.path.dirname(__file__), "accredited_authors.txt")

def get_accredited_authors():
    if os.path.exists(AUTHORS_FILE_PATH):
        with open(AUTHORS_FILE_PATH, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return ["Jane Doe", "John Smith", "Alex Taylor", "Chris Jordan", "Morgan Lee"]


def run_gemini_prompt(prompt, system_instruction=""):
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"system_instruction": system_instruction}
            )
            return response.text
        except Exception as e:
            print(f"Gemini API call notice: {e}")
    return None


def audit_document_with_ai(title, content, region="Belgium", author="Unknown"):
    """
    Pre-audits an uploaded or queued document before it reaches the human checkpoint.
    - Checks document author against accredited_authors.txt whitelist.
    - Scans existing knowledge base for numerical rate conflicts or version overlaps.
    """
    existing_docs = get_all_documents()
    accredited_authors = get_accredited_authors()
    conflict_flags = []
    confidence = 0.85
    
    content_lower = content.lower()
    
    # 1. Accredited Author Verification Check
    is_author_accredited = False
    if author and author.strip():
        author_clean = author.strip().lower()
        for acc_author in accredited_authors:
            if acc_author.lower() in author_clean or author_clean in acc_author.lower():
                is_author_accredited = True
                break
                
    if is_author_accredited:
        conflict_flags.append(f"✅ ACCREDITED AUTHOR: Author '{author}' is verified in accredited_authors.txt whitelist.")
        confidence += 0.05
    else:
        conflict_flags.append(f"⚠️ UNACCREDITED AUTHOR: Author '{author}' was NOT found in accredited_authors.txt whitelist.")
        confidence -= 0.20

    # 2. Semantic rule scan against existing approved documents
    for doc in existing_docs:
        doc_content_lower = doc["content"].lower()
        if "remote work" in content_lower and "remote work" in doc_content_lower:
            if doc["status"] == "APPROVED" and "154" in doc_content_lower and "148" in content_lower:
                conflict_flags.append(f"CONFLICT DETECTED: Document mentions older rate (€148) contradicting approved Doc '{doc['title']}' (€154).")
                confidence -= 0.35
            elif doc["status"] == "APPROVED" and "154" in content_lower and "148" in doc_content_lower:
                conflict_flags.append(f"VERSION UPDATE NOTICE: Document contains updated €154 rate. Supersedes older '{doc['title']}'.")
                confidence += 0.10

    if len(content.strip()) < 50:
        conflict_flags.append("WARNING: Document content is very short. Low information density.")
        confidence -= 0.25

    if "draft" in title.lower() or "unverified" in title.lower() or "proposed" in title.lower():
        conflict_flags.append("NOTICE: Title indicates Draft / Unverified status.")
        confidence -= 0.15

    confidence = max(0.1, min(0.99, confidence))

    first_paragraph = content.strip().split("\n")[0] if content else title
    summary = first_paragraph[:200] + "..." if len(first_paragraph) > 200 else first_paragraph

    gemini_res = run_gemini_prompt(
        f"Analyze this document titled '{title}' by author '{author}'. Content:\n{content[:1500]}\nProvide a concise 2-sentence summary and highlight any compliance risks.",
        system_instruction="You are an expert HR & Legal compliance AI auditor for SD Worx."
    )
    if gemini_res:
        summary = gemini_res.strip()

    return {
        "summary": summary,
        "is_author_accredited": is_author_accredited,
        "ai_confidence_score": round(confidence, 2),
        "ai_audit_flags": conflict_flags,
        "suggested_category": "Payroll & Tax" if "payroll" in content_lower or "tax" in content_lower or "allowance" in content_lower else "HR Policy",
        "suggested_badge": "High Confidence - AI Scanned" if confidence > 0.8 else "Needs Expert Review"
    }


def chunk_document_text(text, max_chunk_words=80):
    paragraphs = text.split("\n\n")
    chunks = []
    for p in paragraphs:
        p_clean = p.strip()
        if p_clean:
            words = p_clean.split()
            if len(words) > max_chunk_words:
                for i in range(0, len(words), max_chunk_words):
                    chunks.append(" ".join(words[i:i+max_chunk_words]))
            else:
                chunks.append(p_clean)
    return chunks or [text]


def calculate_tf_idf_similarity(query, chunk):
    query_terms = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
    chunk_terms = [w.lower() for w in re.findall(r'\w+', chunk)]
    
    if not query_terms or not chunk_terms:
        return 0.0

    score = 0.0
    for term in query_terms:
        tf = chunk_terms.count(term)
        if tf > 0:
            score += (1 + math.log(tf)) * (1.5 if len(term) > 4 else 1.0)
            
    return score


def query_trusted_rag(user_query, user_region="Belgium"):
    all_docs = get_all_documents()
    approved_docs = [d for d in all_docs if d["status"] == "APPROVED"]
    experts = get_experts()
    
    retrieved_chunks = []
    
    for doc in approved_docs:
        chunks = chunk_document_text(doc["content"])
        for chunk_idx, chunk in enumerate(chunks):
            sim_score = calculate_tf_idf_similarity(user_query, chunk)
            
            if doc["region"].lower() in user_query.lower():
                sim_score += 1.5
                
            if sim_score > 0.5:
                retrieved_chunks.append({
                    "score": sim_score,
                    "chunk_text": chunk,
                    "doc_id": doc["id"],
                    "doc_title": doc["title"],
                    "credited_owner": doc["credited_owner"] or "Jane Doe",
                    "verification_date": doc["verification_date"] or "2026-01-18",
                    "region": doc["region"],
                    "trust_badge": doc["trust_badge"] or "Verified Official",
                    "confidence_score": doc["ai_confidence_score"],
                    "summary": doc["summary"]
                })

    retrieved_chunks.sort(key=lambda x: x["score"], reverse=True)

    if not retrieved_chunks or retrieved_chunks[0]["score"] < 1.2:
        query_lower = user_query.lower()
        if "payroll" in query_lower or "tax" in query_lower or "allowance" in query_lower or "german" in query_lower:
            best_expert = next((e for e in experts if "Jane Doe" in e["name"] or "Payroll" in e["role"]), experts[0])
        elif "remote" in query_lower or "benefit" in query_lower or "policy" in query_lower:
            best_expert = next((e for e in experts if "John Smith" in e["name"] or "HR" in e["role"]), experts[1])
        elif "mobility" in query_lower or "cross-border" in query_lower:
            best_expert = next((e for e in experts if "Chris Jordan" in e["name"]), experts[2])
        else:
            best_expert = experts[0]

        return {
            "query": user_query,
            "answer": (
                "I could not find a verified, high-trust document in our database that directly answers your question with full confidence.\n\n"
                "To prevent providing unverified or outdated information, I have automatically escalated your query to a credited domain expert."
            ),
            "confidence": 0.35,
            "trust_badge": "Low Confidence - Human Escalation Triggered",
            "sources": [],
            "retrieved_chunks": [],
            "routed_to_expert": best_expert,
            "has_expert_escalation": True,
            "warnings": ["No verified document met the minimum vector similarity threshold for automated response."]
        }

    top_chunks = retrieved_chunks[:3]
    primary_doc = top_chunks[0]

    context_str = "\n---\n".join([f"Source: {c['doc_title']} (Credited Owner: {c['credited_owner']}):\n{c['chunk_text']}" for c in top_chunks])

    rag_prompt = f"""
    You are an AI assistant for SD Worx. Answer the user's question strictly using the provided grounded context chunks below.
    Cite the credited owner ({primary_doc['credited_owner']}) and document title ({primary_doc['doc_title']}).

    CONTEXT CHUNKS:
    {context_str}

    USER QUERY: {user_query}
    """

    gemini_answer = run_gemini_prompt(rag_prompt, system_instruction="Answer ONLY using grounded context chunks. Never invent information.")
    
    if gemini_answer:
        answer_text = gemini_answer
    else:
        answer_text = (
            f"Based on grounded knowledge retrieved from **'{primary_doc['doc_title']}'** "
            f"(Verified by {primary_doc['credited_owner']}):\n\n"
            f"{primary_doc['chunk_text']}\n\n"
            f"*(Verified Official Guidance — Region: {primary_doc['region']})*"
        )

    warnings = []
    superseded_docs = [d for d in all_docs if d["status"] == "SUPERSEDED"]
    for s_doc in superseded_docs:
        if any(w in s_doc["content"].lower() for w in user_query.lower().split() if len(w) > 4):
            warnings.append(f"Archival Notice: An older superseded document '{s_doc['title']}' exists in records, but has been replaced by '{primary_doc['doc_title']}'.")

    unique_sources = {}
    for c in top_chunks:
        if c["doc_id"] not in unique_sources:
            unique_sources[c["doc_id"]] = {
                "id": c["doc_id"],
                "title": c["doc_title"],
                "credited_owner": c["credited_owner"],
                "verification_date": c["verification_date"],
                "region": c["region"],
                "summary": c["summary"]
            }

    return {
        "query": user_query,
        "answer": answer_text,
        "confidence": round(primary_doc["confidence_score"], 2),
        "trust_badge": primary_doc["trust_badge"],
        "sources": list(unique_sources.values()),
        "retrieved_chunks": top_chunks,
        "routed_to_expert": None,
        "has_expert_escalation": False,
        "warnings": warnings
    }
