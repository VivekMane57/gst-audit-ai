"""
Quick OCR test — run this to see what data is extracted from invoice image
"""
from app.services.ocr_scanner import extract_invoice_from_image

# Invoice screenshot path
FILE_PATH = r"C:\Users\VICKY\OneDrive\Documents\Pictures\Screenshots 1\Screenshot 2026-03-23 100811.png"

with open(FILE_PATH, "rb") as f:
    result = extract_invoice_from_image(f.read())

print("=" * 50)
print("  OCR DETECTED DATA")
print("=" * 50)

fields = [
    ("Invoice Number", "invoice_number"),
    ("Date", "date"),
    ("Party Name", "party_name"),
    ("Party GSTIN", "party_gstin"),
    ("Taxable Value", "taxable_value"),
    ("IGST", "igst"),
    ("CGST", "cgst"),
    ("SGST", "sgst"),
    ("Total Amount", "total_amount"),
    ("HSN Code", "hsn_code"),
    ("Confidence", "ocr_confidence"),
]

for label, key in fields:
    val = result.get(key)
    if val is not None and val != 0 and val != "":
        status = "YES"
    else:
        status = "NO"
    print(f"  {label:20s}: {str(val):30s} [{status}]")

print()
print("=" * 50)
print("  RAW OCR TEXT (first 800 chars)")
print("=" * 50)
ocr_text = result.get("ocr_text", "")
print(ocr_text[:800])
print()
print(f"Total OCR text length: {len(ocr_text)} characters")