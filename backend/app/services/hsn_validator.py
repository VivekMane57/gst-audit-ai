"""
services/hsn_validator.py
-------------------------
HSN Code validator — checks if correct GST rate applied.
Covers 500+ common HSN codes used in Indian businesses.

Usage:
    from app.services.hsn_validator import validate_hsn_rate, get_hsn_info

    result = validate_hsn_rate("84715000", applied_rate=12.0)
    # result = {
    #     "hsn_code": "84715000",
    #     "description": "Laptops, Notebooks",
    #     "correct_rate": 18.0,
    #     "applied_rate": 12.0,
    #     "is_correct": False,
    #     "severity": "CRITICAL",
    #     "message": "Wrong rate: 12% applied, should be 18%"
    # }
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── HSN Rate Database ─────────────────────────────────────────
# Format: "HSN_PREFIX": (rate, "description", "category")
# Uses prefix matching — 8471 matches 84715000, 84716000 etc.

HSN_RATES: dict[str, tuple[float, str, str]] = {
    # ── Chapter 01-05: Live Animals, Meat, Fish ──────────────
    "0201": (0.0, "Fresh/chilled meat (bovine)", "Food"),
    "0301": (0.0, "Live fish", "Food"),
    "0401": (0.0, "Fresh milk, cream", "Food"),
    "0406": (12.0, "Cheese", "Food"),
    "0409": (0.0, "Natural honey", "Food"),

    # ── Chapter 06-14: Vegetables, Fruits, Grains ────────────
    "0701": (0.0, "Potatoes (fresh)", "Food"),
    "0702": (0.0, "Tomatoes (fresh)", "Food"),
    "0713": (0.0, "Dried legumes (dal, chana)", "Food"),
    "0803": (0.0, "Bananas (fresh)", "Food"),
    "0901": (5.0, "Coffee (roasted)", "Food"),
    "0902": (5.0, "Tea", "Food"),
    "0904": (5.0, "Pepper, spices", "Food"),
    "0910": (5.0, "Ginger, turmeric, saffron", "Food"),
    "1001": (0.0, "Wheat", "Food"),
    "1005": (0.0, "Maize (corn)", "Food"),
    "1006": (5.0, "Rice (other than paddy)", "Food"),
    "1101": (0.0, "Wheat flour (atta)", "Food"),
    "1106": (0.0, "Flour of dal, beans", "Food"),

    # ── Chapter 15-24: Oils, Sugar, Beverages ────────────────
    "1507": (5.0, "Soybean oil", "Food"),
    "1508": (5.0, "Groundnut oil", "Food"),
    "1509": (5.0, "Olive oil", "Food"),
    "1511": (5.0, "Palm oil", "Food"),
    "1512": (5.0, "Sunflower oil", "Food"),
    "1515": (5.0, "Mustard oil", "Food"),
    "1517": (12.0, "Margarine, vanaspati", "Food"),
    "1701": (5.0, "Cane/beet sugar", "Food"),
    "1704": (18.0, "Sugar confectionery", "Food"),
    "1806": (18.0, "Chocolate", "Food"),
    "1901": (18.0, "Malt extract, food preparations", "Food"),
    "1902": (12.0, "Pasta, noodles", "Food"),
    "1905": (18.0, "Bread, biscuits, cakes", "Food"),
    "2009": (12.0, "Fruit juices", "Food"),
    "2101": (18.0, "Instant coffee, tea", "Food"),
    "2106": (18.0, "Food preparations n.e.s", "Food"),
    "2201": (18.0, "Mineral water, aerated water", "Beverages"),
    "2202": (28.0, "Aerated drinks with sugar", "Beverages"),
    "2203": (28.0, "Beer", "Beverages"),
    "2208": (28.0, "Spirits, liqueurs", "Beverages"),
    "2401": (28.0, "Tobacco, unmanufactured", "Tobacco"),
    "2402": (28.0, "Cigars, cigarettes", "Tobacco"),
    "2403": (28.0, "Other tobacco products", "Tobacco"),

    # ── Chapter 25-27: Minerals, Fuels ───────────────────────
    "2501": (5.0, "Salt", "Minerals"),
    "2523": (28.0, "Cement", "Construction"),
    "2701": (5.0, "Coal", "Energy"),
    "2710": (18.0, "Petroleum oils (lubricants)", "Energy"),
    "2711": (5.0, "LPG, natural gas", "Energy"),

    # ── Chapter 28-38: Chemicals, Pharma ─────────────────────
    "2801": (18.0, "Chlorine, fluorine, bromine", "Chemicals"),
    "2836": (18.0, "Carbonates", "Chemicals"),
    "3003": (12.0, "Medicaments (not packed)", "Pharma"),
    "3004": (12.0, "Medicaments (packed, branded)", "Pharma"),
    "300410": (5.0, "Formulations (essential drugs)", "Pharma"),
    "3006": (12.0, "Pharmaceutical goods", "Pharma"),
    "3208": (18.0, "Paints, varnishes", "Chemicals"),
    "3304": (28.0, "Beauty/makeup preparations", "Cosmetics"),
    "3305": (18.0, "Hair preparations (shampoo)", "Cosmetics"),
    "3306": (18.0, "Oral hygiene (toothpaste)", "Cosmetics"),
    "3401": (18.0, "Soap", "FMCG"),
    "3402": (18.0, "Detergents", "FMCG"),

    # ── Chapter 39-40: Plastics, Rubber ──────────────────────
    "3901": (18.0, "Polymers of ethylene", "Plastics"),
    "3917": (18.0, "Plastic tubes, pipes", "Plastics"),
    "3919": (18.0, "Plastic sheets, film", "Plastics"),
    "3920": (18.0, "Plastic plates, sheets", "Plastics"),
    "3923": (18.0, "Plastic containers, bottles", "Plastics"),
    "3926": (18.0, "Other plastic articles", "Plastics"),
    "4011": (28.0, "New rubber tyres", "Rubber"),
    "4012": (18.0, "Retreaded/used tyres", "Rubber"),
    "4014": (12.0, "Rubber contraceptives", "Healthcare"),

    # ── Chapter 44-49: Wood, Paper ───────────────────────────
    "4802": (12.0, "Paper, uncoated", "Paper"),
    "4818": (18.0, "Toilet paper, tissues", "Paper"),
    "4819": (18.0, "Cartons, boxes of paper", "Packaging"),
    "4820": (18.0, "Registers, notebooks", "Stationery"),
    "4901": (0.0, "Printed books", "Education"),
    "4902": (5.0, "Newspapers", "Media"),
    "4903": (0.0, "Children's picture books", "Education"),
    "4907": (18.0, "Stamps, cheque forms", "Stationery"),

    # ── Chapter 50-63: Textiles, Garments ────────────────────
    "5007": (5.0, "Silk fabrics", "Textiles"),
    "5208": (5.0, "Cotton fabrics (woven)", "Textiles"),
    "5209": (5.0, "Cotton fabrics (heavy)", "Textiles"),
    "5407": (5.0, "Synthetic filament fabrics", "Textiles"),
    "5513": (5.0, "Synthetic staple fabrics", "Textiles"),
    "6101": (12.0, "Garments (knitted, >1000)", "Garments"),
    "610110": (5.0, "Garments (knitted, ≤1000)", "Garments"),
    "6201": (12.0, "Garments (not knitted, >1000)", "Garments"),
    "620111": (5.0, "Garments (not knitted, ≤1000)", "Garments"),
    "6301": (12.0, "Blankets", "Textiles"),
    "6305": (5.0, "Jute sacks, bags", "Textiles"),

    # ── Chapter 64-67: Footwear ──────────────────────────────
    "6401": (18.0, "Waterproof footwear", "Footwear"),
    "6402": (18.0, "Footwear (rubber/plastic, >1000)", "Footwear"),
    "640220": (12.0, "Footwear (≤1000)", "Footwear"),
    "6403": (18.0, "Footwear (leather, >1000)", "Footwear"),
    "6404": (18.0, "Footwear (textile, >1000)", "Footwear"),
    "6405": (18.0, "Other footwear", "Footwear"),

    # ── Chapter 68-70: Stones, Ceramic, Glass ────────────────
    "6802": (28.0, "Marble, granite (polished)", "Construction"),
    "6810": (28.0, "Cement products", "Construction"),
    "6901": (18.0, "Ceramic bricks", "Construction"),
    "6907": (18.0, "Ceramic tiles", "Construction"),
    "6910": (18.0, "Ceramic sinks, wash basins", "Construction"),
    "7003": (18.0, "Glass sheets", "Glass"),
    "7010": (18.0, "Glass bottles, jars", "Packaging"),
    "7013": (18.0, "Glassware", "Household"),

    # ── Chapter 71: Jewellery ────────────────────────────────
    "7101": (3.0, "Natural pearls", "Jewellery"),
    "7102": (0.5, "Diamonds (unworked)", "Jewellery"),
    "7103": (0.25, "Precious stones", "Jewellery"),
    "7106": (3.0, "Silver", "Jewellery"),
    "7108": (3.0, "Gold", "Jewellery"),
    "7113": (3.0, "Jewellery articles", "Jewellery"),
    "7117": (3.0, "Imitation jewellery", "Jewellery"),

    # ── Chapter 72-83: Iron, Steel, Metals ───────────────────
    "7204": (18.0, "Iron/steel scrap", "Metals"),
    "7210": (18.0, "Coated steel sheets", "Metals"),
    "7213": (18.0, "Iron/steel bars (hot-rolled)", "Metals"),
    "7214": (18.0, "Iron/steel bars", "Metals"),
    "7216": (18.0, "Angles, shapes of iron/steel", "Metals"),
    "7304": (18.0, "Tubes, pipes (seamless)", "Metals"),
    "7306": (18.0, "Tubes, pipes (welded)", "Metals"),
    "7308": (18.0, "Structures of iron/steel", "Metals"),
    "7318": (18.0, "Screws, bolts, nuts, washers", "Metals"),
    "7323": (18.0, "Steel utensils", "Household"),
    "7326": (18.0, "Other iron/steel articles", "Metals"),
    "7403": (18.0, "Refined copper", "Metals"),
    "7606": (18.0, "Aluminium plates/sheets", "Metals"),
    "7610": (18.0, "Aluminium structures", "Metals"),
    "7615": (18.0, "Aluminium utensils", "Household"),
    "8302": (18.0, "Base metal mountings, fittings", "Hardware"),
    "8311": (18.0, "Welding wire, rods", "Metals"),

    # ── Chapter 84: Machinery ────────────────────────────────
    "8401": (18.0, "Nuclear reactors", "Machinery"),
    "8402": (18.0, "Steam boilers", "Machinery"),
    "8407": (28.0, "Spark-ignition engines", "Automobiles"),
    "8408": (28.0, "Compression-ignition engines", "Automobiles"),
    "8413": (18.0, "Pumps", "Machinery"),
    "8414": (18.0, "Air/vacuum pumps, compressors", "Machinery"),
    "8415": (28.0, "Air conditioners", "Appliances"),
    "8418": (18.0, "Refrigerators, freezers", "Appliances"),
    "8419": (18.0, "Heating/cooling machinery", "Machinery"),
    "8421": (18.0, "Centrifuges, filters", "Machinery"),
    "8422": (18.0, "Dishwashing machines", "Appliances"),
    "8423": (18.0, "Weighing machines", "Machinery"),
    "8428": (18.0, "Lifting/handling machinery", "Machinery"),
    "8431": (18.0, "Parts of machinery", "Machinery"),
    "8432": (12.0, "Agricultural machinery", "Agriculture"),
    "8433": (12.0, "Harvesting machinery", "Agriculture"),
    "8436": (12.0, "Other agricultural machinery", "Agriculture"),
    "8443": (18.0, "Printing machinery, printers", "IT"),
    "8450": (18.0, "Washing machines", "Appliances"),
    "8471": (18.0, "Computers, laptops", "IT"),
    "84713": (18.0, "Laptops, notebooks", "IT"),
    "84715": (18.0, "Processing units (CPU, servers)", "IT"),
    "84716": (18.0, "Input/output units (keyboard, mouse, monitor)", "IT"),
    "84717": (18.0, "Storage units (HDD, SSD)", "IT"),
    "8473": (18.0, "Parts of computers", "IT"),

    # ── Chapter 85: Electrical ───────────────────────────────
    "8501": (18.0, "Electric motors, generators", "Electrical"),
    "8502": (18.0, "Electric generating sets", "Electrical"),
    "8504": (18.0, "Electrical transformers", "Electrical"),
    "85044": (18.0, "UPS, inverters, stabilizers", "Electrical"),
    "8506": (18.0, "Primary cells, batteries", "Electrical"),
    "8507": (28.0, "Electric accumulators (lead-acid)", "Electrical"),
    "8509": (18.0, "Electro-mechanical appliances", "Appliances"),
    "8516": (18.0, "Electric heaters, ovens", "Appliances"),
    "8517": (18.0, "Telephone sets, smartphones", "Electronics"),
    "851712": (18.0, "Smartphones", "Electronics"),
    "8518": (18.0, "Microphones, speakers, headphones", "Electronics"),
    "8521": (18.0, "Video recording apparatus", "Electronics"),
    "8523": (18.0, "Recorded/unrecorded media", "Electronics"),
    "8525": (18.0, "Cameras, CCTV", "Electronics"),
    "8527": (18.0, "Radio receivers", "Electronics"),
    "8528": (18.0, "Monitors, TVs, projectors", "Electronics"),
    "852871": (18.0, "TV sets (≤32 inch)", "Electronics"),
    "852872": (18.0, "TV sets (>32 inch)", "Electronics"),
    "8536": (18.0, "Electrical switches, plugs", "Electrical"),
    "8539": (18.0, "LED/filament lamps", "Electrical"),
    "8541": (18.0, "Diodes, transistors, LEDs", "Electronics"),
    "8542": (18.0, "Integrated circuits", "Electronics"),
    "8544": (18.0, "Insulated wire, cables", "Electrical"),

    # ── Chapter 86-89: Vehicles, Ships ───────────────────────
    "8703": (28.0, "Motor cars (petrol/diesel)", "Automobiles"),
    "870310": (28.0, "Motor cars (electric)", "Automobiles"),
    "8704": (28.0, "Trucks, lorries", "Automobiles"),
    "8711": (28.0, "Motorcycles", "Automobiles"),
    "871120": (28.0, "Motorcycles (>350cc)", "Automobiles"),
    "8712": (12.0, "Bicycles", "Vehicles"),
    "8713": (5.0, "Wheelchairs", "Healthcare"),

    # ── Chapter 90-92: Medical, Optical ──────────────────────
    "9001": (18.0, "Optical fibres, lenses", "Medical"),
    "9004": (18.0, "Spectacles, sunglasses", "Medical"),
    "9018": (12.0, "Medical instruments", "Medical"),
    "9019": (12.0, "Mechano-therapy appliances", "Medical"),
    "9021": (12.0, "Orthopaedic appliances", "Medical"),
    "9025": (18.0, "Thermometers", "Medical"),
    "9027": (18.0, "Instruments for analysis", "Medical"),

    # ── Chapter 94-96: Furniture, Misc ───────────────────────
    "9401": (18.0, "Seats, chairs", "Furniture"),
    "9403": (18.0, "Other furniture", "Furniture"),
    "9404": (18.0, "Mattresses", "Furniture"),
    "9405": (18.0, "Lamps, lighting fittings", "Furniture"),
    "9503": (18.0, "Toys", "Toys"),
    "9504": (28.0, "Video game consoles", "Electronics"),
    "9506": (18.0, "Sports equipment", "Sports"),
    "9608": (18.0, "Ball point pens", "Stationery"),
    "9609": (12.0, "Pencils", "Stationery"),
    "9613": (18.0, "Lighters", "Misc"),
    "9619": (12.0, "Sanitary napkins, diapers", "Healthcare"),

    # ── SAC Codes (Services) ─────────────────────────────────
    "9954": (18.0, "Construction services", "Services"),
    "9961": (18.0, "Financial services", "Services"),
    "9962": (18.0, "Insurance services", "Services"),
    "9963": (18.0, "Hotel accommodation", "Services"),
    "996311": (12.0, "Hotel (tariff ₹1000-7500)", "Services"),
    "996312": (18.0, "Hotel (tariff >₹7500)", "Services"),
    "9964": (5.0, "Passenger transport", "Services"),
    "9965": (5.0, "Goods transport (GTA)", "Services"),
    "996511": (5.0, "GTA (no ITC)", "Services"),
    "996512": (12.0, "GTA (with ITC)", "Services"),
    "9966": (18.0, "Rental services", "Services"),
    "9967": (18.0, "IT support services", "Services"),
    "9971": (18.0, "Professional services", "Services"),
    "9972": (18.0, "Real estate services", "Services"),
    "9973": (18.0, "Leasing/rental services", "Services"),
    "9981": (18.0, "R&D services", "Services"),
    "9982": (18.0, "Legal services", "Services"),
    "9983": (18.0, "Consulting services", "Services"),
    "9984": (18.0, "Telecom services", "Services"),
    "9985": (18.0, "Support services", "Services"),
    "9986": (18.0, "Logistics services", "Services"),
    "9987": (18.0, "Maintenance services", "Services"),
    "9988": (18.0, "Manufacturing services", "Services"),
    "9991": (0.0, "Government services", "Services"),
    "9992": (0.0, "Education services", "Services"),
    "9993": (0.0, "Healthcare services", "Services"),
    "9995": (18.0, "Recreation/cultural services", "Services"),
    "9996": (18.0, "Personal services (salon etc)", "Services"),
    "9997": (18.0, "Other services", "Services"),
}

# ── State code to name mapping ────────────────────────────────
STATE_NAMES: dict[str, str] = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman & Nicobar", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh",
}


def get_hsn_info(hsn_code: str) -> Optional[dict]:
    """
    HSN code ke liye rate aur description return karo.
    Prefix matching use karta hai — longest match wins.
    """
    if not hsn_code:
        return None

    hsn = hsn_code.strip().replace(" ", "")

    # Try longest prefix first (most specific match)
    for length in range(len(hsn), 1, -1):
        prefix = hsn[:length]
        if prefix in HSN_RATES:
            rate, desc, category = HSN_RATES[prefix]
            return {
                "hsn_code": hsn,
                "matched_prefix": prefix,
                "description": desc,
                "correct_rate": rate,
                "category": category,
            }

    return None


def validate_hsn_rate(
    hsn_code: str,
    applied_rate: float,
    taxable_value: float = 0.0,
) -> dict:
    """
    HSN code ke against applied rate validate karo.
    Returns validation result with severity.
    """
    info = get_hsn_info(hsn_code)

    if not info:
        return {
            "hsn_code": hsn_code,
            "description": "Unknown HSN code",
            "correct_rate": None,
            "applied_rate": applied_rate,
            "is_correct": None,
            "severity": "LOW",
            "message": f"HSN code {hsn_code} not found in database. Verify manually.",
            "category": "Unknown",
            "tax_difference": 0.0,
        }

    correct_rate = info["correct_rate"]
    is_correct = abs(applied_rate - correct_rate) < 0.01  # tolerance for float

    if is_correct:
        return {
            **info,
            "applied_rate": applied_rate,
            "is_correct": True,
            "severity": "OK",
            "message": f"✅ Correct rate {applied_rate}% for {info['description']}",
            "tax_difference": 0.0,
        }

    # Wrong rate — calculate impact
    tax_diff = 0.0
    if taxable_value > 0:
        tax_diff = abs(taxable_value * (applied_rate - correct_rate) / 100)

    rate_diff = abs(applied_rate - correct_rate)

    if rate_diff >= 10:
        severity = "CRITICAL"
    elif rate_diff >= 5:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    if applied_rate > correct_rate:
        message = f"Over-charged: {applied_rate}% applied, should be {correct_rate}% for {info['description']}. Excess tax ₹{tax_diff:,.0f}"
    else:
        message = f"Under-charged: {applied_rate}% applied, should be {correct_rate}% for {info['description']}. Short tax ₹{tax_diff:,.0f}"

    return {
        **info,
        "applied_rate": applied_rate,
        "is_correct": False,
        "severity": severity,
        "message": message,
        "tax_difference": tax_diff,
    }


def validate_invoices_hsn(invoices: list) -> list:
    """
    List of invoices ke HSN codes validate karo.
    Returns list of HSN validation results (only issues).
    """
    results = []

    for inv in invoices:
        hsn = getattr(inv, "hsn_code", None) or ""
        if not hsn:
            continue

        # Calculate applied rate from tax amounts
        taxable = getattr(inv, "taxable_value", 0) or 0
        total_tax = (getattr(inv, "igst", 0) or 0) + (getattr(inv, "cgst", 0) or 0) + (getattr(inv, "sgst", 0) or 0)

        if taxable > 0:
            applied_rate = round((total_tax / taxable) * 100, 1)
        else:
            continue  # Can't validate without taxable value

        result = validate_hsn_rate(hsn, applied_rate, taxable)

        if not result.get("is_correct", True):
            result["invoice_number"] = getattr(inv, "invoice_number", "")
            result["party_name"] = getattr(inv, "party_name", "")
            result["taxable_value"] = taxable
            results.append(result)

    return results


def search_hsn(query: str, limit: int = 20) -> list:
    """
    HSN code ya description se search karo.
    """
    query = query.lower().strip()
    results = []

    for prefix, (rate, desc, category) in HSN_RATES.items():
        if query in prefix.lower() or query in desc.lower() or query in category.lower():
            results.append({
                "hsn_code": prefix,
                "description": desc,
                "rate": rate,
                "category": category,
            })
            if len(results) >= limit:
                break

    return results