"""Local semantic retrieval without an external embedding provider.

Computes deterministic sparse TF-IDF vectors from repository text and stores
them in SQLite with an in-memory inverted index. This is a lexical-semantic
supplement to exact/FTS search — not a neural embedding — and is local-first.
A future neural model can be swapped in behind the same ``search`` interface.
"""
from __future__ import annotations

import math
import re
import sqlite3
from array import array
from collections import Counter, defaultdict
from pathlib import Path

from intel_core import INDEX_DIR, candidate_files, rel, sha256

DB_PATH = INDEX_DIR / "semantic.sqlite"
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]{2,}")
SCHEMA_VERSION = 2
_CACHE: dict = {}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def build() -> Path:
    _CACHE.clear()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("CREATE TABLE terms(term TEXT PRIMARY KEY, idf REAL)")
    conn.execute(
        "CREATE TABLE vectors(path TEXT PRIMARY KEY, indices BLOB, weights BLOB, "
        "tokens INTEGER, sha256 TEXT)"
    )

    docs: dict[str, list[str]] = {}
    hashes: dict[str, str] = {}
    for path in candidate_files():
        rpath = rel(path)
        docs[rpath] = tokenize(path.read_text(encoding="utf-8", errors="replace"))
        hashes[rpath] = sha256(path)

    total = len(docs)
    df: Counter[str] = Counter()
    for tokens in docs.values():
        df.update(set(tokens))
    idf = {term: math.log((1 + total) / (1 + count)) + 1.0 for term, count in df.items()}
    terms = sorted(idf)
    term_index = {term: i for i, term in enumerate(terms)}

    conn.executemany("INSERT INTO terms VALUES (?, ?)", idf.items())
    for path, tokens in docs.items():
        tf = Counter(tokens)
        weights = {
            term_index[term]: (1 + math.log(count)) * idf[term]
            for term, count in tf.items() if term in term_index
        }
        norm = math.sqrt(sum(value * value for value in weights.values())) or 1.0
        indices = array("I", sorted(weights))
        values = array("f", [weights[i] / norm for i in indices])
        conn.execute(
            "INSERT INTO vectors VALUES (?, ?, ?, ?, ?)",
            (path, indices.tobytes(), values.tobytes(), len(tokens), hashes[path]),
        )
    conn.execute("INSERT INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
    conn.commit()
    conn.close()
    return DB_PATH


def _load_cache() -> None:
    conn = sqlite3.connect(DB_PATH)
    terms = [row[0] for row in conn.execute("SELECT term FROM terms ORDER BY term")]
    idf_rows = dict(conn.execute("SELECT term, idf FROM terms"))
    vectors: list[tuple[str, dict[int, float]]] = []
    for path, iblob, wblob in conn.execute("SELECT path, indices, weights FROM vectors"):
        indices = array("I")
        indices.frombytes(iblob)
        weights = array("f")
        weights.frombytes(wblob)
        vectors.append((path, dict(zip(indices, weights))))
    conn.close()
    inverted: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for doc_index, (_, vector) in enumerate(vectors):
        for term_index, weight in vector.items():
            inverted[term_index].append((doc_index, weight))
    _CACHE.update({
        "terms": terms,
        "idf": idf_rows,
        "index": {term: i for i, term in enumerate(terms)},
        "vectors": vectors,
        "inverted": inverted,
    })


def search(query: str, limit: int = 10) -> list[dict]:
    if not DB_PATH.is_file():
        build()
    if "terms" not in _CACHE:
        _load_cache()

    query_weights: dict[int, float] = defaultdict(float)
    for token in tokenize(query):
        position = _CACHE["index"].get(token)
        if position is not None:
            query_weights[position] += _CACHE["idf"][token]
    norm = math.sqrt(sum(value * value for value in query_weights.values())) or 1.0
    query_weights = {i: value / norm for i, value in query_weights.items()}

    scores: dict[int, float] = defaultdict(float)
    for position, weight in query_weights.items():
        for doc_index, doc_weight in _CACHE["inverted"].get(position, ()):
            scores[doc_index] += weight * doc_weight

    results = [
        {
            "path": _CACHE["vectors"][doc_index][0],
            "line": 0,
            "source": "semantic",
            "score": round(1.0 + score * 3.0, 4),
            "text": f"cosine={score:.3f}",
        }
        for doc_index, score in scores.items() if score > 0.08
    ]
    return sorted(results, key=lambda r: -r["score"])[:limit]


def schema_version() -> int:
    if not DB_PATH.is_file():
        return 0
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()
