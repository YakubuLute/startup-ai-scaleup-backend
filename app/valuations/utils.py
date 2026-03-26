"""
Financial calculation utilities for valuation methods.
Pure Python - no external dependencies beyond standard library.
"""

def calculate_npv(cash_flows: list, discount_rate: float) -> float:
    """
    Calculate Net Present Value of a series of cash flows.
    
    Args:
        cash_flows: List of cash flows [CF0, CF1, CF2, ...]
        discount_rate: Annual discount rate (e.g., 0.15 for 15%)
    
    Returns:
        Net Present Value
    """
    npv = 0
    for t, cf in enumerate(cash_flows):
        npv += cf / ((1 + discount_rate) ** t)
    return npv


def calculate_terminal_value(final_cash_flow: float, growth_rate: float, discount_rate: float) -> float:
    """
    Calculate terminal value using Gordon Growth Model.
    TV = FCF * (1 + g) / (r - g)
    
    Args:
        final_cash_flow: Final year free cash flow
        growth_rate: Perpetual growth rate (g)
        discount_rate: Discount rate (r)
    
    Returns:
        Terminal value
    """
    if discount_rate <= growth_rate:
        raise ValueError("Discount rate must be greater than growth rate")
    
    return (final_cash_flow * (1 + growth_rate)) / (discount_rate - growth_rate)


def discount_to_present_value(future_value: float, discount_rate: float, years: int) -> float:
    """
    Discount a future value to present value.
    PV = FV / (1 + r)^n
    """
    return future_value / ((1 + discount_rate) ** years)