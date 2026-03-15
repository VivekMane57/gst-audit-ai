"""
create_test_data.py
-------------------
Sample Excel files banao testing ke liye.
Run: python tests/create_test_data.py
"""
import pandas as pd
import os

os.makedirs("tests/sample_data", exist_ok=True)

# ── Purchase Register — with known issues ─────────────────────
purchase_data = [
    # Valid invoice
    {
        "Invoice No":     "PUR-001",
        "Party Name":     "Sharma Traders",
        "GSTIN":          "29AABCS1234R1Z5",   # Karnataka
        "Taxable Value":  100000,
        "IGST":           18000,                # Correct — inter-state
        "CGST":           0,
        "SGST":           0,
        "Invoice Date":   "01-01-2025",
        "In GSTR2B":      "Yes",
        "GSTR2B Amount":  18000,
    },
    # Issue: Not in GSTR-2B
    {
        "Invoice No":     "PUR-002",
        "Party Name":     "Ramesh Suppliers",
        "GSTIN":          "27XYZAB1234C1Z5",   # Maharashtra
        "Taxable Value":  50000,
        "IGST":           0,
        "CGST":           4500,                 # Correct — intra-state
        "SGST":           4500,
        "Invoice Date":   "05-01-2025",
        "In GSTR2B":      "No",                 # ❌ Not in 2B
        "GSTR2B Amount":  0,
    },
    # Issue: Amount mismatch
    {
        "Invoice No":     "PUR-003",
        "Party Name":     "Patel Industries",
        "GSTIN":          "24PQRST5678D1Z3",   # Gujarat
        "Taxable Value":  75000,
        "IGST":           13500,                # Books: 13500
        "CGST":           0,
        "SGST":           0,
        "Invoice Date":   "10-01-2025",
        "In GSTR2B":      "Yes",
        "GSTR2B Amount":  12000,                # ❌ 2B: 12000 — mismatch
    },
    # Issue: Duplicate
    {
        "Invoice No":     "PUR-001",            # ❌ Duplicate!
        "Party Name":     "Sharma Traders",
        "GSTIN":          "29AABCS1234R1Z5",
        "Taxable Value":  100000,
        "IGST":           18000,
        "CGST":           0,
        "SGST":           0,
        "Invoice Date":   "01-01-2025",
        "In GSTR2B":      "Yes",
        "GSTR2B Amount":  18000,
    },
    # Issue: Invalid GSTIN
    {
        "Invoice No":     "PUR-004",
        "Party Name":     "Unknown Vendor",
        "GSTIN":          "27INVALID123",       # ❌ Invalid GSTIN
        "Taxable Value":  25000,
        "IGST":           0,
        "CGST":           2250,
        "SGST":           2250,
        "Invoice Date":   "15-01-2025",
        "In GSTR2B":      "No",
        "GSTR2B Amount":  0,
    },
]

df_purchase = pd.DataFrame(purchase_data)
df_purchase.to_excel(
    "tests/sample_data/purchase_register_jan2025.xlsx",
    index=False
)
print("✅ purchase_register_jan2025.xlsx created")

# ── Sales Register — with GSTR-1 missing issue ───────────────
sales_data = [
    {
        "Invoice No":   "SAL-001",
        "Party Name":   "ABC Retail",
        "GSTIN":        "29ABCDE1234F1Z5",
        "Taxable Value": 200000,
        "IGST":          36000,
        "CGST":          0,
        "SGST":          0,
        "Invoice Date":  "03-01-2025",
        "In GSTR1":      "Yes",
    },
    {
        "Invoice No":   "SAL-002",
        "Party Name":   "XYZ Wholesale",
        "GSTIN":        "27WXYZ5678G1Z2",
        "Taxable Value": 150000,
        "IGST":          0,
        "CGST":          13500,
        "SGST":          13500,
        "Invoice Date":  "08-01-2025",
        "In GSTR1":      "No",              # ❌ Not filed in GSTR-1
    },
]

df_sales = pd.DataFrame(sales_data)
df_sales.to_excel(
    "tests/sample_data/sales_register_jan2025.xlsx",
    index=False
)
print("✅ sales_register_jan2025.xlsx created")
print("\nTest files ready in tests/sample_data/")
print("Expected issues:")
print("  Purchase: 1 duplicate, 1 GSTR-2B missing, 1 amount mismatch, 1 invalid GSTIN")
print("  Sales: 1 GSTR-1 missing")