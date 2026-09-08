#!/usr/bin/env python3
"""
scripts/ingest.py

Ingest Egyptian legal articles into Qdrant.

Expected JSONL format (one JSON object per line):
{
  "chunk_id": "labor_12_2003_art10",
  "doc_id": "labor_12_2003",
  "law_name": "قانون العمل",
  "law_number": "12",
  "law_year": "2003",
  "law_type": "labor_law",
  "category": "labor_law",
  "article_number": "10",
  "text": "نص المادة...",
  "context_text": "نص السياق...",
  "cross_references": ["labor_12_2003_art9"]
}

Usage:
  python scripts/ingest.py --input data/legal_corpus.jsonl \\
      --qdrant-url http://localhost:6333 \\
      --collection egyptian_legal_articles \\
      --batch-size 32
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging("INFO")
logger = get_logger("bayyinah.ingest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest legal corpus into Qdrant")
    parser.add_argument("--input", required=True, help="Path to JSONL corpus file")
    parser.add_argument("--qdrant-url", default=None)
    parser.add_argument("--qdrant-api-key", default=None)
    parser.add_argument("--collection", default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate collection if exists")
    return parser.parse_args()


def load_corpus(path: str) -> list[dict[str, Any]]:
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning(f"Skipping malformed line {i}: {exc}")
    logger.info(f"Loaded {len(records)} records from {path}")
    return records


def ensure_collection(client, collection: str, dim: int, recreate: bool) -> None:
    from qdrant_client.http import models as qmodels

    existing = {c.name for c in client.get_collections().collections}
    if collection in existing:
        if recreate:
            logger.info(f"Deleting existing collection '{collection}'")
            client.delete_collection(collection)
        else:
            logger.info(f"Collection '{collection}' already exists — skipping creation")
            return

    logger.info(f"Creating collection '{collection}' dim={dim} with named vector 'dense' ...")
    client.create_collection(
        collection_name=collection,
        vectors_config={"dense": qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE)},
    )

    # Payload indexes for metadata filtering
    for field in ("category", "law_type", "law_name", "law_year"):
        client.create_payload_index(
            collection_name=collection,
            field_name=field,
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )
    logger.info("Collection and indexes created")


def ingest_batch(client, collection: str, records: list[dict], embedder, batch_size: int) -> None:
    from qdrant_client.http import models as qmodels

    total = len(records)
    logger.info(f"Ingesting {total} records in batches of {batch_size}")

    for start in range(0, total, batch_size):
        batch = records[start : start + batch_size]
        texts = [r.get("text", "") for r in batch]

        t0 = time.perf_counter()
        vectors = embedder.embed_batch(texts)
        embed_ms = (time.perf_counter() - t0) * 1000

        points = [
            qmodels.PointStruct(
                id=abs(hash(r.get("chunk_id", str(i + start)))) % (2**63),
                vector={"dense": vectors[i]},
                payload={
                    "chunk_id": r.get("chunk_id"),
                    "doc_id": r.get("doc_id"),
                    "law_name": r.get("law_name"),
                    "law_number": r.get("law_number"),
                    "law_year": r.get("law_year"),
                    "law_type": r.get("law_type"),
                    "category": r.get("category"),
                    "article_number": r.get("article_number"),
                    "text": r.get("text"),
                    "context_text": r.get("context_text"),
                    "cross_references": r.get("cross_references", []),
                },
            )
            for i, r in enumerate(batch)
        ]

        client.upsert(collection_name=collection, points=points)
        end = start + len(batch)
        logger.info(f"Upserted {end}/{total} — embed {embed_ms:.0f}ms")

    logger.info("Ingestion complete")


def main() -> None:
    args = parse_args()
    settings = get_settings()

    qdrant_url = args.qdrant_url or settings.QDRANT_URL
    qdrant_api_key = args.qdrant_api_key or settings.QDRANT_API_KEY
    collection = args.collection or settings.QDRANT_COLLECTION

    logger.info(f"Qdrant: {qdrant_url}  collection: {collection}")

    from qdrant_client import QdrantClient
    from app.services.embedding_service import EmbeddingService

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    embedder = EmbeddingService(model_name=settings.EMBEDDING_MODEL, device=settings.EMBEDDING_DEVICE)

    # Warm up model
    logger.info("Warming up embedding model...")
    embedder.embed_query("test")

    records = load_corpus(args.input)
    if not records:
        logger.error("No records found in corpus file")
        sys.exit(1)

    ensure_collection(client, collection, settings.EMBEDDING_DIM, args.recreate)
    ingest_batch(client, collection, records, embedder, args.batch_size)


if __name__ == "__main__":
    main()
