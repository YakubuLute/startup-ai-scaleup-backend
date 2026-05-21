# app/valuations/utils.py
"""
FR-30 + FR-31: Financial Calculation Utilities
NPV, IRR, terminal value, and multiples helpers for valuation methods.
"""

import math
from typing import List, Optional

def calculate_npv(cash_flows: List[float], discount_rate: float) -> float:
    """
    Calculate Net Present Value of a series of cash flows.
    
    Args:
        cash_flows: List of cash flows [CF0, CF1, CF2, ...] where CF0 is initial investment (negative)
        discount_rate: Annual discount rate as decimal (e.g., 0.15 for 15%)
    
    Returns:
        NPV rounded to 2 decimal places
    """
    npv = 0.0
    for t, cf in enumerate(cash_flows):
        npv += cf / ((1 + discount_rate) ** t)
    return round(npv, 2)

def calculate_terminal_value(final_year_fcf: float, growth_rate: float, discount_rate: float) -> float:
    """
    Calculate terminal value using Gordon Growth Model.
    
    Args:
        final_year_fcf: Free cash flow in the final projection year
        growth_rate: Perpetual growth rate as decimal (e.g., 0.03 for 3%)
        discount_rate: WACC/discount rate as decimal
    
    Returns:
        Terminal value rounded to 2 decimal places
    """
    if discount_rate <= growth_rate:
        # Prevent division by zero or negative denominator
        return round(final_year_fcf * 10, 2)  # Conservative fallback: 10x multiple
    
    terminal_value = (final_year_fcf * (1 + growth_rate)) / (discount_rate - growth_rate)
    return round(terminal_value, 2)

def calculate_irr(cash_flows: List[float], guess: float = 0.1, tolerance: float = 1e-6, max_iterations: int = 100) -> Optional[float]:
    """
    Calculate Internal Rate of Return using Newton-Raphson method.
    
    Args:
        cash_flows: List of cash flows [CF0, CF1, CF2, ...]
        guess: Initial guess for IRR (default 10%)
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations before giving up
    
    Returns:
        IRR as decimal (e.g., 0.25 for 25%) or None if not convergent
    """
    def npv_at_rate(rate: float) -> float:
        return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))
    
    def derivative_at_rate(rate: float) -> float:
        return sum(-t * cf / ((1 + rate) ** (t + 1)) for t, cf in enumerate(cash_flows) if t > 0)
    
    rate = guess
    for _ in range(max_iterations):
        npv = npv_at_rate(rate)
        if abs(npv) < tolerance:
            return round(rate, 4)
        
        deriv = derivative_at_rate(rate)
        if abs(deriv) < 1e-10:  # Avoid division by near-zero
            break
        
        rate = rate - npv / deriv
        if rate < -0.99:  # IRR can't be <-100%
            rate = -0.99
    
    return None  # Did not converge

def calculate_revenue_multiple(revenue: float, industry_multiple: float) -> float:
    """
    Calculate valuation using revenue multiple method.
    
    Args:
        revenue: Annual revenue in GHS
        industry_multiple: Industry-specific revenue multiple (e.g., 3.5x for agritech)
    
    Returns:
        Valuation rounded to 2 decimal places
    """
    return round(revenue * industry_multiple, 2)

def calculate_asset_based_valuation(total_assets: float, total_liabilities: float, intangible_adjustment: float = 0.0) -> float:
    """
    Calculate asset-based valuation (book value method).
    
    Args:
        total_assets: Total assets in GHS
        total_liabilities: Total liabilities in GHS
        intangible_adjustment: Optional adjustment for intangible assets (default 0)
    
    Returns:
        Net asset value rounded to 2 decimal places
    """
    nav = total_assets - total_liabilities + intangible_adjustment
    return round(max(nav, 0), 2)  # Valuation can't be negative

def calculate_confidence_score(completeness: float, data_quality: str, method: str) -> str:
    """
    Calculate confidence level for valuation result.
    
    Args:
        completeness: Percentage of required inputs provided (0-100)
        data_quality: 'high', 'medium', or 'low'
        method: Valuation method used
    
    Returns:
        Confidence level: 'high', 'medium', or 'low'
    """
    # Base score from completeness
    base_score = completeness
    
    # Adjust for data quality
    quality_multipliers = {'high': 1.0, 'medium': 0.85, 'low': 0.6}
    adjusted_score = base_score * quality_multipliers.get(data_quality, 0.7)
    
    # Adjust for method reliability (DCF most reliable with good data)
    method_reliability = {
        'DCF': 1.0 if completeness > 80 else 0.7,
        'Becker': 0.9,
        'Asset': 0.8
    }
    final_score = adjusted_score * method_reliability.get(method, 0.75)
    
    if final_score >= 75:
        return 'high'
    elif final_score >= 50:
        return 'medium'
    else:
        return 'low'