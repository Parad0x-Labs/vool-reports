"""Re-check a newly opened or edited report for private data, label it, and flag repeats.

VOOL scrubs every report on the reporter's computer before they see it. This is the second
line: text typed or pasted straight into GitHub, or edited in after submitting. It masks what
it finds, labels the issue ``needs-scrub`` so a maintainer clears the edit history, and adds
``from-app`` / ``duplicate`` when the report carries a fingerprint seen before.

Standard library only. Reads the issue from GITHUB_EVENT_PATH and talks to the REST API with
GITHUB_TOKEN. Run with --dry-run FILE to print what would be masked in a text file.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request

FINGERPRINT_RE = re.compile(r"bug-report-fingerprint:\s*([0-9a-f]{16,64})")


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _is_card(match: re.Match) -> bool:
    digits = re.sub(r"\D", "", match.group(0))
    return 13 <= len(digits) <= 19 and len(set(digits)) > 1 and _luhn(digits)


def _is_iban(match: re.Match) -> bool:
    raw = re.sub(r"\s", "", match.group(0)).upper()
    if not 15 <= len(raw) <= 34:
        return False
    moved = raw[4:] + raw[:4]
    try:
        return int("".join(str(int(ch, 36)) for ch in moved)) % 97 == 1
    except ValueError:
        return False


def _phone(match: re.Match) -> bool:
    return 8 <= len(re.sub(r"\D", "", match.group(0))) <= 15


# (name, pattern, check or None, replacement). Order matters: specific before generic.
RULES: list[tuple[str, re.Pattern, object, str]] = [
    ("private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)", re.S), None, "[redacted-private-key]"),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{22,})"), None, "[redacted-token]"),
    ("api_key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|xox[abprs]-[A-Za-z0-9-]{10,})"), None, "[redacted-key]"),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}=*"), None, "Bearer [redacted-token]"),
    ("labelled_secret", re.compile(r"(?i)\b(password|passwd|passphrase|api[_-]?key|secret|token|seed phrase|mnemonic)(\s*[:=]\s*)(?!\[redacted)\S{4,}"), None, r"\1\2[redacted-secret]"),
    ("pin", re.compile(r"(?i)\b(pin|passcode|cvv|cvc|otp|one-time code|verification code|2fa code)(\s*(?:is|:|=)?\s*)(\d[\d -]{2,9}\d)\b"), None, r"\1\2[redacted-pin]"),
    ("evm_address", re.compile(r"\b0x[a-fA-F0-9]{40}\b"), None, "[redacted-wallet]"),
    ("card", re.compile(r"(?<![\w-])\d(?:[ -]?\d){12,18}(?![\w-])"), _is_card, "[redacted-card]"),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,4})?\b"), _is_iban, "[redacted-iban]"),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), None, "[redacted-email]"),
    ("phone", re.compile(r"(?<![\w+])\+\d[\d ().-]{6,18}\d(?!\w)"), _phone, "[redacted-phone]"),
    ("home_path", re.compile(r"(/Users/|/home/|[A-Za-z]:\\Users\\)(?!\[redacted)[^/\\\s]+"), None, r"\1[redacted-user]"),
]


def scrub(text: str) -> tuple[str, list[str]]:
    """(masked text, names of the rules that fired)."""
    hits: list[str] = []
    for name, pattern, check, replacement in RULES:
        def repl(match: re.Match, *, _check=check, _name=name, _replacement=replacement) -> str:
            if _check is not None and not _check(match):
                return match.group(0)
            hits.append(_name)
            return match.expand(_replacement)

        text = pattern.sub(repl, text)
    return text, sorted(set(hits))


def kind_label(title: str) -> str:
    return "wrong-answer" if title.lower().startswith("[wrong-answer]") else "bug"


def _api(method: str, path: str, payload: dict | None = None) -> dict | list:
    url = "https://api.github.com" + path
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed host
        body = response.read()
    return json.loads(body) if body else {}


def handle(event: dict, repo: str) -> None:
    issue = event["issue"]
    number = issue["number"]
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    labels = {kind_label(title)}

    new_title, title_hits = scrub(title)
    new_body, body_hits = scrub(body)
    hits = sorted(set(title_hits + body_hits))
    if hits:
        _api("PATCH", f"/repos/{repo}/issues/{number}", {"title": new_title, "body": new_body})
        labels.add("needs-scrub")
        _api("POST", f"/repos/{repo}/issues/{number}/comments", {"body": (
            "The automatic check masked something that looked private (" + ", ".join(hits) + "). "
            "A maintainer will clear the earlier version from this report's edit history. "
            "If you posted a real key or password, change it now: it was public for a moment."
        )})

    match = FINGERPRINT_RE.search(body)
    if match:
        labels.add("from-app")
        if event.get("action") == "opened":
            query = urllib.parse.quote(f'repo:{repo} is:issue "bug-report-fingerprint: {match.group(1)}"')
            found = _api("GET", f"/search/issues?q={query}&sort=created&order=asc&per_page=5")
            earlier = [item for item in found.get("items", []) if item.get("number") != number]
            if earlier:
                first = earlier[0]["number"]
                labels.add("duplicate")
                _api("POST", f"/repos/{repo}/issues/{number}/comments", {"body": (
                    f"Thanks. This looks like the same problem as #{first} (same report fingerprint). "
                    "Adding a 👍 there helps us see how many people hit it."
                )})
    _api("POST", f"/repos/{repo}/issues/{number}/labels", {"labels": sorted(labels)})
    print(f"#{number}: labels {sorted(labels)}; masked {hits or 'nothing'}")


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--dry-run":
        with open(argv[2], encoding="utf-8") as handle_:
            masked, hits = scrub(handle_.read())
        print(masked)
        print("rules:", hits, file=sys.stderr)
        return 0
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle_:
        event = json.load(handle_)
    handle(event, os.environ["GITHUB_REPOSITORY"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
