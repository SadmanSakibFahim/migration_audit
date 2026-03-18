"""QA Tests for T003 — Core Audit Hardening
===========================================
New features: execute_chunked(), progress_callback, _report_progress(),
relationship check loading parent table.

"""

from unittest.mock import MagicMock

import pandas as pd

from core.audit.check_runner import CheckRunner
from core.audit.config_models import RelationshipConfig, TableConfig
from core.audit.enums import CheckStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _meta(pk="id", aggregates=None, relationships=None):
    kwargs = {
        "source": "test_src.csv",
        "target": "test_tgt.csv",
        "primary_key": pk,
        "aggregates": aggregates or [],
    }
    if relationships:
        kwargs["relationships"] = relationships
    return TableConfig(**kwargs)


def _basic_runner(src_df=None, tgt_df=None, meta=None, progress_callback=None):
    if meta is None:
        meta = _meta()
    if src_df is None:
        src_df = pd.DataFrame({"id": [1, 2, 3], "amount": [100.0, 200.0, 300.0]})
    if tgt_df is None:
        tgt_df = pd.DataFrame({"id": [1, 2, 3], "amount": [100.0, 200.0, 300.0]})
    return CheckRunner(
        "test_table",
        meta,
        src_df,
        tgt_df,
        progress_callback=progress_callback,
    )


# ===================================================================
# progress_callback and _report_progress
# ===================================================================


class TestProgressCallback:
    """Verifying progress_callback integration."""

    def test_callback_receives_messages(self):
        """Callback should be called with progress messages during execute_all."""
        messages = []
        runner = _basic_runner(progress_callback=lambda msg: messages.append(msg))
        runner.execute_all()
        # Should receive at least one message per check step + completion
        assert len(messages) >= 7  # 6 steps + "All checks complete"
        assert any("Volume checks" in m for m in messages)
        assert any("All checks complete" in m for m in messages)

    def test_callback_not_called_when_none(self):
        """No crash when progress_callback is None."""
        runner = _basic_runner(progress_callback=None)
        results = runner.execute_all()
        assert isinstance(results, list)

    def test_callback_error_does_not_crash_audit(self):
        """If callback raises an exception, audit should still complete."""

        def bad_callback(msg):
            raise RuntimeError("callback exploded")

        runner = _basic_runner(progress_callback=bad_callback)
        results = runner.execute_all()
        # Should still get valid results despite callback errors
        assert isinstance(results, list)
        assert len(results) > 0

    def test_report_progress_logs_message(self):
        """_report_progress should call logger.info and callback."""
        callback = MagicMock()
        runner = _basic_runner(progress_callback=callback)
        runner._report_progress("test message")
        callback.assert_called_once_with("test message")

    def test_step_numbering_in_messages(self):
        """Messages should contain step numbers like (1/13), (2/13), etc."""
        messages = []
        runner = _basic_runner(progress_callback=lambda msg: messages.append(msg))
        runner.execute_all()
        step_messages = [m for m in messages if "/" in m and "(" in m]
        assert len(step_messages) == 13  # Exactly 13 numbered steps


# ===================================================================
# execute_chunked
# ===================================================================


class TestExecuteChunked:
    """Verifying chunked/streaming processing."""

    def test_chunks_merged_correctly(self):
        """Chunks should be concatenated into a single DataFrame for processing."""
        src_chunks = [
            pd.DataFrame({"id": [1, 2], "amount": [10.0, 20.0]}),
            pd.DataFrame({"id": [3, 4], "amount": [30.0, 40.0]}),
        ]
        tgt_chunks = [
            pd.DataFrame({"id": [1, 2], "amount": [10.0, 20.0]}),
            pd.DataFrame({"id": [3, 4], "amount": [30.0, 40.0]}),
        ]
        runner = _basic_runner()
        results = runner.execute_chunked(iter(src_chunks), iter(tgt_chunks))
        assert isinstance(results, list)
        assert len(results) > 0
        # Verify DataFrames were merged
        assert len(runner.src_df) == 4
        assert len(runner.tgt_df) == 4

    def test_empty_chunks(self):
        """Empty iterators should produce empty DataFrames."""
        runner = _basic_runner()
        results = runner.execute_chunked(iter([]), iter([]))
        # Should have validation results (empty but valid DataFrames)
        assert isinstance(results, list)
        assert len(runner.src_df) == 0
        assert len(runner.tgt_df) == 0

    def test_single_chunk(self):
        """Single chunk should work identically to non-chunked."""
        src = pd.DataFrame({"id": [1, 2, 3], "amount": [100.0, 200.0, 300.0]})
        tgt = pd.DataFrame({"id": [1, 2, 3], "amount": [100.0, 200.0, 300.0]})

        # Non-chunked
        runner_normal = _basic_runner(src_df=src.copy(), tgt_df=tgt.copy())
        results_normal = runner_normal.execute_all()

        # Chunked (single chunk)
        runner_chunked = _basic_runner()
        results_chunked = runner_chunked.execute_chunked(
            iter([src.copy()]), iter([tgt.copy()])
        )

        # Same number of results, same statuses
        assert len(results_chunked) == len(results_normal)
        for rn, rc in zip(results_normal, results_chunked):
            assert rn.status == rc.status

    def test_chunked_reports_progress(self):
        """Progress callback should receive chunk loading messages."""
        messages = []
        runner = _basic_runner(progress_callback=lambda msg: messages.append(msg))

        src_chunks = [
            pd.DataFrame({"id": [1, 2]}),
            pd.DataFrame({"id": [3, 4]}),
        ]
        tgt_chunks = [
            pd.DataFrame({"id": [1, 2, 3, 4]}),
        ]
        runner.execute_chunked(iter(src_chunks), iter(tgt_chunks))

        chunk_msgs = [m for m in messages if "chunk" in m.lower()]
        assert len(chunk_msgs) >= 3  # 2 source chunks + 1 target chunk

    def test_large_chunked_data(self):
        """Stress test: 5 chunks of 2000 rows each."""
        import numpy as np

        rng = np.random.default_rng(42)

        chunks_src = [
            pd.DataFrame(
                {
                    "id": range(i * 2000, (i + 1) * 2000),
                    "amount": rng.uniform(1, 1000, 2000),
                }
            )
            for i in range(5)
        ]
        chunks_tgt = [
            pd.DataFrame(
                {
                    "id": range(i * 2000, (i + 1) * 2000),
                    "amount": rng.uniform(1, 1000, 2000),
                }
            )
            for i in range(5)
        ]

        runner = _basic_runner()
        results = runner.execute_chunked(iter(chunks_src), iter(chunks_tgt))
        assert len(runner.src_df) == 10_000
        assert len(runner.tgt_df) == 10_000
        assert len(results) > 0

    def test_unequal_chunk_sizes(self):
        """Source and target can have different numbers of chunks."""
        src_chunks = [
            pd.DataFrame({"id": [1]}),
            pd.DataFrame({"id": [2]}),
            pd.DataFrame({"id": [3]}),
        ]
        tgt_chunks = [
            pd.DataFrame({"id": [1, 2, 3]}),
        ]
        runner = _basic_runner()
        runner.execute_chunked(iter(src_chunks), iter(tgt_chunks))
        assert len(runner.src_df) == 3
        assert len(runner.tgt_df) == 3


# ===================================================================
# execute_all step-by-step progress
# ===================================================================


class TestExecuteAllProgress:
    """Verifying execute_all reports per-step progress."""

    def test_all_steps_reported(self):
        """All check categories should be reported."""
        messages = []
        runner = _basic_runner(progress_callback=lambda msg: messages.append(msg))
        runner.execute_all()

        expected_steps = [
            "Volume checks",
            "Identity checks",
            "Aggregate checks",
            "Mapping checks",
            "Relationship checks",
            "Data constraint checks",
            "String truncation checks",
            "Enum equivalence checks",
            "Datetime/TZ checks",
            "Null/sentinel checks",
            "Numeric precision checks",
            "Boolean checks",
            "Uniqueness checks",
        ]
        for step in expected_steps:
            assert any(step in m for m in messages), f"Missing progress for: {step}"

    def test_table_name_included_in_progress(self):
        """Progress messages should include the table name."""
        messages = []
        runner = _basic_runner(progress_callback=lambda msg: messages.append(msg))
        runner.execute_all()
        assert all("test_table" in m for m in messages)

    def test_aborted_run_does_not_report_steps(self):
        """If validation fails, no step progress should be reported."""
        messages = []
        runner = _basic_runner(progress_callback=lambda msg: messages.append(msg))
        runner.src_df = None  # Force validation failure
        runner.execute_all()
        # No step messages should fire
        assert not any("Running" in m for m in messages)


# ===================================================================
# Relationship check — parent table loading
# ===================================================================


class TestRelationshipCheckFix:
    """Verifying relationship STUB is fixed."""

    def test_relationship_loads_parent_from_target(self, tmp_path):
        """Relationship check should load parent table via load_table()."""
        # Create a parent CSV file
        parent_csv = tmp_path / "parents.csv"
        parent_df = pd.DataFrame({"parent_id": [10, 20, 30]})
        parent_df.to_csv(parent_csv, index=False)

        rel = RelationshipConfig(
            child={"target": "child_table", "fk_column": "parent_id"},
            parent={"target": str(parent_csv), "pk_column": "parent_id"},
        )

        child_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "parent_id": [10, 20, 99],  # 99 is orphan
            }
        )

        meta = _meta(relationships=[rel])
        runner = _basic_runner(tgt_df=child_df, meta=meta)
        results = runner.execute_all()

        # Should have relationship check results (check_links names them "Foreign Key Check")
        rel_results = [
            r for r in results if "Foreign Key" in r.name or "Relationship" in r.name
        ]
        assert len(rel_results) > 0

    def test_relationship_missing_parent_target_uses_fallback(self):
        """If parent target is empty, should fallback to tgt_df."""
        rel = RelationshipConfig(
            child={"target": "child_table", "fk_column": "id"},
            parent={"target": "", "pk_column": "id"},
        )
        meta = _meta(relationships=[rel])
        runner = _basic_runner(meta=meta)
        # Should not crash — uses fallback
        results = runner.execute_all()
        assert isinstance(results, list)

    def test_relationship_parent_load_failure_reported(self):
        """If parent table cannot be loaded, an ERROR result should be appended."""
        rel = RelationshipConfig(
            child={"target": "child_table", "fk_column": "parent_id"},
            parent={"target": "/nonexistent/path.csv", "pk_column": "parent_id"},
        )
        meta = _meta(relationships=[rel])
        runner = _basic_runner(meta=meta)
        results = runner.execute_all()

        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        assert any("Relationship" in r.name for r in error_results)
        assert any("nonexistent" in r.message for r in error_results)
