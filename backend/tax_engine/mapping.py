from typing import Dict, Any

def map_document_to_form1040(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the fields Form 1040 cares about."""
    if extracted.get("document_type") == "W-2":
        return {
            "wages": extracted.get("wages", 0),
            "federal_withholding": extracted.get("federal_withholding", 0),
        }
    if extracted.get("document_type") == "1099-NEC":
        return {
            "business_income": extracted.get("nonemployee_compensation", 0),
            "federal_withholding": extracted.get("federal_withholding", 0),
        }
    return {}