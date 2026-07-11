"""Chunk the synthetic policy corpus by clause and ingest into Qdrant.

Each markdown file in policies/ has a YAML front-matter block with doc-level
metadata (doc_id, plan_type, category, effective_date) followed by one
`## Clause <CLAUSE_ID>: <Title>` section per clause. Each clause becomes one
vector point with payload = {text, doc_id, source_doc, plan_type, category,
clause_id}.
"""
import hashlib
import re
import sys
from pathlib import Path

import yaml
from qdrant_client.models import Distance, PointStruct, VectorParams

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402
from app.embeddings import embed_texts  # noqa: E402
from app.vectorstore import get_qdrant_client  # noqa: E402

POLICIES_DIR = Path(__file__).resolve().parents[2] / "policies"
CLAUSE_HEADER_RE = re.compile(r"^##\s+Clause\s+([A-Z0-9_.\-]+):\s*(.+)$", re.MULTILINE)


def parse_doc(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        meta = yaml.safe_load(fm)
    else:
        meta, body = {}, raw
    return meta, body


def chunk_by_clause(body: str) -> list[dict]:
    matches = list(CLAUSE_HEADER_RE.finditer(body))
    chunks = []
    for i, m in enumerate(matches):
        clause_id = m.group(1)
        title = m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[start:end].strip()
        chunks.append({"clause_id": clause_id, "title": title, "text": text})
    return chunks


def stable_point_id(clause_id: str) -> int:
    return int(hashlib.sha1(clause_id.encode()).hexdigest()[:12], 16)


def main() -> None:
    settings = get_settings()
    client = get_qdrant_client()

    docs = sorted(POLICIES_DIR.glob("*.md"))
    if not docs:
        raise SystemExit(f"No policy documents found in {POLICIES_DIR}")

    all_points_payload = []
    all_texts = []

    for path in docs:
        meta, body = parse_doc(path)
        clauses = chunk_by_clause(body)
        for clause in clauses:
            embed_source = f"{clause['title']}. {clause['text']}"
            payload = {
                "text": clause["text"],
                "title": clause["title"],
                "clause_id": clause["clause_id"],
                "doc_id": meta.get("doc_id", path.stem),
                "source_doc": path.name,
                "plan_type": meta.get("plan_type", "All"),
                "category": meta.get("category", "general"),
                "effective_date": str(meta.get("effective_date", "")),
            }
            all_points_payload.append(payload)
            all_texts.append(embed_source)

    print(f"Parsed {len(docs)} documents -> {len(all_points_payload)} clauses.")
    print("Embedding clauses with all-MiniLM-L6-v2 (first run downloads the model)...")
    vectors = embed_texts(all_texts, fit=True)
    dim = len(vectors[0])

    if client.collection_exists(settings.qdrant_collection):
        client.delete_collection(settings.qdrant_collection)
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    points = [
        PointStruct(id=stable_point_id(payload["clause_id"]), vector=vec, payload=payload)
        for payload, vec in zip(all_points_payload, vectors)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)

    print(f"Ingested {len(points)} clauses into Qdrant collection "
          f"'{settings.qdrant_collection}'.")

    # Spot-check: run one similarity query per plan type
    sample_query = "MRI advanced imaging prior authorization requirement"
    q_vec = embed_texts([sample_query])[0]
    results = client.query_points(
        collection_name=settings.qdrant_collection, query=q_vec, limit=3
    ).points
    print(f"\nSpot-check query: '{sample_query}'")
    for r in results:
        print(f"  [{r.score:.3f}] {r.payload['clause_id']} — {r.payload['title']}")


if __name__ == "__main__":
    main()
