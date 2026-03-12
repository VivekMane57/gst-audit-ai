"""
state_codes.py
--------------
India ke saare GST state codes.
GSTIN ke pehle 2 digits = state code.
"""

STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman & Diu",
    "26": "Dadra & Nagar Haveli",
    "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre / Export",
}

VALID_STATE_CODES: frozenset[str] = frozenset(STATE_CODES.keys())


def get_state_name(code: str) -> str:
    return STATE_CODES.get(code, "Unknown State")


def is_valid_state_code(code: str) -> bool:
    return code in VALID_STATE_CODES


def is_interstate(seller_gstin: str, buyer_gstin: str) -> bool:
    """
    Returns True if transaction is inter-state.
    Inter-state = IGST lagta hai.
    Intra-state = CGST + SGST lagta hai.
    """
    if len(seller_gstin) < 2 or len(buyer_gstin) < 2:
        return False
    return seller_gstin[:2] != buyer_gstin[:2]


def is_export(buyer_gstin: str) -> bool:
    """GSTIN '99' prefix = export transaction."""
    return buyer_gstin[:2] == "99"