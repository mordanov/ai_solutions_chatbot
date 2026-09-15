"""Rule-based blocklist for detecting unsafe content in responses."""
import re

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{32,}"),                             # OpenAI API keys
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),  # JWT tokens
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"reveal\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?(?:DAN|developer\s+mode)", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous\s+)?(?:instructions|guidelines)", re.IGNORECASE),
]


class RuleBlocklist:
    """Check text against hard-coded regex patterns for secrets and injection probes."""

    def check(self, text: str) -> bool:
        """Return True if text matches any blocked pattern."""
        return any(p.search(text) for p in _PATTERNS)
