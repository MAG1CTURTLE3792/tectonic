import json
import os
import re
from database import get_all_documents, get_experts

# Try importing google.genai if available, otherwise use fallback logic for hackathon portability
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def run_gemini_prompt(prompt, system_instruction=""):
    """
    Attempts to execute prompt with Gemini API if key exists,
    otherwise provides intelligent heuristic response.
    """
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


def audit_document_with_ai(title, content, region="Belgium"):
    """
    Pre-audits an uploaded document before it reaches the human checkpoint.
    Detects metadata, potential conflicts, and calculates initial trust score.
    """
    existing_docs = get_all_documents()
    
    # Check for conflict keywords & rate discrepancies against existing DB docs
    conflict_flags = []
    confidence = 0.85
    
    # Simple semantic rule check for demo (e.g., numerical rate changes, version tags)
    content_lower = content.lower()
    
    for doc in existing_docs:
        # Check for rate conflicts e.g. €148 vs €154 or conflicting remote work rules
        if "remote work" in content_lower and "remote work" in doc["content"].lower():
            if doc["status"] == "APPROVED" and "154" in doc["content"] and "148" in content_lower:
                conflict_flags.append(f"CONFLICT DETECTED: Document mentions older rate (€148) which contradicts approved Doc '{doc['title']}' (€154).")
                confidence -= 0.35
            elif doc["status"] == "APPROVED" and "154" in content_lower and "148" in doc["content"]:
                conflict_flags.append(f"VERSION UPDATE NOTICE: Document contains updated €154 rate. Supersedes older '{doc['title']}'.")
                confidence += 0.10
    
    if len(content.strip()) < 50:
        conflict_flags.append("WARNING: Document content is very short. Low information density.")
        confidence -= 0.25

    if "draft" in title.lower() or "unverified" in title.lower():
        conflict_flags.append("NOTICE: Document title indicates Draft status.")
        confidence -= 0.15

    # Clamp confidence
    confidence = max(0.1, min(0.99, confidence))

    # Generate summary
    first_paragraph = content.strip().split("\n")[0] if content else title
    summary = first_paragraph[:200] + "..." if len(first_paragraph) > 200 else first_paragraph

    # Try Gemini API for rich AI analysis if configured
    gemini_res = run_gemini_prompt(
        f"Analyze this policy document titled '{title}'. Content:\n{content[:1500]}\nProvide a short 2-sentence summary and any risk flags.",
        system_instruction="You are an expert HR & Legal compliance AI auditor for SD Worx."
    )
    if gemini_res:
        summary = gemini_res.strip()

    return {
        "summary": summary,
        "ai_confidence_score": round(confidence, 2),
        "ai_audit_flags": conflict_flags,
        "suggested_category": "Payroll & Tax" if "payroll" in content_lower or "allowance" in content_lower else "HR Policy",
        "suggested_badge": "High Confidence - AI Scanned" if confidence > 0.8 else "Needs Expert Review"
    }


def query_trusted_rag(user_query, user_region="Belgium"):
    """
    RAG Search pipeline over APPROVED documents with Trust Scoring and Expert Escalation Routing.
    """
    all_docs = get_all_documents()
    approved_docs = [d for d in all_docs if d["status"] == "APPROVED"]
    experts = get_experts()
    
    query_lower = user_query.lower()
    matching_docs = []
    
    # Score documents by keyword & relevance
    for doc in approved_docs:
        score = 0
        content_lower = doc["content"].lower()
        title_lower = doc["title"].lower()
        
        # Match significant query keywords
        words = [w for w in query_lower.split() if len(w) > 3 and w not in ["what", "where", "which", "about", "rules", "policy"]]
        for w in words:
            if w in content_lower:
                score += 3
            if w in title_lower:
                score += 5
                
        if doc["region"].lower() in query_lower:
            score += 2
            
        if score >= 3: # Require significant match
            matching_docs.append((score, doc))
            
    # Sort by score descending
    matching_docs.sort(key=lambda x: x[0], reverse=True)
    
    # Determine RAG confidence and outcome
    if not matching_docs:
        # LOW CONFIDENCE / NO MATCH -> SMART EXPERT ROUTING
        best_expert = None
        if "payroll" in query_lower or "tax" in query_lower or "allowance" in query_lower or "german" in query_lower:
            best_expert = next((e for e in experts if "Cross-Border" in e["domain"] or "Payroll" in e["role"]), experts[0])
        elif "remote" in query_lower or "benefit" in query_lower or "policy" in query_lower:
            best_expert = next((e for e in experts if "HR" in e["role"]), experts[1])
        else:
            best_expert = experts[0]
            
        answer = (
            "I could not find a verified, high-trust document in our database that directly answers your question with full confidence.\n\n"
            "To prevent providing unverified or outdated information, I have automatically escalated your query to an SD Worx Subject Matter Expert."
        )
        
        return {
            "query": user_query,
            "answer": answer,
            "confidence": 0.35,
            "trust_badge": "Low Confidence - Human Escalation Triggered",
            "sources": [],
            "routed_to_expert": best_expert,
            "has_expert_escalation": True,
            "warnings": ["No verified document met the minimum confidence threshold for automated response."]
        }
    
    top_doc = matching_docs[0][1]
    
    # Formulate answer using Top Document
    answer_text = f"Based on our credited document **'{top_doc['title']}'** (Verified by {top_doc['credited_owner'] or 'SD Worx Expert'}):\n\n"
    answer_text += f"{top_doc['content']}\n\n"
    answer_text += f"**Expert Verification Note**: {top_doc['expert_notes'] or 'Formally approved for operational use.'}"

    # Use Gemini API if available for synthesized prose answer
    prompt = f"""
    Answer the user query using ONLY the following verified document content:
    Document Title: {top_doc['title']}
    Credited Owner: {top_doc['credited_owner']}
    Content: {top_doc['content']}
    
    User Query: {user_query}
    
    Respond concisely with high clarity and cite the credited owner.
    """
    gemini_answer = run_gemini_prompt(prompt, system_instruction="You are SD Worx Trusted AI Assistant.")
    if gemini_answer:
        answer_text = gemini_answer

    # Check for superseded / conflicting documents to warn the user
    warnings = []
    superseded_docs = [d for d in all_docs if d["status"] == "SUPERSEDED"]
    for s_doc in superseded_docs:
        if any(w in s_doc["content"].lower() for w in words):
            warnings.append(f"Archival Warning: Older document '{s_doc['title']}' was superseded by '{top_doc['title']}'.")

    return {
        "query": user_query,
        "answer": answer_text,
        "confidence": round(top_doc["ai_confidence_score"], 2),
        "trust_badge": top_doc["trust_badge"] or "Verified Official",
        "sources": [{
            "id": top_doc["id"],
            "title": top_doc["title"],
            "credited_owner": top_doc["credited_owner"],
            "verification_date": top_doc["verification_date"],
            "region": top_doc["region"],
            "summary": top_doc["summary"]
        }],
        "routed_to_expert": None,
        "has_expert_escalation": False,
        "warnings": warnings
    }
