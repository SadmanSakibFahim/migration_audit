import pytest
import os
import tempfile
import csv
from unittest.mock import patch, MagicMock
from core.schema_only.schema_converter import SchemaConverter
from core.schema_only.data_generator import DataGenerator
from core.schema_only.scenario_runner import ScenarioRunner
from core.audit.result import TestResult
from core.audit.enums import CheckStatus

def test_convert_to_config_sql():
    converter = SchemaConverter()
    sql_content = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        age INT,
        created_at DATE
    );
    """
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(sql_content)
        f_name = f.name
    
    try:
        config = converter.convert_to_config(f_name, format="sql")
        assert "users" in config["tables"]
        table = config["tables"]["users"]
        assert table["primary_key"] == "id"
        assert "age" in table["aggregates"]
        assert "not_null" in table["data_constraints"]["name"]
        assert "date" in table["data_constraints"]["created_at"]
    finally:
        os.unlink(f_name)

def test_convert_to_config_json():
    converter = SchemaConverter()
    json_content = """
    {
        "title": "users",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "created_at": {"type": "string", "format": "date"}
        },
        "required": ["name"]
    }
    """
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(json_content)
        f_name = f.name
        
    try:
        config = converter.convert_to_config(f_name, format="json")
        assert "users" in config["tables"]
        table = config["tables"]["users"]
        assert table["primary_key"] == "id"
        assert "not_null" in table["data_constraints"]["name"]
        assert "date" in table["data_constraints"]["created_at"]
    finally:
        os.unlink(f_name)

def test_convert_to_config_invalid_format():
    converter = SchemaConverter()
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("test")
        f_name = f.name
    try:
        with pytest.raises(ValueError):
            converter.convert_to_config(f_name, format="xml")
    finally:
        os.unlink(f_name)

def test_convert_to_config_invalid_json():
    converter = SchemaConverter()
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write("invalid json")
        f_name = f.name
    try:
        with pytest.raises(ValueError):
            converter.convert_to_config(f_name, format="json")
    finally:
        os.unlink(f_name)

def test_data_generator_generate():
    gen = DataGenerator()
    config = {
        "tables": {
            "users": {
                "source": "some_path.csv",
                "primary_key": "id",
                "data_constraints": {"name": ["not_null"], "created_at": ["date"]},
                "mappings": [{"columns": ["status"], "allowed_values": ["active", "inactive"]}]
            }
        }
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        files = gen.generate_data_for_config(config, tmpdir, row_count=5)
        assert len(files) == 2
        
        with open(files[0], "r") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 5
            for row in reader:
                assert "id" in row
                assert "name" in row
                assert "status" in row
                assert row["status"] in ["active", "inactive"]

def test_data_generator_heuristics():
    gen = DataGenerator()
    val_email = gen._generate_value("user_email", [], [])
    assert "@example.com" in val_email
    val_name = gen._generate_value("first_name", [], [])
    assert "Name_" in val_name
    val_price = gen._generate_value("item_price", [], [])
    assert isinstance(val_price, float)
    
@patch("core.schema_only.scenario_runner.SchemaConverter")
@patch("core.schema_only.scenario_runner.DataGenerator")
@patch("core.schema_only.scenario_runner.CheckRunner")
def test_scenario_runner(mock_runner, mock_gen, mock_conv):
    # Setup mocks
    mock_conv_instance = mock_conv.return_value
    mock_conv_instance.convert_to_config.return_value = {
        "tables": {
            "users": {
                "primary_key": "id"
            }
        }
    }
    
    mock_runner_instance = mock_runner.return_value
    mock_runner_instance.execute_all.return_value = [
        TestResult(name="Test1", status=CheckStatus.FAIL, message="error"),
        TestResult(name="Test2", status=CheckStatus.PASS, message="ok")
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = ScenarioRunner(temp_dir=tmpdir)
        # Mock the pandas read and to_csv to avoid file IO errors during apply_mutation
        with patch("pandas.read_csv", return_value=MagicMock()), \
             patch("pandas.DataFrame.to_csv"), \
             patch("core.schema_only.scenario_runner.os.path.exists", return_value=True):

            scenario_config = {
                "schema_path": "dummy.sql",
                "row_count": 5,
                "mutations": [
                    {"table": "users", "type": "delete_row", "count": 1},
                    {"table": "users", "type": "modify_value", "column": "name", "value": "x"},
                    {"table": "users", "type": "nullify_value", "column": "name"}
                ],
                "expected_failures": [{"check_name_contains": "Test1", "count": 1}]
            }
            
            res = runner.run_scenario(scenario_config)
            assert res["passed"] is True
            assert len(res["results"]) > 0
            
def test_scenario_runner_verify_results():
    runner = ScenarioRunner()
    results = [
        TestResult(name="Volume Check", status=CheckStatus.FAIL, message="error")
    ]
    # Match expected
    assert runner._verify_results(results, [{"check_name_contains": "Volume", "count": 1}]) is True
    # Missing expected
    assert runner._verify_results(results, [{"check_name_contains": "Aggregate", "count": 1}]) is False
    # No expected, but got failures
    assert runner._verify_results(results, []) is False
    # No expected, no failures
    assert runner._verify_results([TestResult(name="Ok", status=CheckStatus.PASS, message="ok")], []) is True
