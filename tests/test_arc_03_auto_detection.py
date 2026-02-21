import os
import pytest
from unittest.mock import patch, MagicMock
from run_audit import run_audit
from core.audit.config_models import AuditConfig, TableConfig

@pytest.fixture
def mock_large_files():
    # Setup dummy paths
    src = "large_src.csv"
    tgt = "large_tgt.csv"
    
    with patch("os.path.exists", return_value=True), \
         patch("os.path.getsize") as mock_size:
        # Mock sizes to be > 50MB
        # 60MB = 60 * 1024 * 1024 bytes
        mock_size.return_value = 60 * 1024 * 1024
        yield src, tgt

def test_arc_03_auto_detect_large_files(mock_large_files):
    src, tgt = mock_large_files
    
    # Minimal config that should trigger auto-detection
    # large_file_threshold_mb defaults to 50.0
    config_obj = AuditConfig(
        tables={
            "large_table": TableConfig(
                source=src,
                target=tgt,
                primary_key="id"
            )
        }
    )
    
    with patch("run_audit.load_config", return_value=config_obj), \
         patch("run_audit.IncrementalRunner") as mock_runner, \
         patch("run_audit.authenticate_cli_user", return_value=True):
        
        # Mock the runner instance and its methods
        mock_runner_inst = mock_runner.return_value
        mock_runner_inst.finalize.return_value = []
        
        results = run_audit(no_auth=True)
        
        # Verify IncrementalRunner was called for 'large_table'
        mock_runner.assert_called_once()
        args, kwargs = mock_runner.call_args
        assert kwargs["table_name"] == "large_table"
        assert kwargs["chunk_size"] == 50000  # Default fallback
