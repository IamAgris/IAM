"""Static security inspection for skill packages.

No skill code is executed here. This is a conservative, text-based gate that
catches prompt injection, self-escalation, secret exposure and obviously
destructive commands before a skill can be validated or tested.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Pattern, Tuple

INSPECTABLE_SUFFIXES = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".sh", ".toml",
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


@dataclass(frozen=True)
class Finding:
    severity: str  # info | low | medium | high | critical
    code: str
    path: str
    message: str
    line: int = 0

    def to_dict(self) -> Dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "line": self.line,
        }


# (code, severity, compiled pattern, human-readable message)
RULES: Tuple[Tuple[str, str, Pattern, str], ...] = (
    (
        "PROMPT_INJECTION",
        "critical",
        re.compile(
            r"(?i)(ignore|disregard|forget|override)\s+(?:all\s+|any\s+)?"
            r"(?:previous|prior|above|earlier|system)\s+"
            r"(?:instructions|prompts|rules|messages)"
        ),
        "Attempts to override higher-priority instructions",
    ),
    (
        "ROLE_OVERRIDE",
        "high",
        re.compile(
            r"(?i)(you are now|act as (?:an? )?(?:unrestricted|evil|dan)\b|"
            r"jailbreak|developer mode enabled|pretend you have no (?:rules|limits))"
        ),
        "Attempts to replace IAM's role or safety constraints",
    ),
    (
        "SELF_ESCALATION",
        "critical",
        re.compile(
            r"(?i)(grant yourself|give yourself|escalate (?:your )?permissions|"
            r"bypass (?:the )?(?:approval|permission|security|constitution)|"
            r"override (?:the )?(?:constitution|security|permissions)|"
            r"modify protected core|ignore permissions|self[- ]approve)"
        ),
        "Attempts to widen the skill's own authority",
    ),
    (
        "SECRET_EXPOSURE",
        "critical",
        re.compile(
            r"(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|"
            r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)"
        ),
        "Possible hardcoded credential or private key",
    ),
    (
        "HARDCODED_SECRET",
        "high",
        re.compile(
            r"(?i)(api[_-]?key|password|passwd|secret|access[_-]?token)\s*[:=]\s*"
            r"[\"'][^\"']{8,}[\"']"
        ),
        "Possible hardcoded secret assignment",
    ),
    (
        "DESTRUCTIVE_COMMAND",
        "high",
        re.compile(
            r"(rm\s+-rf\s+(?:/|~|\.)(?=\s|$|;|&&|\|)|"
            r":\(\)\{\s*:\|\:&?\s*\};\s*:|mkfs(\.[a-z0-9]+)?\s|"
            r"dd\s+if=[^\n]*of=/dev/)"
        ),
        "Contains a destructive shell command",
    ),
    (
        "PIPE_TO_SHELL",
        "high",
        re.compile(r"(?i)\b(curl|wget)\b[^\n|]*\|\s*(ba|z|sh|ksh)?sh\b"),
        "Pipes downloaded content into a shell",
    ),
    (
        "DYNAMIC_EXECUTION",
        "medium",
        re.compile(
            r"\b(eval|exec)\s*\(|os\.system\s*\(|"
            r"subprocess\.[a-z_]+\s*\([^)]*shell\s*=\s*True"
        ),
        "Uses dynamic code execution",
    ),
    (
        "PRIVILEGE_ESCALATION",
        "high",
        re.compile(r"(?i)\b(sudo\b|chmod\s+777|chown\s+root|setuid\s*\()"),
        "Requests elevated OS privileges",
    ),
)

BLOCKING_SEVERITIES = {"high", "critical"}


class SecurityValidator:
    """Inspects skill package text files without executing them."""

    def __init__(self, max_file_bytes: int = 262144):
        self.max_file_bytes = max_file_bytes

    def scan_text(self, text: str, rel_path: str) -> List[Finding]:
        findings: List[Finding] = []
        for code, severity, pattern, message in RULES:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(Finding(severity, code, rel_path, message, line))
        return findings

    def scan_directory(self, root: Path) -> List[Finding]:
        if not root.exists():
            return []
        findings: List[Finding] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS or part.startswith(".") for part in path.relative_to(root).parts):
                continue
            if path.suffix.lower() not in INSPECTABLE_SUFFIXES:
                continue
            try:
                if path.stat().st_size > self.max_file_bytes:
                    findings.append(
                        Finding(
                            "info",
                            "FILE_TOO_LARGE",
                            str(path.relative_to(root)),
                            "File skipped by security inspection (size limit)",
                        )
                    )
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                findings.append(
                    Finding("medium", "READ_ERROR", str(path.relative_to(root)), str(exc))
                )
                continue
            findings.extend(self.scan_text(text, str(path.relative_to(root))))
        return findings

    @staticmethod
    def has_blocking_findings(findings: List[Finding]) -> bool:
        return any(f.severity in BLOCKING_SEVERITIES for f in findings)
