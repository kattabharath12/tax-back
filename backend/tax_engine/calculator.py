from typing import Dict, Any

class TaxCalculator:
    BRACKETS_2024_SINGLE = [
        (0,     11000, 0.10),
        (11000, 44725, 0.12),
        (44725, 95375, 0.22),
        (95375, 182100, 0.24),
        (182100,231250, 0.32),
        (231250,578125, 0.35),
        (578125,float("inf"),0.37),
    ]

    def _tax_for_brackets(self, taxable: float) -> float:
        tax = 0.0
        for lower, upper, rate in self.BRACKETS_2024_SINGLE:
            if taxable <= lower:
                break
            taxed_amount = min(taxable, upper) - lower
            tax += taxed_amount * rate
            if taxable < upper:
                break
        return round(tax, 2)

    def calculate(
        self,
        form_data: Dict[str, Any],
        filing_status: str = "single",
        state: str = "CA"
    ) -> Dict[str, Any]:
        wages   = float(form_data.get("wages", 0))
        biz_inc = float(form_data.get("business_income", 0))
        other   = sum(float(v) for k, v in form_data.items()
                      if k not in {"wages", "business_income",
                                   "federal_withholding", "state_withholding"})
        total_income = wages + biz_inc + other
        standard_deduction = 11600  # single 2024
        taxable_income = max(total_income - standard_deduction, 0)

        federal_tax = self._tax_for_brackets(taxable_income)
        result = {
            "total_income": round(total_income, 2),
            "deductions": standard_deduction,
            "taxable_income": taxable_income,
            "tax_owed": federal_tax,
            "refund": 0  # fill in after subtracting withholding
        }
        return result