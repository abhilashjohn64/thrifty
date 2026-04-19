import pytest
from tests.conftest import _savings
from thrifty.filters.git import (
    compact_diff,
    filter_log_output,
    format_status_output,
)

# ---------------------------------------------------------------------------
# git status
# ---------------------------------------------------------------------------

def test_status_clean():
    out = format_status_output("## main...origin/main\n")
    assert "clean" in out.lower()


def test_status_dirty(tmp_path):
    raw = "## main...origin/main\nM  app.py\n?? notes.txt\nA  new.py\n"
    out = format_status_output(raw)
    assert "Staged" in out
    assert "Untracked" in out


def test_status_detached_head():
    porcelain = "## HEAD (no branch)\n?? foo.py\n"
    out = format_status_output(porcelain)
    assert "detached" in out.lower()


def test_status_ahead_behind():
    porcelain = "## main...origin/main [ahead 2, behind 1]\nM  app.py\n"
    out = format_status_output(porcelain)
    assert "ahead: 2" in out
    assert "behind: 1" in out


def test_status_file_cap():
    lines = ["## main"] + [f"?? file{i}.py" for i in range(10)]
    out = format_status_output("\n".join(lines))
    assert "+5 more" in out


def test_status_conflicts():
    porcelain = "## main\nUU conflict.py\n"
    out = format_status_output(porcelain)
    assert "Conflict" in out


# ---------------------------------------------------------------------------
# git log
# ---------------------------------------------------------------------------

def test_log_subject_truncated():
    long_subject = "x" * 200
    raw = f"abc1234 {long_subject} (2 hours ago) <a@b.com>\n---END---\n"
    out = filter_log_output(raw, limit=20, user_set_limit=False, user_format=False)
    assert len(out.splitlines()[0]) <= 83  # 80 + "..."


def test_log_block_parsed():
    raw = "abc1234 fix: something (1 day ago) <dev@x.com>\n\n---END---\n"
    out = filter_log_output(raw, limit=20, user_set_limit=False, user_format=False)
    assert "abc1234" in out
    assert "fix: something" in out


def test_log_trailer_stripped():
    raw = (
        "abc1234 feat: add thing (1 hour ago) <dev@x.com>\n"
        "Signed-off-by: Bot <bot@ci.com>\n"
        "---END---\n"
    )
    out = filter_log_output(raw, limit=20, user_set_limit=False, user_format=False)
    assert "Signed-off-by" not in out


def test_log_user_format_passthrough():
    raw = "abc1234 short message\ndef5678 another commit\n"
    out = filter_log_output(raw, limit=20, user_set_limit=False, user_format=True)
    assert "abc1234" in out
    assert "def5678" in out


# ---------------------------------------------------------------------------
# git diff
# ---------------------------------------------------------------------------

def test_diff_small_hunk_preserved():
    small = "diff --git a/f b/f\n@@ -1,3 +1,5 @@\n+line1\n+line2\n context\n"
    out = compact_diff(small, max_hunk_lines=100)
    assert "truncated" not in out
    assert "+line1" in out


def test_diff_large_hunk_truncated():
    changed = "".join(f"+line{i}\n" for i in range(200))
    big = f"diff --git a/f b/f\n@@ -1,1 +1,200 @@\n{changed}"
    out = compact_diff(big, max_hunk_lines=100)
    assert "truncated" in out


def test_diff_shows_file_name():
    diff = "diff --git a/src/foo.py b/src/foo.py\n@@ -1 +1 @@\n+x\n"
    out = compact_diff(diff)
    assert "src/foo.py" in out


def test_diff_empty_input():
    assert compact_diff("") == ""
