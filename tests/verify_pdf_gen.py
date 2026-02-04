
import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from reports.report_builder import build_report
from core.audit.result import TestResult
from core.audit.enums import CheckStatus

def create_dummy_logo(path):
    """Creates a simple dummy logo image."""
    width, height = 200, 100
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Draw a circle (Coral color)
    draw.ellipse((10, 10, 90, 90), fill='#FF7F50', outline=None)
    
    # Draw text
    try:
        # Try to load a default font, fallback if fails
        font = ImageFont.load_default()
    except IOError:
        font = None
        
    text = "CORAL"
    # Basic text drawing
    draw.text((100, 40), text, fill=(50, 50, 50))
    
    image.save(path)
    print(f"Dummy logo created at: {path}")

def run_verification():
    # Setup paths
    output_dir = os.path.join("tests", "verification_output")
    os.makedirs(output_dir, exist_ok=True)
    logo_path = os.path.join(output_dir, "dummy_logo.png")
    
    # Create logo
    create_dummy_logo(logo_path)
    
    # Create dummy results
    results = [
        TestResult(name="Legacy User Check", status=CheckStatus.PASS, message="No legacy users found."),
        TestResult(name="Weak Password Check", status=CheckStatus.FAIL, message="5 users found with weak passwords.", details="User IDs: 101, 102..."),
        TestResult(name="Encryption Check", status=CheckStatus.WARN, message="Encryption at rest verified but using old algorithm."),
        TestResult(name="Data Volume Consistency", status=CheckStatus.PASS, message="Row counts match."),
        TestResult(name="Orphaned Records", status=CheckStatus.FAIL, message="Found 150 orphaned records in Orders table."),
    ]
    
    print("Generating report...")
    # Call build_report with logo_path (Note: we need to modify build_report first to accept check this, 
    # but for now we call with extra arg to see it fail or just mock it)
    
    try:
        # Intentionally calling with keyword arg that might not exist yet to verify we're using the right version 
        # or plan the update.
        # Actually, let's call it normally first to ensure baseline works, then we modify.
        paths = build_report(
            results, 
            client="Acme Corp", 
            migration="On-Prem -> Cloud", 
            base_dir=output_dir,
            label="_verification",
            logo_path=logo_path
        )
        print("Report generated successfully (Baseline).")
        print(f"PDF: {paths['pdf']}")
        print(f"HTML: {paths['html']}")
        
    except Exception as e:
        print(f"Error during baseline generation: {e}")

if __name__ == "__main__":
    run_verification()
