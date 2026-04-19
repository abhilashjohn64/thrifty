from tests.conftest import _savings
from thrifty.filters.search import (
    _clean_grep_line,
    _compact_path,
    _strip_rg_incompatible,
    filter_grep_output,
)

_BASIC_GREP = "\n".join(
    [f"src/foo.py:{i}:def func_{i}(x):" for i in range(1, 8)]
    + [f"src/bar.py:{i}:def other_{i}():" for i in range(1, 4)]
)

# ---------------------------------------------------------------------------
# filter_grep_output
# ---------------------------------------------------------------------------

def test_grep_header_shows_totals():
    out = filter_grep_output(_BASIC_GREP, "def")
    assert "10 matches" in out
    assert "2 file" in out


def test_grep_groups_by_file():
    out = filter_grep_output(_BASIC_GREP, "def")
    assert "[file] src/foo.py" in out
    assert "[file] src/bar.py" in out


def test_grep_caps_per_file():
    lines = "\n".join(f"src/foo.py:{i}:match" for i in range(15))
    out = filter_grep_output(lines, "match")
    assert "+5 more" in out


def test_grep_caps_total():
    lines = "\n".join(f"src/file{i % 6}.py:{i}:match" for i in range(60))
    out = filter_grep_output(lines, "match")
    assert "more matches" in out


def test_grep_zero_matches():
    out = filter_grep_output("", "xyz")
    assert "0 matches" in out


def test_grep_output_is_structured():
    # Small fixture — no savings assertion; just verify structure is correct
    out = filter_grep_output(_BASIC_GREP, "def")
    assert out.startswith("10 matches")


# ---------------------------------------------------------------------------
# _clean_grep_line
# ---------------------------------------------------------------------------

def test_clean_short_line_unchanged():
    line = "def process(data):"
    assert _clean_grep_line(line, "process") == line


def test_clean_long_line_contains_match():
    line = "x" * 5000 + "TARGET" + "y" * 5000
    out = _clean_grep_line(line, "TARGET")
    assert "TARGET" in out
    assert len(out) <= 90


def test_clean_long_line_truncated_with_ellipsis():
    line = "x" * 5000 + "TARGET" + "y" * 5000
    out = _clean_grep_line(line, "TARGET")
    assert "..." in out


def test_clean_no_match_in_long_line():
    line = "a" * 200
    out = _clean_grep_line(line, "notfound")
    assert len(out) <= 83  # MAX_LINE_LEN + "..."
    assert out.endswith("...")


# ---------------------------------------------------------------------------
# _strip_rg_incompatible
# ---------------------------------------------------------------------------

def test_strip_removes_r_flag():
    args = ["-r", "--recursive", "-n", "pattern", "src/"]
    result = _strip_rg_incompatible(args)
    assert "-r" not in result
    assert "--recursive" not in result
    assert "-n" in result
    assert "pattern" in result


def test_strip_noop_when_no_incompatible():
    args = ["-n", "--no-heading", "pattern"]
    assert _strip_rg_incompatible(args) == args


# ---------------------------------------------------------------------------
# _compact_path
# ---------------------------------------------------------------------------

def test_compact_path_short_unchanged():
    assert _compact_path("src/foo.py") == "src/foo.py"


def test_compact_path_long_shortened():
    long = "home/user/projects/myapp/src/components/ui/buttons/primary/LargeButton.tsx"
    out = _compact_path(long)
    assert "..." in out
    assert out.endswith("LargeButton.tsx")
