import subprocess
import sys


def _rewrite(cmd: str) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "-m", "thrifty", "rewrite", cmd],
        capture_output=True,
        text=True,
        cwd="/home/ajohn/Projects/AI_POC/thrifty",
    )
    return r.returncode, r.stdout.strip()


def test_rewrite_git_status():
    code, out = _rewrite("git status")
    assert code == 0
    assert "thrifty" in out
    assert "git status" in out


def test_rewrite_git_log_with_flags():
    code, out = _rewrite("git log -10 --oneline")
    assert code == 0
    assert "git log" in out


def test_rewrite_git_diff():
    code, out = _rewrite("git diff HEAD~1")
    assert code == 0
    assert "git diff" in out


def test_rewrite_ls():
    code, out = _rewrite("ls -la")
    assert code == 0
    assert "ls" in out


def test_rewrite_rg():
    code, out = _rewrite("rg -n pattern src/")
    assert code == 0


def test_rewrite_grep():
    code, out = _rewrite("grep -rn pattern src/")
    assert code == 0


def test_rewrite_unsupported_exits_1():
    code, _ = _rewrite("npm install")
    assert code == 1


def test_rewrite_compound_and_refused():
    code, _ = _rewrite("git status && git log")
    assert code == 1


def test_rewrite_pipe_refused():
    code, _ = _rewrite("git log | head -5")
    assert code == 1


def test_rewrite_already_wrapped():
    code, _ = _rewrite("python3 -m thrifty git status")
    assert code == 1


def test_rewrite_heredoc_refused():
    code, _ = _rewrite("cat << EOF")
    assert code == 1


def test_rewrite_semicolon_refused():
    code, _ = _rewrite("cd src; git diff")
    assert code == 1


def test_rewrite_empty_exits_1():
    code, _ = _rewrite("")
    assert code == 1
