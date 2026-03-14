import os
import json
import pytest
from core.audit.enums import CheckStatus
from core.audit.result import TestResult
from reports.report_builder import build_report

def test_json_report_generation(tmp_path):
    """Test that build_report correctly generates a JSON file with valid structure."""
    
    # 1. Setup mock results
    results = [
        TestResult(
            name="Volume Check", 
            status=CheckStatus.PASS, 
            message="Counts match", 
            metrics={"src": 100, "tgt": 100}
        ),
        TestResult(
            name="Identity Check", 
            status=CheckStatus.FAIL, 
            message="ID mismatch", 
            details={"mismatched_ids": [101, 102]}
        ),
        TestResult(
            name="Status Mapping", 
            status=CheckStatus.WARN, 
            message="Found NULL status in target", 
            metrics={"null_count": 5}
        )
    ]
    
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    docx_path = output_dir / "Audit_Report.docx"
    
    # 2. Run build_report
    paths = build_report(
        results,
        output_path=str(docx_path),
        client="Test Client",
        migration="Source -> Target"
    )
    
    # 3. Assert JSON file exists
    json_path = paths["json"]
    assert os.path.exists(json_path)
    assert json_path.endswith(".json")
    
    # 4. Verify JSON content
    with open(json_path, "r") as f:
        data = json.load(f)
        
    # Check Metadata
    assert data["metadata"]["client"] == "Test Client"
    assert data["metadata"]["migration"] == "Source -> Target"
    assert "date" in data["metadata"]
    assert "integrity_hash" in data["metadata"]
    assert len(data["metadata"]["integrity_hash"]) == 64  # SHA-256 length
    
    # Check Summary
    assert data["summary"]["final_verdict"] == "NO-GO"  # Because we have a FAIL
    assert "Data Volume Checks" in data["summary"]["section_verdicts"]
    assert data["summary"]["section_verdicts"]["Data Volume Checks"] == "PASS"
    
    # Check Results Array
    assert len(data["results"]) == 3
    
    # Verify a specific result entry
    vol_check = next(r for r in data["results"] if r["name"] == "Volume Check")
    assert vol_check["status"] == "PASS"
    assert vol_check["metrics"]["src"] == 100
    assert vol_check["details"] is None
    
    fail_check = next(r for r in data["results"] if r["name"] == "Identity Check")
    assert fail_check["status"] == "FAIL"
    assert fail_check["details"]["mismatched_ids"] == [101, 102]

def test_json_report_empty_results(tmp_path):
    """Test JSON generation with an empty results list."""
    output_path = tmp_path / "Empty_Report.docx"
    paths = build_report([], output_path=str(output_path))
    
    with open(paths["json"], "r") as f:
        data = json.load(f)
        
    assert data["results"] == []
    assert data["summary"]["final_verdict"] == "NO-GO"  # Default for empty in current logic
    assert data["summary"]["section_verdicts"] == {}
