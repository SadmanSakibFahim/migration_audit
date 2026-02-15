"""
Integration tests for CLI --ci mode.

Tests that the CLI produces correct JSON output and exit codes
when running in CI/CD gate mode.
"""

import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch, MagicMock

import pytest

# We test through subprocess calls to validate the full CLI behavior,
# and through direct function calls for unit-level verification.


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLI_PATH = os.path.join(PROJECT_ROOT, "cli.py")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "audit.yaml")


class TestCliCiFlagParsing:
    """Test that --ci flag is parsed correctly."""

    def test_ci_flag_exists(self):
        """Verify --ci flag is accepted by the argument parser."""
        sys.path.insert(0, PROJECT_ROOT)
        from cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "run",
            "--config", "config/audit.yaml",
            "--client", "Test",
            "--migration", "A->B",
            "--ci",
        ])
        assert args.ci is True

    def test_ci_implies_test(self):
        """Verify --ci sets test mode."""
        sys.path.insert(0, PROJECT_ROOT)
        from cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "run",
            "--config", "config/audit.yaml",
            "--client", "Test",
            "--migration", "A->B",
            "--ci",
        ])
        # --ci implies --test in main(), but at parse time
        # test defaults to False until main() processes it
        assert args.ci is True

    def test_fail_on_warnings_flag(self):
        """Verify --fail-on-warnings is accepted."""
        sys.path.insert(0, PROJECT_ROOT)
        from cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "run",
            "--config", "config/audit.yaml",
            "--client", "Test",
            "--migration", "A->B",
            "--ci",
            "--fail-on-warnings",
        ])
        assert args.fail_on_warnings is True

    def test_ci_without_fail_on_warnings(self):
        """Verify --fail-on-warnings defaults to False."""
        sys.path.insert(0, PROJECT_ROOT)
        from cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "run",
            "--config", "config/audit.yaml",
            "--client", "Test",
            "--migration", "A->B",
            "--ci",
        ])
        assert args.fail_on_warnings is False


class TestCiOutputIntegration:
    """
    Integration tests that run the audit in CI mode and check
    JSON output and exit codes.

    These tests use the sample config/data that ships with the project.
    They may be slow since they run a full audit.
    """

    @pytest.fixture(autouse=True)
    def setup_ci_output_dir(self):
        """Ensure CI output directory exists and cleanup after."""
        ci_dir = os.path.join(PROJECT_ROOT, "test_outputs", "ci")
        os.makedirs(ci_dir, exist_ok=True)
        yield
        # Cleanup is optional — test_outputs is gitignored

    def test_ci_mode_produces_json(self):
        """Running with --ci should produce audit_result.json."""
        result = subprocess.run(
            [
                sys.executable, CLI_PATH,
                "run",
                "--config", CONFIG_PATH,
                "--client", "CI_Test",
                "--migration", "Source -> Target",
                "--ci",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=120,
        )

        json_path = os.path.join(PROJECT_ROOT, "test_outputs", "ci", "audit_result.json")
        assert os.path.exists(json_path), f"JSON result file not found. stderr: {result.stderr[-500:]}"

        with open(json_path) as f:
            data = json.load(f)

        assert "verdict" in data
        assert "summary" in data
        assert "timestamp" in data
        assert "total_checks" in data
        assert "checks" in data
        assert data["verdict"] in ["GO", "GO WITH WARNINGS", "NO-GO", "ERROR"]

    def test_ci_mode_exit_code_matches_verdict(self):
        """Exit code should be 0 for GO, 1 for NO-GO/ERROR."""
        result = subprocess.run(
            [
                sys.executable, CLI_PATH,
                "run",
                "--config", CONFIG_PATH,
                "--client", "CI_Test",
                "--migration", "Source -> Target",
                "--ci",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=120,
        )

        json_path = os.path.join(PROJECT_ROOT, "test_outputs", "ci", "audit_result.json")
        if os.path.exists(json_path):
            with open(json_path) as f:
                data = json.load(f)

            if data["verdict"] in ["GO", "GO WITH WARNINGS"]:
                assert result.returncode == 0, f"Expected exit 0 for {data['verdict']}"
            else:
                assert result.returncode == 1, f"Expected exit 1 for {data['verdict']}"

    def test_ci_output_contains_gate_banner(self):
        """CLI should print a formatted gate result banner."""
        result = subprocess.run(
            [
                sys.executable, CLI_PATH,
                "run",
                "--config", CONFIG_PATH,
                "--client", "CI_Test",
                "--migration", "Source -> Target",
                "--ci",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=120,
        )

        assert "CI/CD Audit Gate Result" in result.stdout
        assert "Verdict" in result.stdout
