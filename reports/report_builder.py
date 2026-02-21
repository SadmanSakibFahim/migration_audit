import base64
import os
from collections import defaultdict
from datetime import date, datetime

from docx import Document
from xhtml2pdf import pisa  # For PDF generation

from core.audit.enums import CheckStatus
from core.audit.verdict import final_verdict

SECTION_MAP = {
    "volume": ("Data Volume Checks", ["volume"]),
    "aggregates": (
        "Aggregate Checks",
        ["sum", "average", "avg", "max", "min", "variance"],
    ),
    "mappings": ("Mapping Checks", ["mapping"]),
    "relationships": ("Relationship Checks", ["foreign key"]),
    "data_constraints": (
        "Data Constraint Checks",
        ["data constraint", "data constraints"],
    ),
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
        "all_results": results,
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

    for section, res in content["grouped_results"].items():
        verdict = section_verdict(res)
        doc.add_paragraph(f"{section}: {verdict}")

    # Sections
    for section, res in content["grouped_results"].items():
        doc.add_heading(section, level=2)

        doc.add_paragraph("Checks Performed:")
        for r in res:
            doc.add_paragraph(f"- {r.name}", style="List Bullet")

        doc.add_paragraph("Findings:")
        for r in res:
            doc.add_paragraph(f"- [{r.status.value}] {r.message}", style="List Bullet")

        doc.add_paragraph(f"Section Verdict: {section_verdict(res)}")

    # Final Verdict
    doc.add_heading("Final Deployability Verdict", level=2)
    doc.add_paragraph(content["final_verdict"])

    doc.save(output_path)


def _write_markdown(content, output_path):
    """Generate Markdown report."""
    lines = []

    lines.append("# Migration Validation & Risk Audit\n")
    lines.append(f"**Client:** {content['client']}\n")
    lines.append(f"**Migration:** {content['migration']}\n")
    lines.append(f"**Audit Date:** {content['date']}\n")
    lines.append("**Auditor:** Independent Migration Audit\n")

    # Executive Summary
    lines.append("\n## Executive Summary\n")
    lines.append(f"**Final Verdict:** {content['final_verdict']}\n")

    for section, res in content["grouped_results"].items():
        verdict = section_verdict(res)
        lines.append(f"- **{section}:** {verdict}")

    # Detailed Sections
    for section, res in content["grouped_results"].items():
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

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


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
    lines.append("Auditor: Independent Migration Audit")
    lines.append("")

    # Executive Summary
    lines.append("-" * 80)
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Final Verdict: {content['final_verdict']}")
    lines.append("")

    for section, res in content["grouped_results"].items():
        verdict = section_verdict(res)
        lines.append(f"{section}: {verdict}")

    lines.append("")

    # Detailed Sections
    for section, res in content["grouped_results"].items():
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
    lines.append(content["final_verdict"])
    lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def _write_html(content, output_path, logo_path=None):
    """Generate HTML report."""

    # Handle Logo (Base64 Encode)
    logo_html = ""
    if logo_path and os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as img_file:
                b64_string = base64.b64encode(img_file.read()).decode("utf-8")
                # Determine mime type based on extension
                ext = os.path.splitext(logo_path)[1].lower().replace(".", "")
                mime_type = "image/png" if ext == "png" else "image/jpeg"
                logo_html = (
                    f'<img src="data:{mime_type};base64,{b64_string}" class="logo" />'
                )
        except Exception as e:
            print(f"Failed to load logo: {e}")

    html = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
                margin-bottom: 2.5cm;
                @frame footer_frame {{
                    -pdf-frame-content: footerContent;
                    bottom: 1cm;
                    margin-left: 2cm;
                    margin-right: 2cm;
                    height: 1cm;
                }}
            }}
            
            body {{ 
                font-family: Helvetica, Arial, sans-serif; 
                color: #2c3e50;
                line-height: 1.5;
            }}
            
            /* Footer Content (Hidden from normal flow, used by frame) */
            #footerContent {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 9pt;
                color: #7f8c8d;
                text-align: center;
                border-top: 1px solid #ecf0f1;
                padding-top: 5px;
            }}
            
            /* Header Section (Table used for layout) */
            .header-table {{
                width: 100%;
                border-bottom: 3px solid #FF7F50; /* Coral brand color */
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header-info {{ text-align: left; vertical-align: bottom; }}
            .header-logo {{ text-align: right; vertical-align: bottom; }}
            .logo {{ max-height: 60px; }}
            
            h1 {{ 
                color: #2c3e50; 
                font-size: 24pt; 
                margin: 0; padding: 0; 
            }}
            
            h2 {{ 
                color: #34495e; 
                border-bottom: 2px solid #FF7F50; 
                padding-bottom: 5px; 
                margin-top: 30px;
                font-size: 16pt;
            }}

            .meta-info {{ font-size: 10pt; color: #7f8c8d; }}
            
            /* Verdict Styles */
            .verdict-box {{
                background-color: #f8f9fa;
                border: 1px solid #bdc3c7;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                font-size: 14pt;
                text-align: center;
            }}
            
            .verdict-PASS {{ color: #27ae60; font-weight: bold; }}
            .verdict-WARN {{ color: #e67e22; font-weight: bold; }}
            .verdict-FAIL {{ color: #c0392b; font-weight: bold; }}
            
            /* Section Summary */
            .summary-table {{ width: 100%; margin-bottom: 20px; }}
            .summary-row td {{ padding: 5px; border-bottom: 1px solid #ecf0f1; }}
            
            /* Detailed Tables */
            .detail-table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-top: 10px; 
                font-size: 10pt;
            }}
            .detail-table th {{ 
                background-color: #ecf0f1; 
                color: #2c3e50; 
                padding: 8px; 
                text-align: left; 
                border-bottom: 2px solid #bdc3c7;
            }}
            .detail-table td {{ 
                border-bottom: 1px solid #ecf0f1; 
                padding: 8px; 
                vertical-align: top;
            }}
            
            /* Status Badges */
            .status-badge {{
                display: inline-block;
                padding: 2px 6px;
                border-radius: 4px;
                color: white;
                font-size: 8pt;
                font-weight: bold;
                text-align: center;
                min-width: 50px;
            }}
            .bg-PASS {{ background-color: #27ae60; }}
            .bg-WARN {{ background-color: #f39c12; }}
            .bg-FAIL {{ background-color: #e74c3c; }}
            .bg-ERROR {{ background-color: #c0392b; }}
            
            .footer-note {{
                color: #bdc3c7;
                font-size: 8pt;
                text-align: center;
                margin-top: 40px;
                border-top: 1px solid #ecf0f1;
                padding-top: 10px;
            }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <table class="header-table">
            <tr>
                <td class="header-info">
                    <h1>Migration Validation & Risk Audit</h1>
                    <div class="meta-info">
                        <strong>Client:</strong> {content['client']}<br/>
                        <strong>Migration:</strong> {content['migration']}<br/>
                        <strong>Date:</strong> {content['date']}<br/>
                        <strong>Auditor:</strong> Independent Migration Audit
                    </div>
                </td>
                <td class="header-logo">
                    {logo_html}
                </td>
            </tr>
        </table>

        <!-- Executive Summary -->
        <h2>Executive Summary</h2>
        <div class="verdict-box">
            Final Verdict: <span class="verdict-{content['final_verdict'].replace(' ', '-')}">{content['final_verdict']}</span>
        </div>
        
        <table class="summary-table">
    """

    for section, res in content["grouped_results"].items():
        verdict = section_verdict(res)
        html += f"""
            <tr class="summary-row">
                <td><strong>{section}</strong></td>
                <td style="text-align: right;"><span class="verdict-{verdict}">{verdict}</span></td>
            </tr>
        """

    html += """
        </table>
    """

    # Detailed Sections
    for section, res in content["grouped_results"].items():
        html += f"""
        <div class="section-block">
            <h2>{section}</h2>
            <table class="detail-table">
                <tr>
                    <th width="30%">Check Name</th>
                    <th width="15%">Status</th>
                    <th width="55%">Details</th>
                </tr>
        """
        for r in res:
            html += f"""
                <tr>
                    <td>{r.name}</td>
                    <td><span class="status-badge bg-{r.status.value}">{r.status.value}</span></td>
                    <td>
                        {r.message}
                        {f'<br/><small style="color:#7f8c8d">{r.details}</small>' if r.details else ''}
                    </td>
                </tr>
            """
        html += """
            </table>
        </div>
        """

    html += f"""
        <div style="page-break-before: always;"></div>
        <h2>Final Deployability Verdict</h2>
        <div class="verdict-box">
             <span class="verdict-{content['final_verdict'].replace(' ', '-')}">{content['final_verdict']}</span>
        </div>
        
        <div id="footerContent">
            Automatically generated by Coral &nbsp;|&nbsp; Page <pdf:pagenumber> of <pdf:pagecount>
        </div>
    </body>
    </html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
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


def build_report(
    results,
    output_path=None,
    client="Client",
    migration="Source → Target",
    base_dir="outputs",
    label="",
    logo_path=None,
):
    """Generate reports in all formats (DOCX, Markdown, Text, HTML, PDF).

    Args:
        results: List of TestResult objects
        output_path: Path for the DOCX file (base name). If None, generated automatically.
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
    # Pass logo_path to html generator
    html_content = _write_html(content, html_path, logo_path=logo_path)
    _write_pdf(html_content, pdf_path)

    return {
        "docx": output_path,
        "markdown": md_path,
        "text": txt_path,
        "html": html_path,
        "pdf": pdf_path,
    }
