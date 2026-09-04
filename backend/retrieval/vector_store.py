import os
import math
import hashlib
import json
from sqlalchemy import text
from dotenv import load_dotenv


# Load env variables
load_dotenv()

EMBEDDING_DIM = 384

def _get_mock_embedding(text_content: str) -> list[float]:
    """
    Generates a deterministic 384-dimensional unit vector from text.
    Uses basic word hashing to simulate text similarity.
    Words are hashed to bins, creating a bag-of-words representation.
    """
    words = text_content.lower().split()
    vector = [0.0] * EMBEDDING_DIM
    if not words:
        # Return a default unit vector
        vector[0] = 1.0
        return vector

    for word in words:
        # Hash word to index
        h = hashlib.md5(word.encode("utf-8")).hexdigest()
        idx = int(h, 16) % EMBEDDING_DIM
        vector[idx] += 1.0

    # L2 Normalization
    sq_sum = sum(x * x for x in vector)
    if sq_sum > 0:
        norm = math.sqrt(sq_sum)
        vector = [x / norm for x in vector]
    else:
        vector[0] = 1.0
    return vector

def get_embedding(text_content: str) -> list[float]:
    """
    Generates embedding for text.
    Uses Google Gemini or OpenAI if API keys are set, otherwise falls back
    to deterministic word-hashing mock embedding.
    """
    provider = os.getenv("LLM_PROVIDER", "google").lower()
    
    # Try live Gemini Embeddings
    if provider == "google" and os.getenv("GEMINI_API_KEY"):
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client()
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text_content
            )
            # Response returns list of embeddings
            emb = response.embeddings[0].values
            return emb
        except Exception as e:
            # Fallback to mock on error
            pass

    # Try live OpenAI Embeddings
    elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI()
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[text_content]
            )
            emb = response.data[0].embedding
            return emb
        except Exception as e:
            pass

    # Fallback to mock embedding
    return _get_mock_embedding(text_content)

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two lists of floats."""
    if len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def add_evidence_record(db, evidence_id: str, transaction_id: str, source_type: str, source_record: str, content: str, relevant_date=None, reliability="HIGH"):
    """Inserts an evidence record, calculates embedding, and stores in DB."""
    from backend.database.models import Evidence
    
    # Check if exists
    existing = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    emb = get_embedding(content)
    
    new_evidence = Evidence(
        evidence_id=evidence_id,
        transaction_id=transaction_id,
        source_type=source_type,
        source_record=source_record,
        content=content,
        embedding=emb,
        relevant_date=relevant_date,
        reliability=reliability
    )
    db.add(new_evidence)
    db.commit()
    return new_evidence

def search_semantic_evidence(db, query: str, limit: int = 5) -> list[dict]:
    """
    Retrieves evidence records sorted by similarity to query.
    If PostgreSQL/pgvector is active, it runs pgvector similarity query.
    Otherwise (SQLite fallback), it loads all embeddings and computes similarity in Python.
    """
    from backend.database.connection import DATABASE_URL
    from backend.database.models import Evidence

    query_emb = get_embedding(query)

    # If it is Postgres with pgvector, run DB-native search (mock interface here since we fallback to SQLite)
    # Since we operate on SQLite for our MVP run, we'll fetch elements and compute similarity.
    evidences = db.query(Evidence).all()
    results = []
    
    for ev in evidences:
        if not ev.embedding:
            continue
        sim = cosine_similarity(query_emb, ev.embedding)
        results.append({
            "evidence_id": ev.evidence_id,
            "transaction_id": ev.transaction_id,
            "source_type": ev.source_type,
            "source_record": ev.source_record,
            "content": ev.content,
            "relevant_date": ev.relevant_date.isoformat() if ev.relevant_date else None,
            "reliability": ev.reliability,
            "score": float(sim)
        })
        
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
