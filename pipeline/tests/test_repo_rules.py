"""Repo-wide rules from CLAUDE.md."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "out",
    "cache",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
}
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".css"}
GENERATED = {"web/src/types/chapter.ts", "web/next-env.d.ts"}
MAX_LINES, MAX_FILE_MB, MAX_TOTAL_MB = 500, 25, 150


def walk():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not any(part in SKIP_DIRS for part in rel.parts):
            yield p, rel.as_posix()


def test_source_files_within_line_limit():
    too_long = {
        rel: n
        for p, rel in walk()
        if p.suffix in SOURCE_SUFFIXES
        and rel not in GENERATED
        and (n := len(p.read_text(encoding="utf-8").splitlines())) > MAX_LINES
    }
    assert not too_long, too_long


def test_claude_md_within_line_limit():
    assert len((ROOT / "CLAUDE.md").read_text().splitlines()) <= 40


def test_no_credential_files():
    bad = [
        rel
        for _, rel in walk()
        if Path(rel).name in {".netrc", "_netrc", ".env"} or Path(rel).suffix == ".pem"
    ]
    assert not bad, bad


def test_no_credentials_in_text():
    pattern = re.compile(
        r"machine\s+urs\.earthdata|EARTHDATA_(?:PASSWORD|TOKEN)\s*=\s*\S|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY"
    )
    hits = []
    for p, rel in walk():
        if (
            p.suffix in {".md", ".py", ".toml", ".json", ".yml", ".yaml", ".ts", ".tsx", ".mjs", ".txt"}
            and rel != "pipeline/tests/test_repo_rules.py"
        ):
            if pattern.search(p.read_text(encoding="utf-8", errors="ignore")):
                hits.append(rel)
    assert not hits, hits


def test_public_data_size_budget():
    files = [(p, p.stat().st_size) for p, rel in walk() if rel.startswith("web/public/data/")]
    big = {p.name: s for p, s in files if s > MAX_FILE_MB * 1e6}
    assert not big, big
    assert sum(s for _, s in files) <= MAX_TOTAL_MB * 1e6
