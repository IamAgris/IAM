#!/usr/bin/env python3
"""Lazy local neural re-ranking with a persistent per-file vector cache.

Only the shortlist from exact/FTS/TF-IDF retrieval is embedded, and vectors are
cached by file hash. If the local Ollama model is unavailable, callers fall
back to deterministic lexical retrieval unchanged.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import time
from array import array
from pathlib import Path

from embeddings import EmbeddingUnavailable, config, embed, is_available
from intel_core import INDEX_DIR, ROOT, sha256

DB_PATH = INDEX_DIR / "neural-cache.sqlite"
MAX_CHARS = 400
BATCH_SIZE = 5
MAX_CANDIDATES = 5


def status() -> dict:
    settings = config()
    available = is_available()
    vectors = 0
    if DB_PATH.is_file():
        conn = sqlite3.connect(DB_PATH)
        try:
            vectors = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
    return {"config": settings, "available": available, "cached_vectors": vectors}


def _embed_batch(texts: list[str]) -> list[list[float]]:
    import urllib.request

    settings = config()
    url = settings["base_url"].rstrip("/") + "/api/embed"
    body = json.dumps({
        "model": settings.get("model", "nomic-embed-text"),
        "input": texts,
    }).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return [[float(v) for v in vector] for vector in payload["embeddings"]]
        except Exception as exc:  # retry transient Ollama connection resets
            last_error = exc
            time.sleep(1 + attempt)
    raise EmbeddingUnavailable(str(last_error))


def _vectors(paths: list[str]) -> dict[str, list[float]]:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS vectors(path TEXT PRIMARY KEY, sha256 TEXT, vector BLOB)")
    conn.commit()
    cached: dict[str, list[float]] = {}
    missing: list[str] = []
    for path in paths:
        full = ROOT / path
        if not full.is_file():
            continue
        digest = sha256(full)
        row = conn.execute("SELECT vector FROM vectors WHERE path=? AND sha256=?", (path, digest)).fetchone()
        if row:
            vector = array("f")
            vector.frombytes(row[0])
            cached[path] = list(vector)
        else:
            missing.append(path)
    for start in range(0, len(missing), BATCH_SIZE):
        batch = missing[start:start + BATCH_SIZE]
        texts = [(ROOT / p).read_text(encoding="utf-8", errors="replace")[:MAX_CHARS] for p in batch]
        try:
            vectors = _embed_batch(texts)
        except EmbeddingUnavailable:
            break
        for path, vector in zip(batch, vectors):
            cached[path] = vector
            conn.execute(
                "INSERT OR REPLACE INTO vectors VALUES (?, ?, ?)",
                (path, sha256(ROOT / path), array("f", vector).tobytes()),
            )
    conn.commit()
    conn.close()
    return cached


def rerank(query: str, candidates: list[dict], limit: int = 10) -> list[dict]:
    """Re-rank a shortlist by cosine similarity to a local neural query vector."""
    if not is_available() or not candidates:
        return []
    # Exact identifiers and filenames keep their precedence over neural ranks.
    eligible = [c for c in candidates if c.get("source") not in ("symbol", "filename")]
    paths = list(dict.fromkeys(c["path"] for c in eligible[:MAX_CANDIDATES]))
    vectors = _vectors(paths)
    if not vectors:
        return []
    try:
        query_vector = embed(query)
    except EmbeddingUnavailable:
        return []
    qnorm = math.sqrt(sum(v * v for v in query_vector)) or 1.0
    scored = []
    for path, vector in vectors.items():
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        score = sum(a * b for a, b in zip(query_vector, vector)) / (qnorm * norm)
        scored.append((path, score))
    ranked = {path: score for path, score in sorted(scored, key=lambda item: -item[1])}
    results = []
    for candidate in candidates:
        score = ranked.get(candidate["path"])
        if score is None or score < 0.30:
            continue
        item = dict(candidate)
        item["neural_cosine"] = round(score, 4)
        item["score"] = round(9.0 + score + candidate.get("score", 0) / 100.0, 4)
        item["source"] = "neural_rerank"
        results.append(item)
        if len(results) >= limit:
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = status()
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
