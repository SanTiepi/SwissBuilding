"""SwissBuilding — Fiscal Deduction Service.

Calculate tax deduction savings from building renovations by canton.
Provides single-year deduction calculations and multi-year projections.
"""

from __future__ import annotations

from datetime import datetime

from app.constants import DEDUCTION_RULES


class FiscalDeductionService:
    """Calculate tax deduction savings from renovation work."""

    @staticmethod
    def calculate_deduction(
        canton: str,
        renovation_type: str,
        total_cost_chf: float,
        fiscal_year: int,
    ) -> dict:
        """
        Calculate deduction and tax savings for a renovation.

        Args:
            canton: Two-letter canton code (e.g., 'VD', 'GE', 'BE', 'ZH')
            renovation_type: Type of renovation (energy, amiante, seismic, facade, sanitary, roof)
            total_cost_chf: Total renovation cost in CHF
            fiscal_year: The fiscal year for which to calculate deduction

        Returns:
            Dictionary with deduction details and estimated tax savings
        """
        # Get rules for this canton
        rules = DEDUCTION_RULES.get(canton, {})

        if renovation_type not in rules:
            return {
                "canton": canton,
                "renovation_type": renovation_type,
                "total_cost": total_cost_chf,
                "deduction_rate": 0,
                "deduction_amount": 0,
                "max_deduction": 0,
                "tax_savings_estimate": 0,
                "fiscal_year": fiscal_year,
                "notes": f"No standard deduction for {renovation_type} in {canton}",
            }

        rule = rules[renovation_type]
        deduction_rate = rule["rate"]
        max_deduction = rule.get("max_per_year", 999999)
        eligible_cost_percent = rule.get("eligible_cost_percent", 1.0)
        eligible_cost = eligible_cost_percent * total_cost_chf

        # Calculate deduction amount
        deduction_amount = min(eligible_cost * deduction_rate, max_deduction)

        # Estimate tax savings (assume 20% marginal tax rate)
        marginal_tax_rate = 0.20
        tax_savings_estimate = deduction_amount * marginal_tax_rate

        return {
            "canton": canton,
            "renovation_type": renovation_type,
            "total_cost": total_cost_chf,
            "deduction_rate": deduction_rate,
            "deduction_amount": round(deduction_amount, 2),
            "max_deduction": max_deduction,
            "tax_savings_estimate": round(tax_savings_estimate, 2),
            "fiscal_year": fiscal_year,
            "notes": rule.get("notes", ""),
        }

    @staticmethod
    def simulate_multi_year_deduction(
        canton: str,
        renovations: list[dict],
        fiscal_years: int = 5,
    ) -> dict:
        """
        Simulate deductions spread over multiple fiscal years.

        Args:
            canton: Two-letter canton code
            renovations: List of dicts with 'type' and 'cost' keys
            fiscal_years: Number of fiscal years to project

        Returns:
            Dictionary with multi-year deduction projection
        """
        total_deduction = 0.0
        total_tax_savings = 0.0
        yearly_breakdown = []

        current_year = datetime.now().year

        for year_offset in range(fiscal_years):
            fiscal_year = current_year + year_offset
            year_deduction = 0.0
            year_tax_savings = 0.0

            for reno in renovations:
                result = FiscalDeductionService.calculate_deduction(
                    canton, reno["type"], reno["cost"], fiscal_year
                )
                year_deduction += result["deduction_amount"]
                year_tax_savings += result["tax_savings_estimate"]

            total_deduction += year_deduction
            total_tax_savings += year_tax_savings

            yearly_breakdown.append({
                "fiscal_year": fiscal_year,
                "year_deduction": round(year_deduction, 2),
                "year_tax_savings": round(year_tax_savings, 2),
            })

        return {
            "canton": canton,
            "total_renovation_cost": sum(r["cost"] for r in renovations),
            "total_deduction": round(total_deduction, 2),
            "total_tax_savings_estimate": round(total_tax_savings, 2),
            "yearly_breakdown": yearly_breakdown,
            "fiscal_years_projected": fiscal_years,
            "notes": "Estimates based on 20% marginal tax rate; consult accountant for actual rate",
        }
