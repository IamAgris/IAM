"""Audit the frozen IAM architecture for consistency issues."""
import os, re, glob

root = r"D:\AI\project-aura"
docs = {}
for p in glob.glob(os.path.join(root, "*.md")) + glob.glob(os.path.join(root, "canonical", "*.md")):
    docs[os.path.relpath(p, root)] = open(p, encoding="utf-8").read()

print("=== 1. STALE PROJECT NAMES ===")
for name, text in docs.items():
    stale = []
    for term in ["Project AURA", "AURA", "Marlow", "Project Codename"]:
        c = len(re.findall(r'\b' + re.escape(term) + r'\b', text))
        if c: stale.append(f"{term}:{c}")
    if stale:
        print(f"  {name}: {', '.join(stale)}")

print("\n=== 2. DECISION COUNT CLAIMS ===")
claim_patterns = [
    r"ALL (?:TWENTY|THIRTY|SEVENTEEN|FIFTEEN|TEN|NINE|[A-Z]+)[\s-]*[A-Z]* DECISIONS LOCKED",
    r"(\d+) (?:locked|owner) decisions",
    r"ALL \d+ DECISIONS",
]
for name, text in docs.items():
    for m in re.finditer(r'[^.\n]{0,60}(?:DECISIONS LOCKED|decisions locked|decisions? (?:are )?(?:locked|confirmed))[^.\n]{0,60}', text, re.I):
        print(f"  {name}: ...{m.group(0).strip()}...")

print("\n=== 3. PHASE / COMPLETION CLAIMS ===")
for name, text in docs.items():
    for m in re.finditer(r'[^.\n]{0,50}(?:ALL FIVE|all five|Levels? [1-5]|Level [1-5]|Phases? 0-9|Phase 1[0-9]?)[^.\n]{0,60}', text):
        s = m.group(0).strip()
        if any(k in s for k in ["PASSED", "COMPLETE", "FROZEN", "frozen", "passed"]):
            print(f"  {name}: ...{s[:110]}...")

print("\n=== 4. ARCHITECTURE DOC REFERENCES ===")
refs = {}
for name, text in docs.items():
    for m in re.findall(r'`(IAM_[^`]+\.md|MASTER_SPECIFICATION\.md)`', text):
        refs.setdefault(m, set()).add(name)
missing = []
for ref in sorted(refs):
    if ref not in docs and not os.path.exists(os.path.join(root, ref)):
        missing.append(ref)
        print(f"  BROKEN REF: {ref} referenced in {sorted(refs[ref])}")

print("\n=== 5. KEY TERM CONSISTENCY ===")
terms = ["protected_core", "zero standing budget", "OD-04", "OD-05", "native", "x86-64"]
for term in terms:
    files = [n for n, t in docs.items() if term.lower() in t.lower()]
    print(f"  '{term}': {len(files)} docs")

print("\n=== 6. DOC LENGTHS ===")
for name, text in sorted(docs.items(), key=lambda x: -len(x[1])):
    print(f"  {len(text):6d}  {name}")
