import re
import unicodedata

SUFFIXES = [
    "- PRUDENCIAL",
    "(conglomerado)",
    "S.A.",
    "LTDA",
    "S/A",
]


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    value = value.strip().upper()
    for suffix in SUFFIXES:
        value = value.replace(suffix.upper(), "")
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ASCII", "ignore").decode("ASCII")
    value = re.sub(r"[^A-Z0-9 ]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_cnpj(value: str) -> str:
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    digits = re.sub(r"\D", "", value)
    digits = digits.lstrip("0")
    return digits
