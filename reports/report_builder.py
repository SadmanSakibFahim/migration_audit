import json
import os
import hashlib
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from core.audit.enums import CheckStatus
from core.audit.verdict import final_verdict

SECTION_MAP = {
    "volume": ("Data Volume Checks", ["volume"]),
    "identity": ("Identity Checks", ["identity", "primary key", "pk"]),
    "aggregates": (
        "Aggregate Checks",
        ["sum", "average", "avg", "max", "min", "variance", "aggregate"],
    ),
    "mappings": ("Mapping Checks", ["mapping"]),
    "relationships": ("Relationship Checks", ["foreign key", "relationship"]),
    "data_constraints": (
        "Data Constraint Checks",
        ["data constraint", "data constraints", "uniqueness"],
    ),
    "string": (
        "String Data Quality Checks",
        ["truncation", "whitespace", "encoding", "string"],
    ),
    "enum": (
        "Enum & Categorical Checks",
        ["enum", "categorical", "equivalence", "distribution"],
    ),
    "datetime": (
        "Datetime & Timezone Checks",
        ["datetime", "timezone", "tz"],
    ),
    "null_sentinel": (
        "Null & Sentinel Value Checks",
        ["null", "sentinel"],
    ),
    "numeric_precision": (
        "Numeric Precision Checks",
        ["precision", "scale", "numeric"],
    ),
    "boolean": ("Boolean Normalization Checks", ["boolean"]),
}

def get_content_hash(content: Dict[str, Any]) -> str:
    """Generate a canonical SHA-256 hash of the report content to ensure data integrity."""
    serializable = {
        "client": content["client"],
        "migration": content["migration"],
        "date": content["date"],
        "final_verdict": content["final_verdict"],
        "results": [
            {"name": r.name, "status": str(r.status.value) if hasattr(r.status, "value") else str(r.status), "message": r.message} 
            for r in content.get("all_results", [])
        ]
    }
    content_str = json.dumps(serializable, sort_keys=True)
    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()

def sign_report(file_path: str) -> str:
    """Generate a .sha256 signature file for a generated report."""
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        hasher.update(f.read())
    file_hash = hasher.hexdigest()
    with open(f"{file_path}.sha256", "w") as f:
        f.write(f"{file_hash} *{os.path.basename(file_path)}\n")
    return file_hash


def group_results(results: List[Any]) -> Dict[str, Dict[str, List[Any]]]:
    """Group results hierarchically with sub-group and target extraction."""
    hierarchical = defaultdict(lambda: defaultdict(list))

    for r in results:
        name_lower = r.name.lower()
        section_assigned = "General Checks"

        for key, (section_name, keywords) in SECTION_MAP.items():
            if any(kw in name_lower for kw in keywords):
                section_assigned = section_name
                break
        
        # Determine sub-group and extract target
        sub_group = "General"
        target = r.name
        if " check: " in name_lower:
            parts = r.name.split(" Check:", 1)
            sub_group = parts[0] + " Check"
            target = parts[1].lstrip(": ").strip()
        elif ":" in r.name:
            parts = r.name.split(":", 1)
            sub_group = parts[0].strip()
            target = parts[1].strip()
        
        # Attach temporary target attribute for the writers
        r._report_target = target
        hierarchical[section_assigned][sub_group].append(r)

    return hierarchical


def section_verdict(sub_groups: Dict[str, List[Any]]) -> str:
    """Compute verdict for a section based on its sub-groups."""
    all_results = [r for sub in sub_groups.values() for r in sub]
    if any(r.status == CheckStatus.FAIL for r in all_results):
        return "FAIL"
    if any(r.status == CheckStatus.WARN for r in all_results):
        return "WARN"
    return "PASS"


def _build_report_content(results: List[Any], client: str = "Client", migration: str = "Source → Target") -> Dict[str, Any]:
    """Build the core report content as a dictionary for reuse across formats."""
    grouped = group_results(results)
    final = final_verdict(results)

    content = {
        "client": client,
        "migration": migration,
        "date": str(date.today()),
        "final_verdict": final,
        "grouped_results": grouped,
        "all_results": results,
    }
    content["integrity_hash"] = get_content_hash(content)
    return content


def _write_json(content: Dict[str, Any], output_path: str) -> None:
    """Generate JSON report."""
    serializable = {
        "metadata": {
            "client": content["client"],
            "migration": content["migration"],
            "date": content["date"],
            "auditor": "Albatross Audit",
            "integrity_hash": content.get("integrity_hash", "")
        },
        "summary": {
            "final_verdict": content["final_verdict"],
            "section_verdicts": {
                section: section_verdict(sub_groups)
                for section, sub_groups in content["grouped_results"].items()
            }
        },
        "results": [
            {
                "name": r.name,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "message": r.message,
                "details": r.details,
                "metrics": r.metrics
            }
            for r in content.get("all_results", [])
        ]
    }
    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=4)


def build_report(
    results: List[Any],
    output_path: Optional[str] = None,
    client: str = "Client",
    migration: str = "Source → Target",
    base_dir: str = "outputs",
    label: str = "",
    logo_path: Optional[str] = None,
) -> Dict[str, str]:
    """Generate reports in JSON format.

    Args:
        results: List of TestResult objects
        output_path: Path for the file (base name). If None, generated automatically.
        client: Client name for the report
        migration: Migration description
        base_dir: Base directory for output (default: "outputs")
        label: Optional label to append to the timestamped folder (e.g., "_test")
        logo_path: Optional path to a logo image (PNG/JPG)
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_client = client.replace(" ", "_").lower()
        folder_name = f"{timestamp}_{safe_client}{label}"
        output_dir = os.path.join(base_dir, folder_name)
        os.makedirs(output_dir, exist_ok=True)
        # We default output_path to a base string that _write_json will use
        output_path = os.path.join(output_dir, "Audit_Report")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # Strip extension if provided so we can append .json
        output_path = os.path.splitext(output_path)[0]

    # Build report content once
    content = _build_report_content(results, client, migration)

    json_path = output_path + ".json"
    _write_json(content, json_path)

    paths = {
        "json": json_path,
    }
    
    for fmt, p in paths.items():
        sign_report(p)

    return paths
