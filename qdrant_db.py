"""
qdrant_db.py  –  Vector Database Layer
Uses Qdrant Cloud (europe-west3 GCP) with local disk fallback.
"""

import hashlib
import os
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    PayloadSchemaType,
)
from sentence_transformers import SentenceTransformer
from config import QDRANT_URL, QDRANT_API_KEY

# ── Connection mode tracker ───────────────────────────────────────────────────
_connection_mode = "disk"

def _make_client():
    global _connection_mode

    # 1. Try Qdrant Cloud
    if QDRANT_URL and QDRANT_URL.strip() and "localhost" not in QDRANT_URL:
        try:
            url = QDRANT_URL.rstrip("/")
            c = QdrantClient(
                url=url,
                api_key=QDRANT_API_KEY,
                timeout=30,
                prefer_grpc=False,
            )
            c.get_collections()
            _connection_mode = "cloud"
            print("[qdrant] ✅ Connected to Qdrant Cloud.")
            return c
        except Exception as e:
            print(f"[qdrant] ⚠️  Cloud failed: {e}")

    # 2. Local disk fallback
    try:
        storage_path = "./qdrant_storage"
        os.makedirs(storage_path, exist_ok=True)
        c = QdrantClient(path=storage_path)
        _connection_mode = "disk"
        print(f"[qdrant] 💾 Using local disk storage: {storage_path}")
        return c
    except Exception as e:
        print(f"[qdrant] ⚠️  Disk storage failed: {e}")

    # 3. In-memory last resort
    _connection_mode = "memory"
    print("[qdrant] ⚠️  Using in-memory mode.")
    return QdrantClient(":memory:")


def get_connection_mode() -> str:
    return _connection_mode


_client = _make_client()
_model  = SentenceTransformer("all-MiniLM-L6-v2")

COLLECTION  = "jobs"
VECTOR_SIZE = 384   # all-MiniLM-L6-v2 outputs 384-dim vectors


# ── Collection management ─────────────────────────────────────────────────────

def init_collection(force_recreate: bool = False) -> None:
    try:
        existing = [c.name for c in _client.get_collections().collections]
    except Exception:
        existing = []

    if COLLECTION in existing and not force_recreate:
        count = collection_count()
        print(f"[qdrant] Collection '{COLLECTION}' exists — {count} jobs stored.")
        return

    if COLLECTION in existing and force_recreate:
        _client.delete_collection(COLLECTION)
        print(f"[qdrant] Collection '{COLLECTION}' deleted for recreation.")

    # Create collection with cosine similarity
    _client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        ),
    )

    # Create payload index for faster filtering
    try:
        _client.create_payload_index(
            collection_name=COLLECTION,
            field_name="post_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        _client.create_payload_index(
            collection_name=COLLECTION,
            field_name="role",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        _client.create_payload_index(
            collection_name=COLLECTION,
            field_name="keyword_matched",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        print(f"[qdrant] Index creation warning: {e}")

    print(f"[qdrant] ✅ Collection '{COLLECTION}' created with indexes.")


def _ensure_collection():
    try:
        existing = [c.name for c in _client.get_collections().collections]
        if COLLECTION not in existing:
            init_collection()
    except Exception as e:
        print(f"[qdrant] _ensure_collection error: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _skills_to_vector(skills: list) -> list:
    text = " ".join(s for s in skills if s and s != "Not specified")
    return _model.encode(text if text else "general").tolist()


def _post_id_to_int(post_id: str) -> int:
    return int(hashlib.md5(post_id.encode()).hexdigest(), 16) % (10**15)


# ── Core operations ───────────────────────────────────────────────────────────

def is_duplicate(post_id: str) -> bool:
    _ensure_collection()
    try:
        records, _ = _client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(
                    key="post_id",
                    match=MatchValue(value=post_id)
                )]
            ),
            limit=1,
        )
        return len(records) > 0
    except Exception as e:
        print(f"[qdrant] is_duplicate error: {e}")
        return False


def store_job(job: dict) -> None:
    _ensure_collection()
    try:
        vector   = _skills_to_vector(job.get("primary_skills", []))
        point_id = _post_id_to_int(job["post_id"])
        _client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(
                id=point_id,
                vector=vector,
                payload=job
            )],
        )
    except Exception as e:
        print(f"[qdrant] store_job error: {e}")


def search_jobs(user_skills: list, top_k: int = 5) -> list:
    _ensure_collection()
    try:
        count = collection_count()
        if count == 0:
            print("[qdrant] No jobs stored yet.")
            return []
        vector = _skills_to_vector(user_skills)
        results = _client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=min(top_k, count),
            with_payload=True,
        )
        return results
    except Exception as e:
        print(f"[qdrant] search_jobs error: {e}")
        return []


def get_all_jobs(limit: int = 200) -> list:
    _ensure_collection()
    try:
        records, _ = _client.scroll(
            collection_name=COLLECTION,
            limit=limit,
            with_payload=True,
        )
        return [r.payload for r in records]
    except Exception as e:
        print(f"[qdrant] get_all_jobs error: {e}")
        return []


def collection_count() -> int:
    try:
        info = _client.get_collection(COLLECTION)
        return info.points_count or 0
    except Exception:
        return 0


# ── smoke-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_collection()
    dummy = {
        "post_id":        "test_001",
        "role":           "ML Engineer",
        "primary_skills": ["Python", "TensorFlow"],
        "company_name":   "Google",
        "location":       "Bangalore",
        "keyword_matched": "ML Engineer",
        "date_processed": "2025-03-31",
    }
    print("Duplicate before:", is_duplicate("test_001"))
    store_job(dummy)
    print("Duplicate after:", is_duplicate("test_001"))
    hits = search_jobs(["Python", "TensorFlow"])
    print(f"Search results: {len(hits)}")
    print(f"Connection mode: {get_connection_mode()}")