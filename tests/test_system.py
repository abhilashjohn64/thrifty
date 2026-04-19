from tests.conftest import _savings
from thrifty.filters.system import _parse_ls_line, compact_ls

_BASIC_LS = """\
total 48
drwxr-xr-x  5 john  staff    160 Apr 19 10:23 .
drwxr-xr-x  3 john  staff     96 Apr 18 09:11 ..
drwxr-xr-x  3 john  staff     96 Apr 17 08:45 src
-rw-r--r--  1 john  staff   4823 Apr 19 14:02 README.md
-rw-r--r--  1 john  staff  12400 Apr 19 11:30 main.py
drwxr-xr-x  2 john  staff     64 Apr 19 09:00 node_modules
drwxr-xr-x  2 john  staff     64 Apr 19 09:00 .git
"""

# ---------------------------------------------------------------------------
# _parse_ls_line
# ---------------------------------------------------------------------------

def test_parse_valid_file():
    line = "-rw-r--r--  1 john staff  4823 Apr 19 14:02 README.md"
    result = _parse_ls_line(line)
    assert result is not None
    file_type, size, name = result
    assert file_type == "-"
    assert size == 4823
    assert name == "README.md"


def test_parse_directory():
    line = "drwxr-xr-x  3 john staff  96 Apr 17 08:45 src"
    result = _parse_ls_line(line)
    assert result is not None
    assert result[0] == "d"
    assert result[2] == "src"


def test_parse_rejects_total():
    assert _parse_ls_line("total 48") is None


def test_parse_rejects_empty():
    assert _parse_ls_line("") is None


def test_parse_group_with_spaces():
    line = "-rw-r--r--  1 john smith  domain users  4823 Apr 19 14:02 README.md"
    result = _parse_ls_line(line)
    assert result is not None
    assert result[2] == "README.md"


def test_parse_filename_with_spaces():
    line = "-rw-r--r--  1 john  staff  4823 Apr 19 14:02 My Document Final.pdf"
    result = _parse_ls_line(line)
    assert result is not None
    assert result[2] == "My Document Final.pdf"


def test_parse_year_format():
    # Older files show year instead of time
    line = "-rw-r--r--  1 john  staff  1000 Jan  5  2022 archive.tar.gz"
    result = _parse_ls_line(line)
    assert result is not None
    assert result[2] == "archive.tar.gz"


# ---------------------------------------------------------------------------
# compact_ls
# ---------------------------------------------------------------------------

def test_ls_strips_metadata():
    entries, _ = compact_ls(_BASIC_LS)
    assert "drwxr" not in entries
    assert "Apr" not in entries
    assert "john" not in entries
    assert "staff" not in entries


def test_ls_hides_noise_dirs():
    entries, _ = compact_ls(_BASIC_LS)
    assert "node_modules" not in entries
    assert ".git" not in entries


def test_ls_shows_noise_dirs_with_show_all():
    entries, _ = compact_ls(_BASIC_LS, show_all=True)
    assert "node_modules" in entries
    assert ".git" in entries


def test_ls_dirs_have_trailing_slash():
    entries, _ = compact_ls(_BASIC_LS)
    assert "src/" in entries


def test_ls_files_have_sizes():
    entries, _ = compact_ls(_BASIC_LS)
    assert "README.md" in entries
    assert "4.7K" in entries or "4.8K" in entries  # 4823 bytes ≈ 4.7K


def test_ls_skips_dot_entries():
    entries, _ = compact_ls(_BASIC_LS)
    # . and .. should not appear as standalone entries
    assert "\n./\n" not in entries
    assert "\n../\n" not in entries


def test_ls_empty_directory():
    raw = "total 0\ndrwxr-xr-x  2 john staff 64 Apr 19 10:00 .\ndrwxr-xr-x  3 john staff 96 Apr 19 09:00 ..\n"
    entries, _ = compact_ls(raw)
    assert "(empty)" in entries


def test_ls_summary_contains_counts():
    _, summary = compact_ls(_BASIC_LS)
    assert "files" in summary
    assert "dirs" in summary


def test_ls_savings():
    entries, summary = compact_ls(_BASIC_LS)
    assert _savings(_BASIC_LS, entries + summary) >= 40
