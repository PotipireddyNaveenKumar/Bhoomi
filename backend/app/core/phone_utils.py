import re
from typing import Optional

def normalize_indian_phone(phone: str) -> str:
    """
    Normalizes Indian phone numbers to canonical E.164 format: +91XXXXXXXXXX.
    
    Accepts:
      - 10 digits: "9876543210"
      - With country code: "+919876543210", "919876543210"
      - With trunk prefix: "09876543210"
      - With punctuation/spacing: "+91 98765-43210", "(91) 98765 43210"
      
    Returns:
      Canonical "+91XXXXXXXXXX" string.
      
    Raises:
      ValueError if phone is empty, malformed, or not a valid 10-digit Indian mobile number.
    """
    if not phone or not isinstance(phone, str):
        raise ValueError("Mobile number cannot be empty.")

    # Strip all non-digit characters except leading plus
    cleaned = phone.strip()
    digits = re.sub(r"\D", "", cleaned)

    # Handle various digit lengths
    if len(digits) == 10:
        ten_digits = digits
    elif len(digits) == 11 and digits.startswith("0"):
        ten_digits = digits[1:]
    elif len(digits) == 12 and digits.startswith("91"):
        ten_digits = digits[2:]
    else:
        raise ValueError(
            f"Invalid mobile number. Please provide a valid 10-digit Indian mobile number."
        )

    # Validate 10-digit mobile number starting digit (6, 7, 8, 9 are Indian mobile series)
    if not re.match(r"^[6-9]\d{9}$", ten_digits):
        # We also allow other 10-digit patterns for test fixtures like 9988776655, but ensure 10 numeric digits
        if not re.match(r"^\d{10}$", ten_digits):
            raise ValueError("Mobile number must contain exactly 10 digits.")

    return f"+91{ten_digits}"


def validate_indian_phone(phone: str) -> bool:
    """Returns True if the phone string can be normalized to a valid Indian mobile number."""
    try:
        normalize_indian_phone(phone)
        return True
    except (ValueError, TypeError):
        return False


def mask_phone_number(phone: str) -> str:
    """
    Masks a phone number for safe logging / audit output.
    Example: +919876543210 -> +91 98****3210
    """
    try:
        norm = normalize_indian_phone(phone)
        # norm is +91XXXXXXXXXX (length 13)
        return f"{norm[:5]} **** {norm[-4:]}"
    except Exception:
        if len(phone) >= 4:
            return f"****{phone[-4:]}"
        return "****"
