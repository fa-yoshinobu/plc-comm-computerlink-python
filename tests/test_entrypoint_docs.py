import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_samples_readme_uses_current_paths() -> None:
    text = _read("samples/README.md")

    assert "python samples/high_level_minimal.py" in text
    assert "device_monitor_gui.py" not in text
    assert "low_level_basic.py" not in text
    assert "../scripts/README.md" in text
    assert "examples/" not in text
    assert "../tools/README.md" not in text


def test_samples_and_scripts_use_current_transport_keyword() -> None:
    client_names = {
        "ToyopucClient",
        "ToyopucDeviceClient",
        "AsyncToyopucClient",
        "AsyncToyopucDeviceClient",
    }
    violations: list[str] = []

    for folder in ("samples", "scripts"):
        for path in sorted((REPO_ROOT / folder).glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Name):
                    function_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    function_name = node.func.attr
                else:
                    continue
                if function_name in client_names and any(keyword.arg == "protocol" for keyword in node.keywords):
                    violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert violations == []


def test_user_docs_focus_on_high_level_api_only() -> None:
    readme = _read("README.md")
    user_guide = _read("docsrc/user/USAGE_GUIDE.md")
    api_ref = REPO_ROOT / "docsrc" / "api" / "client.md"
    combined = "\n".join([readme, user_guide])

    assert "ToyopucDeviceClient" in combined
    assert "open_and_connect" in combined
    assert "ToyopucClient" not in combined
    assert "low-level" not in combined.lower()
    assert not api_ref.exists()
    assert ":::" not in combined


def test_scripts_readme_uses_current_paths() -> None:
    text = _read("scripts/README.md")

    assert "This directory contains Python helper programs only." in text
    assert "scripts/run_" not in text
    assert "run_sim_tests.bat" not in text
    assert "scripts/sim_server.py" in text
    assert "tools/" not in text
    assert "tools\\" not in text


def test_run_ci_documents_current_static_analysis_policy() -> None:
    text = _read("run_ci.bat")

    assert "python -m ruff check toyopuc tests scripts samples" in text
    assert "python -m ruff format --check toyopuc tests scripts samples" in text
    assert "python -m mypy toyopuc" in text
    assert "for %%F in (scripts\\*.py samples\\*.py)" in text
    assert "run_sim_tests.bat" not in text


def test_release_check_checks_canonical_profiles_then_delegates_to_ci() -> None:
    text = _read("release_check.bat")

    assert "[2/4] Checking canonical ComputerLink profile fixtures" in text
    assert "scripts\\update_computerlink_profile_jsons.ps1 -FailIfChanged" in text
    assert "[3/4] Checking GitHub source archive contents" in text
    assert "scripts\\check_source_archive.ps1" in text
    assert "[4/4] Running CI" in text
    assert "call run_ci.bat" in text
    assert text.count("call ") == 1


def test_historical_release_notes_use_current_repo_paths() -> None:
    for path in sorted((REPO_ROOT / "docsrc" / "maintainer").glob("GITHUB_RELEASE_*.md")):
        text = path.read_text(encoding="utf-8")
        assert "docsrc/TESTING.md" not in text
        assert "docsrc/RELEASE.md" not in text
        assert "examples/README.md" not in text
        assert "tools/README.md" not in text
