"""
Integration tests for scripts/audit_gate.sh.

Tests the shell wrapper script that powers the GitHub Action.
Verifies it correctly parses inputs, sets outputs, and handles exit codes.
"""

import os
import shutil
import subprocess
import tempfile

import pytest

SCRIPT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "audit_gate.sh")
)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestAuditGateScript:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Create temp files for GITHUB_OUTPUT and GITHUB_STEP_SUMMARY."""
        self.temp_dir = tempfile.mkdtemp()
        self.github_output = os.path.join(self.temp_dir, "github_output")
        self.github_step_summary = os.path.join(self.temp_dir, "github_step_summary")

        # Touch files
        open(self.github_output, "w").close()
        open(self.github_step_summary, "w").close()

        # Default env vars
        self.env = os.environ.copy()

        # 🚨 CRITICAL: Remove VIRTUAL_ENV so the script doesn't pick up the empty venv
        if "VIRTUAL_ENV" in self.env:
            del self.env["VIRTUAL_ENV"]

        # Ensure /usr/bin is at the front of PATH to pick up system python3
        self.env["PATH"] = f"/usr/bin:{self.env.get('PATH', '')}"

        self.env["GITHUB_OUTPUT"] = self.github_output
        self.env["GITHUB_STEP_SUMMARY"] = self.github_step_summary
        self.env["INPUT_CONFIG_PATH"] = "config/audit.yaml"
        self.env["INPUT_CLIENT_NAME"] = "TestClient"
        self.env["INPUT_MIGRATION_DESC"] = "TestMig"

        yield

        shutil.rmtree(self.temp_dir)

    def test_script_execution_pass(self):
        """Test script runs and passes (exit 0) on clean sample data.

        The sample data has identical source/target with valid FKs and mappings,
        so the audit should produce a GO verdict.
        """
        result = subprocess.run(
            [SCRIPT_PATH],
            cwd=PROJECT_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Script failed!\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert "Verdict : GO" in result.stdout

        # Check GitHub Output
        with open(self.github_output) as f:
            content = f.read()
            assert "verdict=GO" in content
            assert "results_json=" in content

        # Check Step Summary
        with open(self.github_step_summary) as f:
            content = f.read()
            assert "## 🔍 Migration Audit Gate" in content
            assert "### ✅ Verdict: GO" in content
            assert "| ❌ Fail | 0 |" in content

    def test_fail_on_warnings_flag(self):
        """Test INPUT_FAIL_ON_WARNINGS passed to CLI."""
        self.env["INPUT_FAIL_ON_WARNINGS"] = "true"

        result = subprocess.run(
            [SCRIPT_PATH],
            cwd=PROJECT_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
        )

        # Should still output fail-on-warnings in logs
        assert result.returncode == 0, f"Script failed!\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert "Fail on warnings: true" in result.stdout
