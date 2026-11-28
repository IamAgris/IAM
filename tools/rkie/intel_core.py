"""Core deterministic repository intelligence primitives.

No network, no LLM, no third-party parser. Uses the Python standard library
(ast, sqlite3, difflib) and git. All functions return plain dictionaries so the
agent-facing API and CLI can share them.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import re
import sqlite3
import subprocess
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "tools" / "rkie" / "index"
CODE_INDEX_PATH = INDEX_DIR / "code-intel.json"
SEARCH_DB_PATH = INDEX_DIR / "search.sqlite"
LINKS_PATH = ROOT / "tools" / "rkie" / "config" / "architecture-links.json"

SKIP_DIRS = {
    ".git", "node_modules", ".next", ".venv", "__pycache__", ".pytest_cache",
    "dist", "build", ".mypy_cache", ".ruff_cache",
}
MAX_FILE_BYTES = 2_000_000
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".sql", ".yaml",
                 ".yml", ".toml", ".ps1", ".sh", ".json", ".ini", ".cfg", ".conf"}
SECRET_RE = re.compile(
    r"(^|/)\.env([./]|$)|(^|/)(secrets?|private)(/|$)|\.(pfx|p12|key|pem|crt|cer|keystore|jks|asc)$",
    re.I,
)


def git(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, text=True, errors="replace",
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def candidate_files(suffixes: set[str] | None = None) -> list[Path]:
    suffixes = suffixes or TEXT_SUFFIXES
    files: list[Path] = []
    for entry in git("ls-files", "--cached", "--others", "--exclude-standard"):
        rel = entry.replace("\\", "/")
        if SECRET_RE.search(rel):
            continue
        if any(part in SKIP_DIRS for part in rel.split("/")):
            continue
        if rel.startswith("tools/rkie/index/"):
            continue
        if Path(rel).suffix.lower() not in suffixes:
            continue
        path = ROOT / rel
        if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES:
            files.append(path)
    return sorted(files)


@lru_cache(maxsize=1)
def _default_candidates() -> tuple[Path, ...]:
    return tuple(candidate_files())


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_links() -> dict[str, Any]:
    if not LINKS_PATH.is_file():
        return {"mappings": [], "superseded": [], "default": {}}
    return json.loads(LINKS_PATH.read_text(encoding="utf-8"))


def specs_for(path: str) -> tuple[str, list[str], str]:
    links = load_links()
    default = links.get("default", {})
    spec = default.get("spec", "docs/IAM_FINAL_CONSOLIDATION.md")
    decisions: list[str] = list(default.get("decisions", []))
    area = default.get("area", "general")
    for mapping in links.get("mappings", []):
        if re.search(mapping["pattern"], path):
            spec = mapping["spec"]
            decisions = list(mapping.get("decisions", []))
            area = mapping.get("area", area)
            break
    superseded = any(re.search(p, path) for p in links.get("superseded", []))
    return spec, decisions, ("superseded" if superseded else area)


# ---------------------------------------------------------------------------
# AST code index
# ---------------------------------------------------------------------------

class CodeIndex:
    """Definitions, imports, calls, routes and models extracted from Python AST."""

    def __init__(self, root: Path = ROOT):
        self.root = root
        self.data: dict[str, Any] = {
            "version": 2,
            "definitions": defaultdict(list),
            "calls": defaultdict(list),
            "imports": {},
            "importers": defaultdict(list),
            "routes": [],
            "models": [],
            "files": {},
        }

    def build(self) -> dict[str, Any]:
        for path in candidate_files({".py"}):
            if not str(path).startswith(str(self.root)):
                continue
            self._parse(path)
        result = {k: (dict(v) if isinstance(v, defaultdict) else v)
                  for k, v in self.data.items()}
        return result

    def _parse(self, path: Path) -> None:
        rpath = rel(path)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rpath)
        except (SyntaxError, OSError):
            return
        spec, decisions, area = specs_for(rpath)
        self.data["files"][rpath] = {
            "sha256": sha256(path), "spec": spec, "decisions": decisions, "area": area,
        }
        prefix = ""
        imports: list[str] = []
        calls: list[str] = []
        defs: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                imports.extend(names)
                for name in names:
                    self.data["importers"][name].append(rpath)
            elif isinstance(node, ast.Assign):
                if isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("router", "APIRouter"):
                    if isinstance(node.value, ast.Call):
                        for kw in node.value.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                prefix = str(kw.value.value)
            elif isinstance(node, ast.ClassDef):
                defs.append(node.name)
                bases = [ast.unparse(b) for b in node.bases]
                self.data["definitions"][node.name].append({
                    "file": rpath, "line": node.lineno, "kind": "class", "bases": bases,
                    "spec": spec, "decisions": decisions,
                })
                if any(b.endswith("Base") or b == "Base" for b in bases):
                    self.data["models"].append({
                        "name": node.name, "file": rpath, "line": node.lineno,
                    })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.append(node.name)
                self.data["definitions"][node.name].append({
                    "file": rpath, "line": node.lineno,
                    "kind": "async def" if isinstance(node, ast.AsyncFunctionDef) else "def",
                    "decorators": [ast.unparse(d) for d in node.decorator_list],
                    "spec": spec, "decisions": decisions,
                })
                for decorator in node.decorator_list:
                    text = ast.unparse(decorator)
                    # ast.unparse on a decorator expression omits the leading '@'.
                    match = re.match(r"@?(?:router|app)\.(get|post|put|patch|delete)\((['\"])(.+?)\2", text)
                    if match:
                        self.data["routes"].append({
                            "method": match.group(1).upper(),
                            "path": prefix + match.group(3),
                            "handler": node.name,
                            "file": rpath, "line": node.lineno,
                            "spec": spec, "decisions": decisions,
                        })
            elif isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Name):
                    calls.append(target.id)
                elif isinstance(target, ast.Attribute):
                    calls.append(target.attr)
        for name in set(calls):
            self.data["calls"][name].append({"file": rpath, "count": calls.count(name)})

        self.data["imports"][rpath] = sorted(set(imports))
        self.data["files"][rpath]["definitions"] = sorted(set(defs))
        self.data["files"][rpath]["calls"] = sorted(set(calls))


def build_code_index() -> Path:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    data = CodeIndex().build()
    CODE_INDEX_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return CODE_INDEX_PATH


def load_code_index() -> dict[str, Any]:
    if not CODE_INDEX_PATH.is_file():
        return {}
    return json.loads(CODE_INDEX_PATH.read_text(encoding="utf-8"))


def symbol_report(name: str, index: dict[str, Any] | None = None) -> dict[str, Any]:
    index = index or load_code_index()
    definitions = index.get("definitions", {}).get(name, [])
    callers = index.get("calls", {}).get(name, [])
    importers = index.get("importers", {}).get(name, [])
    routes = [r for r in index.get("routes", []) if r.get("handler") == name]
    return {
        "symbol": name,
        "definitions": definitions,
        "call_sites": callers,
        "importers": importers,
        "routes": routes,
        "tests": [p for p in index.get("files", {})
                  if "/tests/" in p and any(d.get("file") == p for d in definitions)],
    }


def import_cycles(index: dict[str, Any] | None = None) -> list[list[str]]:
    index = index or load_code_index()
    graph: dict[str, set[str]] = defaultdict(set)
    for file, imports in index.get("imports", {}).items():
        for module in imports:
            for other, other_imports in index.get("imports", {}).items():
                if module and (module == Path(other).stem or other.endswith("/" + module + ".py")):
                    graph[file].add(other)
    cycles: list[list[str]] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(node: str, stack: list[str]) -> None:
        if node in visiting:
            cycle = stack[stack.index(node):] + [node]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, ()):
            walk(child, stack + [node])
        visiting.discard(node)
        visited.add(node)

    for node in sorted(graph):
        walk(node, [])
    return cycles


def dead_symbols(index: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    index = index or load_code_index()
    used = set(index.get("calls", {})) | {
        r["handler"] for r in index.get("routes", [])
    }
    result = []
    for name, defs in index.get("definitions", {}).items():
        if name.startswith("__") or name in used:
            continue
        if any("/tests/" in d.get("file", "") for d in defs):
            continue
        for definition in defs:
            result.append({"name": name, **definition})
    return result


def change_impact(files: Iterable[str], index: dict[str, Any] | None = None) -> dict[str, Any]:
    index = index or load_code_index()
    changed = sorted(set(files))
    changed_symbols = set()
    for file in changed:
        changed_symbols.update(index.get("files", {}).get(file, {}).get("definitions", []))
    affected = set(changed)
    for symbol in changed_symbols:
        for site in index.get("calls", {}).get(symbol, []):
            affected.add(site["file"])
        for importer in index.get("importers", {}).get(symbol, []):
            affected.add(importer)
    routes = [r for r in index.get("routes", []) if r.get("file") in affected]
    models = [m for m in index.get("models", []) if m.get("file") in affected]
    tests = [f for f in affected if "/tests/" in f]
    specs = sorted({r["spec"] for r in routes} | {
        index.get("files", {}).get(f, {}).get("spec", "") for f in affected
    } - {""})
    return {
        "changed": changed,
        "changed_symbols": sorted(changed_symbols),
        "affected_files": sorted(affected),
        "routes": routes,
        "models": models,
        "tests": tests,
        "specs": specs,
        "risk": "high" if routes or models else ("medium" if len(affected) > 1 else "low"),
    }


# ---------------------------------------------------------------------------
# SQLite FTS5 + hybrid ranking
# ---------------------------------------------------------------------------

class HybridSearch:
    def __init__(self, db_path: Path = SEARCH_DB_PATH):
        self.db_path = db_path

    def build(self) -> Path:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE VIRTUAL TABLE docs USING fts5(path, content, tokenize='unicode61')")
        conn.execute("CREATE TABLE meta(path UNIQUE, sha256, size)")
        count = 0
        for path in candidate_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            conn.execute("INSERT INTO docs(path, content) VALUES (?, ?)", (rel(path), text))
            conn.execute("INSERT OR REPLACE INTO meta VALUES (?, ?, ?)",
                         (rel(path), sha256(path), path.stat().st_size))
            count += 1
        conn.commit()
        conn.close()
        return self.db_path

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.db_path.is_file():
            return []
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        results: list[dict[str, Any]] = []
        try:
            for row in conn.execute(
                "SELECT path, snippet(docs, 1, '[', ']', ' ... ', 8) AS text, "
                "bm25(docs, 0.0, 1.0) AS score FROM docs WHERE docs MATCH ? "
                "ORDER BY score LIMIT ?", ('"' + query.replace('"', '""') + '"', limit),
            ):
                results.append({
                    "path": row["path"], "line": 0,
                    "text": row["text"], "score": 2.0 + max(0.0, -float(row["score"])),
                    "source": "fts5",
                })
        except sqlite3.OperationalError:
            pass
        conn.close()

        # Exact identifier matches outrank full-text matches.
        index = load_code_index()
        for definition in index.get("definitions", {}).get(query, []):
            results.insert(0, {
                "path": definition["file"], "line": definition["line"],
                "text": f"{definition['kind']} {query}", "score": 30.0,
                "source": "symbol",
            })
        # Filename matches (cached candidate set keeps repeated queries cheap).
        for path in _default_candidates():
            if query.lower() in path.name.lower():
                results.insert(0, {
                    "path": rel(path), "line": 0, "text": "[filename] " + rel(path),
                    "score": 20.0, "source": "filename",
                })
        # Fuzzy fallback: only when nothing else matched and query is a name-like token.
        if not results and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{3,}", query):
            names = list(index.get("definitions", {}))
            for name in difflib.get_close_matches(query, names, n=5, cutoff=0.75):
                for definition in index.get("definitions", {}).get(name, []):
                    results.append({
                        "path": definition["file"], "line": definition["line"],
                        "text": f"fuzzy: {name}", "score": 1.0, "source": "fuzzy",
                    })
        # Local TF-IDF semantic retrieval supplements exact/FTS results.
        if len(results) < limit:
            from semantic import search as semantic_search

            for item in semantic_search(query, limit):
                if item["path"] not in {r["path"] for r in results}:
                    results.append(item)

        # Local neural embeddings re-rank the assembled shortlist (supplement,
        # never replacement). Exact and filename hits keep their precedence.
        import os

        if results and os.environ.get("IAM_NO_NEURAL") != "1":
            from neural import rerank as neural_rerank

            reranked = neural_rerank(query, results, limit)
            if reranked:
                protected = [r for r in results if r.get("source") in ("symbol", "filename")]
                results = protected + reranked

        seen: set[tuple[str, int, str]] = set()
        unique = []
        for result in results:
            key = (result["path"], result["line"], result["text"])
            if key not in seen:
                seen.add(key)
                unique.append(result)
        return sorted(unique, key=lambda r: -r["score"])[:limit]


# ---------------------------------------------------------------------------
# Git history / changelog
# ---------------------------------------------------------------------------

def git_history(query: str, limit: int = 20, regex: bool = False) -> list[dict[str, str]]:
    flag = "-G" if regex else "-S"
    return [{"commit": line, "kind": "pickaxe"}
            for line in git("log", "--oneline", "--all", "-n", str(limit), flag, query)]


def git_blame(path: str, line: int) -> list[str]:
    return git("blame", "-L", f"{line},{line}", "--", path)


def git_diff(from_ref: str, to_ref: str = "HEAD") -> list[str]:
    return git("diff", "--stat", from_ref, to_ref)


def changelog(from_ref: str, to_ref: str = "HEAD") -> list[dict[str, str]]:
    lines = git("log", "--pretty=format:%h%x09%s", f"{from_ref}..{to_ref}")
    return [{"commit": part[0], "subject": part[1]}
            for part in (line.split("\t", 1) for line in lines) if len(part) == 2]
