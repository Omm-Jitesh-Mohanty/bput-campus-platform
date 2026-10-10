"""
RAG query engine — uses FAISS retriever with re-ranking.
"""
import logging

from ai_engine.rag.retriever import retrieve
from ai_engine.llm import generate_text

logger = logging.getLogger(__name__)


STUDENT_SYSTEM = """You are a warm, concise campus assistant for engineering
college students in India.

Answer the student's question using ONLY the provided context from official
campus policies and past resolutions.

Rules:
- If the answer is in the context, answer clearly and cite the policy name.
- If not in context, say: "I don't have that information. Please contact the 
  concerned office."
- Keep responses under 120 words.
- Be friendly but professional.
- Do NOT invent policies, dates, or procedures.
"""

ADMIN_SYSTEM = """You are an assistant for college administrators.

Answer using the provided context from past tickets, policies, and config.

Rules:
- Be specific. Cite numbers (SLA hours, ticket IDs, department codes).
- If the answer isn't in context, say so clearly.
- Keep responses under 150 words.
"""


def answer(query, audience='student', user=None, conversation_history=None):
    """
    Full RAG pipeline:
      1. Retrieve top-5 chunks (audience-filtered, re-ranked)
      2. Build a context prompt
      3. Call the LLM
      4. Return answer + sources
    """
    # 1. Retrieve
    chunks = retrieve(query, audience=audience, top_k=5, candidate_k=20)

    if not chunks:
        return {
            'answer': (
                "I couldn't find relevant information in the campus knowledge base. "
                "Try rephrasing or contact the concerned office directly."
            ),
            'sources': [],
            'chunks_used': 0,
            'source': 'no_context',
        }

    # 2. Build prompt
    context_lines = []
    for i, c in enumerate(chunks, 1):
        src = c['metadata'].get('source', '')
        title = c['metadata'].get('title', '')
        context_lines.append(
            f"[{i}] ({src}) {title}\n{c['text']}"
        )
    context = '\n\n---\n\n'.join(context_lines)

    history = ''
    if conversation_history:
        recent = conversation_history[-4:]
        history = '\n\nRecent conversation:\n' + '\n'.join(
            f"{m['role']}: {m['content'][:200]}" for m in recent
        )

    prompt = f"""Context from official campus records:

{context}
{history}

Question: {query}

Answer:"""

    system = STUDENT_SYSTEM if audience == 'student' else ADMIN_SYSTEM

    # 3. Generate
    response = generate_text(prompt, system=system, temperature=0.3, max_tokens=350)

    sources = [
        {
            'title': c['metadata'].get('title', ''),
            'type': c['metadata'].get('source', ''),
            'score': round(c.get('rerank_score', c.get('score', 0)), 3),
            'doc_name': c['metadata'].get('doc_name', ''),
        }
        for c in chunks
    ]

    if response.success and response.text:
        return {
            'answer': response.text.strip(),
            'sources': sources,
            'chunks_used': len(chunks),
            'source': 'llm',
            'latency_ms': response.latency_ms,
        }

    # Fallback: return the top chunk verbatim
    top = chunks[0]
    return {
        'answer': f"Based on our records:\n\n{top['text'][:400]}",
        'sources': sources,
        'chunks_used': len(chunks),
        'source': 'fallback_retrieval',
    }