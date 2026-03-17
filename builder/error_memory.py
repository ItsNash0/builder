"""Error pattern memory cache — learns from past failures to help agents avoid repeated mistakes.

Stores error patterns (build failures, test failures, common mistakes) in a JSON file
within .builder/errors.json. This is injected into agent context so they can learn from
prior rounds and avoid the same pitfalls.
"""

import json
import re
from pathlib import Path


MAX_PATTERNS = 50  # Cap stored patterns to prevent context bloat
MAX_PATTERN_CHARS = 500  # Truncate long error messages


def _normalize_error(error: str) -> str:
    """Normalize an error message for deduplication."""
    # Strip ANSI codes
    error = re.sub(r"\x1b\[[0-9;]*m", "", error)
    # Strip file paths (vary per machine)
    error = re.sub(r"/[\w/.\-]+", "<path>", error)
    # Strip line numbers
    error = re.sub(r"line \d+", "line N", error)
    # Collapse whitespace
    error = re.sub(r"\s+", " ", error).strip()
    return error[:MAX_PATTERN_CHARS]


class ErrorMemory:
    def __init__(self, builder_dir: Path):
        self.path = builder_dir / "errors.json"
        self._patterns: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._patterns = json.loads(self.path.read_text())
            except (json.JSONDecodeError, ValueError):
                self._patterns = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._patterns, indent=2))

    def record_error(self, phase: str, round_number: int, error: str, fix: str = "") -> None:
        """Record an error pattern with optional fix description."""
        normalized = _normalize_error(error)
        if not normalized:
            return

        # Check for duplicates
        for pattern in self._patterns:
            if pattern["normalized"] == normalized:
                pattern["count"] = pattern.get("count", 1) + 1
                if fix and not pattern.get("fix"):
                    pattern["fix"] = fix[:MAX_PATTERN_CHARS]
                self._save()
                return

        self._patterns.append({
            "phase": phase,
            "round": round_number,
            "error": error[:MAX_PATTERN_CHARS],
            "normalized": normalized,
            "fix": fix[:MAX_PATTERN_CHARS] if fix else "",
            "count": 1,
        })

        # Evict oldest if over cap
        if len(self._patterns) > MAX_PATTERNS:
            self._patterns = self._patterns[-MAX_PATTERNS:]

        self._save()

    def record_fix(self, error: str, fix: str) -> None:
        """Retroactively record a fix for a known error pattern."""
        normalized = _normalize_error(error)
        for pattern in self._patterns:
            if pattern["normalized"] == normalized:
                pattern["fix"] = fix[:MAX_PATTERN_CHARS]
                self._save()
                return

    def get_context_prompt(self) -> str:
        """Generate a prompt section summarizing known error patterns."""
        if not self._patterns:
            return ""

        lines = ["## Known Error Patterns (from prior rounds)", ""]
        for p in self._patterns:
            lines.append(f"- **{p['phase']}**: {p['error']}")
            if p.get("fix"):
                lines.append(f"  Fix: {p['fix']}")
            if p.get("count", 1) > 1:
                lines.append(f"  (seen {p['count']} times)")

        return "\n".join(lines)

    @property
    def patterns(self) -> list[dict]:
        return list(self._patterns)
