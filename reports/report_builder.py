from docx import Document
from datetime import date, datetime
from collections import defaultdict
from core.verdict import final_verdict
from core.enums import CheckStatus
import os

SECTION_MAP = {
    "volume": ("Data Volume Checks", ["volume"]),
    "aggregates": ("Aggregate Checks", ["sum", "average", "avg", "max", "min", "variance"]),
    "mappings": ("Mapping Checks", ["mapping"]),
    "relationships": ("Relationship Checks", ["foreign key"]),
    "data_constraints": ("Data Constraint Checks", ["data constraint", "data constraints"])
}

def group_results(results):
    grouped = defaultdict(list)

    for r in results:
        name_lower = r.name.lower()
        found = False
        
        for key, (section_name, keywords) in SECTION_MAP.items():
            for keyword in keywords:
                if keyword in name_lower:
                    grouped[section_name].append(r)
                    found = True
                    break
            if found:
                break
        
        # If no section matched, try to group by key name as fallback
        if not found:
            for key, (section_name, keywords) in SECTION_MAP.items():
                if key in name_lower:
                    grouped[section_name].append(r)
                    break

    return grouped

def section_verdict(results):
    if any(r.status == CheckStatus.FAIL for r in results):
        return "FAIL"
    if any(r.status == CheckStatus.WARN for r in results):
        return "WARN"
    return "PASS"

def _build_report_content(results, client="Client", migration="Source → Target"):
    """Build the core report content as a dictionary for reuse across formats."""
    grouped = group_results(results)
    final = final_verdict(results)
    
    return {
        "client": client,
        "migration": migration,
        "date": str(date.today()),
        "final_verdict": final,
        "grouped_results": grouped,
        "all_results": results
    }

def _write_docx(content, output_path):
    """Generate DOCX report."""
    doc = Document()

    # Title
    doc.add_heading("Migration Validation & Risk Audit", level=1)

    doc.add_paragraph(
        f"Client: {content['client']}\n"
        f"Migration: {content['migration']}\n"
        f"Audit Date: {content['date']}\n"
        f"Auditor: Independent Migration Audit"
    )

    # Executive Summary
    doc.add_heading("Executive Summary", level=2)

    doc.add_paragraph(f"Final Verdict: {content['final_verdict']}\n")

    for section, res in content['grouped_results'].items():
        verdict = section_verdict(res)
        doc.add_paragraph(f"{section}: {verdict}")

    # Sections
    for section, res in content['grouped_results'].items():
        doc.add_heading(section, level=2)

        doc.add_paragraph("Checks Performed:")
        for r in res:
            doc.add_paragraph(f"- {r.name}", style="List Bullet")

        doc.add_paragraph("Findings:")
        for r in res:
            doc.add_paragraph(
                f"- [{r.status.value}] {r.message}",
                style="List Bullet"
            )

        doc.add_paragraph(f"Section Verdict: {section_verdict(res)}")

    # Final Verdict
    doc.add_heading("Final Deployability Verdict", level=2)
    doc.add_paragraph(content['final_verdict'])

    doc.save(output_path)

def _write_markdown(content, output_path):
    """Generate Markdown report."""
    lines = []
    
    lines.append("# Migration Validation & Risk Audit\n")
    lines.append(f"**Client:** {content['client']}\n")
    lines.append(f"**Migration:** {content['migration']}\n")
    lines.append(f"**Audit Date:** {content['date']}\n")
    lines.append(f"**Auditor:** Independent Migration Audit\n")
    
    # Executive Summary
    lines.append("\n## Executive Summary\n")
    lines.append(f"**Final Verdict:** {content['final_verdict']}\n")
    
    for section, res in content['grouped_results'].items():
        verdict = section_verdict(res)
        lines.append(f"- **{section}:** {verdict}")
    
    # Detailed Sections
    for section, res in content['grouped_results'].items():
        lines.append(f"\n## {section}\n")
        
        lines.append("### Checks Performed\n")
        for r in res:
            lines.append(f"- {r.name}")
        
        lines.append("\n### Findings\n")
        for r in res:
            lines.append(f"- **[{r.status.value}]** {r.message}")
            if r.details:
                lines.append(f"  - Details: {r.details}")
        
        lines.append(f"\n**Section Verdict:** {section_verdict(res)}\n")
    
    # Final Verdict
    lines.append("\n## Final Deployability Verdict\n")
    lines.append(f"{content['final_verdict']}\n")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

def _write_text(content, output_path):
    """Generate plain text report."""
    lines = []
    
    lines.append("=" * 80)
    lines.append("MIGRATION VALIDATION & RISK AUDIT")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Client:  {content['client']}")
    lines.append(f"Migration: {content['migration']}")
    lines.append(f"Audit Date: {content['date']}")
    lines.append(f"Auditor: Independent Migration Audit")
    lines.append("")
    
    # Executive Summary
    lines.append("-" * 80)
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Final Verdict: {content['final_verdict']}")
    lines.append("")
    
    for section, res in content['grouped_results'].items():
        verdict = section_verdict(res)
        lines.append(f"{section}: {verdict}")
    
    lines.append("")
    
    # Detailed Sections
    for section, res in content['grouped_results'].items():
        lines.append("-" * 80)
        lines.append(section.upper())
        lines.append("-" * 80)
        lines.append("")
        
        lines.append("Checks Performed:")
        for r in res:
            lines.append(f"  - {r.name}")
        
        lines.append("")
        lines.append("Findings:")
        for r in res:
            lines.append(f"  [{r.status.value}] {r.message}")
            if r.details:
                lines.append(f"       Details: {r.details}")
        
        lines.append("")
        lines.append(f"Section Verdict: {section_verdict(res)}")
        lines.append("")
    
    # Final Verdict
    lines.append("=" * 80)
    lines.append("FINAL DEPLOYABILITY VERDICT")
    lines.append("=" * 80)
    lines.append(content['final_verdict'])
    lines.append("")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

def build_report(results, output_path=None, client="Client", migration="Source → Target"):
    """Generate reports in all formats (DOCX, Markdown, and Text).
    
    Args:
        results: List of TestResult objects
        output_path: Path for the DOCX file (base name). If None, defaults to outputs/<timestamp>/Audit_Report.docx
        client: Client name for the report
        migration: Migration description
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("outputs", timestamp + '_' + client) # drop spaces and special characters from client and migration
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "Audit_Report.docx")
    # Build report content once
    content = _build_report_content(results, client, migration)
    
    # Generate DOCX
    _write_docx(content, output_path)
    
    # Generate Markdown and Text files with same base name
    base_path = os.path.splitext(output_path)[0]
    md_path = base_path + ".md"
    txt_path = base_path + ".txt"
    
    _write_markdown(content, md_path)
    _write_text(content, txt_path)
    
    return {
        "docx": output_path,
        "markdown": md_path,
        "text": txt_path
    }
