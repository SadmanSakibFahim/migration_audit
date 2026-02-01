from docx import Document
from datetime import date, datetime
from collections import defaultdict
from core.verdict import final_verdict
from core.enums import CheckStatus
import os
from xhtml2pdf import pisa  # For PDF generation

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

def _write_html(content, output_path):
    """Generate HTML report."""
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
            .verdict {{ font-weight: bold; font-size: 1.2em; }}
            .verdict-PASS {{ color: #27ae60; }}
            .verdict-WARN {{ color: #f39c12; }}
            .verdict-FAIL {{ color: #c0392b; }}
            .section {{ margin-bottom: 30px; }}
            .check-item {{ margin: 5px 0; }}
            .status-PASS {{ color: green; font-weight: bold; }}
            .status-WARN {{ color: orange; font-weight: bold; }}
            .status-FAIL {{ color: red; font-weight: bold; }}
            .status-ERROR {{ color: darkred; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Migration Validation & Risk Audit</h1>
        <p>
            <strong>Client:</strong> {content['client']}<br>
            <strong>Migration:</strong> {content['migration']}<br>
            <strong>Audit Date:</strong> {content['date']}<br>
            <strong>Auditor:</strong> Independent Migration Audit
        </p>

        <h2>Executive Summary</h2>
        <p class="verdict">Final Verdict: <span class="verdict-{content['final_verdict'].replace(' ', '-')}">{content['final_verdict']}</span></p>
        
        <ul>
    """
    
    for section, res in content['grouped_results'].items():
        verdict = section_verdict(res)
        html += f"<li><strong>{section}:</strong> {verdict}</li>"
    
    html += "</ul>"
    
    # Detailed Sections
    for section, res in content['grouped_results'].items():
        html += f"""
        <div class="section">
            <h2>{section}</h2>
            <table>
                <tr>
                    <th>Check Name</th>
                    <th>Status</th>
                    <th>Message</th>
                </tr>
        """
        for r in res:
            html += f"""
                <tr>
                    <td>{r.name}</td>
                    <td><span class="status-{r.status.value}">{r.status.value}</span></td>
                    <td>{r.message}</td>
                </tr>
            """
        html += """
            </table>
        </div>
        """
        
    html += f"""
        <h2>Final Deployability Verdict</h2>
        <p class="verdict verdict-{content['final_verdict'].replace(' ', '-')}">{content['final_verdict']}</p>
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return html

def _write_pdf(html_content, output_path):
    """Generate PDF report from HTML content using xhtml2pdf."""
    try:
        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
        
        if pisa_status.err:
            print(f"Error generating PDF: {pisa_status.err}")
    except Exception as e:
        print(f"Failed to generate PDF: {e}")

def build_report(results, output_path=None, client="Client", migration="Source → Target", base_dir="outputs", label=""):
    """Generate reports in all formats (DOCX, Markdown, Text, HTML, PDF).
    
    Args:
        results: List of TestResult objects
        output_path: Path for the DOCX file (base name). If None, generated automatically.
        client: Client name for the report
        migration: Migration description
        base_dir: Base directory for output (default: "outputs")
        label: Optional label to append to the timestamped folder (e.g., "_test")
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_client = client.replace(" ", "_").lower()
        folder_name = f"{timestamp}_{safe_client}{label}"
        output_dir = os.path.join(base_dir, folder_name)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "Audit_Report.docx")
    else:
        # If output_path is provided, ensure its directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Build report content once
    content = _build_report_content(results, client, migration)
    
    # Generate DOCX
    _write_docx(content, output_path)
    
    # Generate Markdown, Text, HTML, PDF
    base_path = os.path.splitext(output_path)[0]
    md_path = base_path + ".md"
    txt_path = base_path + ".txt"
    html_path = base_path + ".html"
    pdf_path = base_path + ".pdf"
    
    _write_markdown(content, md_path)
    _write_text(content, txt_path)
    html_content = _write_html(content, html_path)
    _write_pdf(html_content, pdf_path)
    
    return {
        "docx": output_path,
        "markdown": md_path,
        "text": txt_path,
        "html": html_path,
        "pdf": pdf_path
    }
