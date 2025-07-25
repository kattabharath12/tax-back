import os
import re
from typing import Dict, Any, List

import pytesseract
from PIL import Image
from pdf2image import convert_from_path

W2_REGEX = {
    "employer_ein": re.compile(r"Employer.*EIN.*?(\d{2}-\d{7})", re.I),
    "wages": re.compile(r"1\s+wages.*?\$?([\d,\.]+)", re.I),
    "federal_withholding": re.compile(r"2\s+federal.*?\$?([\d,\.]+)", re.I),
}
NEC_REGEX = {
    "payer_tin": re.compile(r"PAYER.*TIN.*?(\d{2}-\d{7})", re.I),
    "nonemployee_compensation": re.compile(r"1\s+Nonemployee.*?\$?([\d,\.]+)", re.I),
}
W9_REGEX = {
    "taxpayer_id": re.compile(r"Part\s+I.*?TIN.*?(\d{2}-\d{7})", re.I)
}

def _images_from_file(path: str) -> List[Image.Image]:
    if path.lower().endswith(".pdf"):
        return convert_from_path(path, dpi=300)
    return [Image.open(path)]

def _ocr_text(path: str) -> str:
    text_segments = [pytesseract.image_to_string(img) for img in _images_from_file(path)]
    return "\n".join(text_segments)

def _extract_fields(text: str, patterns: Dict[str, re.Pattern]) -> Dict[str, Any]:
    data = {}
    for key, pat in patterns.items():
        match = pat.search(text)
        if match:
            raw = match.group(1).replace(",", "")
            data[key] = float(raw) if raw.replace(".", "").isdigit() else raw
    return data

def extract_document_data(file_path: str, content_type: str) -> Dict[str, Any]:
    text = _ocr_text(file_path)
    filename = os.path.basename(file_path).lower()

    if "w2" in filename or "w-2" in filename:
        data = _extract_fields(text, W2_REGEX)
        data["document_type"] = "W-2"
        return data
    if "1099" in filename:
        data = _extract_fields(text, NEC_REGEX)
        data["document_type"] = "1099-NEC"
        return data
    if "w9" in filename or "w-9" in filename:
        data = _extract_fields(text, W9_REGEX)
        data["document_type"] = "W-9"
        return data

    return {"document_type": "Unknown", "raw_text": text[:500]}
