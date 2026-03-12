"""
gstin_validator.py
------------------
GSTIN validation — 6 checks:
1. Empty check
2. Length = 15
3. Valid state code (first 2 digits)
4. PAN format (chars 3-12)
5. 14th char = Z
6. Regex pattern match

CGST Act Section 25, Rule 8 ke according.
"""
import re
from dataclasses import dataclass
from app.utils.state_codes import is_valid_state_code, get_state_name

# Official GSTIN pattern
_GSTIN_REGEX = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)


@dataclass
class GSTINResult:
    is_valid: bool
    error: str | None = None
    state_code: str | None = None
    state_name: str | None = None
    pan: str | None = None
    entity_number: str | None = None


def validate_gstin(gstin: str) -> GSTINResult:
    """
    Validate a GSTIN string.
    Returns GSTINResult with is_valid flag and error message if invalid.
    """
    if not gstin or not gstin.strip():
        return GSTINResult(is_valid=False, error="GSTIN empty hai")

    gstin = gstin.strip().upper()

    # Check 1: Length
    if len(gstin) != 15:
        return GSTINResult(
            is_valid=False,
            error=(
                f"GSTIN 15 characters ka hona chahiye — "
                f"aapka {len(gstin)} characters ka hai"
            ),
        )

    # Check 2: State code
    state_code = gstin[:2]
    if not is_valid_state_code(state_code):
        return GSTINResult(
            is_valid=False,
            error=f"Invalid state code: {state_code}",
        )

    # Check 3: PAN format (positions 2-11)
    pan = gstin[2:12]
    pan_regex = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
    if not pan_regex.match(pan):
        return GSTINResult(
            is_valid=False,
            error=f"Invalid PAN in GSTIN: {pan} — format hona chahiye AAAAA9999A",
        )

    # Check 4: 14th char must be Z
    if gstin[13] != "Z":
        return GSTINResult(
            is_valid=False,
            error="GSTIN ka 14th character 'Z' hona chahiye",
        )

    # Check 5: Full regex
    if not _GSTIN_REGEX.match(gstin):
        return GSTINResult(
            is_valid=False,
            error="GSTIN format invalid (correct format: 22AAAAA0000A1Z5)",
        )

    return GSTINResult(
        is_valid=True,
        state_code=state_code,
        state_name=get_state_name(state_code),
        pan=pan,
        entity_number=gstin[12],
    )


def mask_gstin(gstin: str) -> str:
    """
    27AABCS1234R1Z5 → 27**********1Z5
    Display ke liye — database mein full encrypted version store hoti hai.
    """
    if len(gstin) != 15:
        return "***"
    return f"{gstin[:2]}{'*' * 10}{gstin[12:]}"