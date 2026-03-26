"""
Valuation calculation services implementing FR-30 to FR-33.
"""

from app.valuations.utils import calculate_npv, calculate_terminal_value, discount_to_present_value


def calculate_dcf_valuation(financials: dict) -> dict:
    """
    Calculate business valuation using Discounted Cash Flow (DCF) method.
    FR-31: Automated Calculations
    
    Args:
        financials: Dict containing:
            - revenue_history: List of historical revenues [Y1, Y2, Y3]
            - projected_growth: Annual growth rate for forecast period
            - profit_margin: Expected net profit margin
            - discount_rate: WACC or required rate of return
            - terminal_growth: Perpetual growth rate after forecast
            - forecast_years: Number of years to project (default: 5)
    
    Returns:
        Dict with valuation amount and detailed breakdown
    """
    # Extract inputs with defaults
    revenue_history = financials.get('revenue_history', [])
    projected_growth = financials.get('projected_growth', 0.20)
    profit_margin = financials.get('profit_margin', 0.15)
    discount_rate = financials.get('discount_rate', 0.15)
    terminal_growth = financials.get('terminal_growth', 0.03)
    forecast_years = financials.get('forecast_years', 5)
    
    # Validate inputs
    if discount_rate <= terminal_growth:
        return {
            'error': 'Discount rate must be greater than terminal growth rate',
            'valuation': None
        }
    
    # Estimate starting cash flow from last historical revenue
    if revenue_history:
        last_revenue = revenue_history[-1]
    else:
        return {'error': 'Revenue history required', 'valuation': None}
    
    starting_fcf = last_revenue * profit_margin
    
    # Project future cash flows
    projected_cf = []
    current_fcf = starting_fcf
    for year in range(1, forecast_years + 1):
        current_fcf *= (1 + projected_growth)
        projected_cf.append(current_fcf)
    
    # Calculate present value of projected cash flows
    pv_cash_flows = sum(
        cf / ((1 + discount_rate) ** year)
        for year, cf in enumerate(projected_cf, start=1)
    )
    
    # Calculate terminal value and discount to present
    terminal_value = calculate_terminal_value(
        projected_cf[-1], terminal_growth, discount_rate
    )
    pv_terminal = discount_to_present_value(
        terminal_value, discount_rate, forecast_years
    )
    
    # Total enterprise value
    enterprise_value = pv_cash_flows + pv_terminal
    
    # Determine confidence based on data quality
    confidence = 'high' if len(revenue_history) >= 3 else 'medium' if len(revenue_history) >= 1 else 'low'
    
    return {
        'valuation': round(enterprise_value, 2),
        'breakdown': {
            'present_value_cash_flows': round(pv_cash_flows, 2),
            'terminal_value': round(terminal_value, 2),
            'pv_terminal_value': round(pv_terminal, 2),
            'assumptions': {
                'starting_fcf': round(starting_fcf, 2),
                'projected_growth': projected_growth,
                'discount_rate': discount_rate,
                'terminal_growth': terminal_growth,
                'forecast_years': forecast_years
            }
        },
        'confidence': confidence,
        'method': 'DCF'
    }


def calculate_becker_valuation(financials: dict) -> dict:
    """
    Calculate valuation using Becker Method (simplified for early-stage startups).
    Formula: Valuation = (Revenue × Industry Multiple) + (Team Score × Team Multiplier)
    
    Note: This is a simplified version. Full Becker method includes more factors.
    """
    revenue = financials.get('revenue_history', [0])[-1] if financials.get('revenue_history') else 0
    industry_multiple = financials.get('industry_multiple', 3.0)  # Typical range: 2-5x for agritech
    team_score = financials.get('team_score', 5)  # 1-10 scale
    team_multiplier = financials.get('team_multiplier', 10000)  # $10K per team point
    
    valuation = (revenue * industry_multiple) + (team_score * team_multiplier)
    
    return {
        'valuation': round(valuation, 2),
        'breakdown': {
            'revenue_component': round(revenue * industry_multiple, 2),
            'team_component': round(team_score * team_multiplier, 2),
            'assumptions': {
                'industry_multiple': industry_multiple,
                'team_score': team_score,
                'team_multiplier': team_multiplier
            }
        },
        'confidence': 'medium',
        'method': 'Becker'
    }


def calculate_asset_valuation(financials: dict) -> dict:
    """
    Calculate valuation using Asset-Based Method.
    Valuation = Total Assets - Total Liabilities
    """
    total_assets = financials.get('total_assets', 0)
    total_liabilities = financials.get('total_liabilities', 0)
    intangible_adjustment = financials.get('intangible_adjustment', 0)  # For IP, brand, etc.
    
    valuation = (total_assets - total_liabilities) + intangible_adjustment
    
    return {
        'valuation': round(max(0, valuation), 2),  # Can't be negative
        'breakdown': {
            'net_tangible_assets': round(total_assets - total_liabilities, 2),
            'intangible_adjustment': round(intangible_adjustment, 2),
            'assumptions': {
                'total_assets': total_assets,
                'total_liabilities': total_liabilities
            }
        },
        'confidence': 'high' if total_assets > 0 else 'low',
        'method': 'Asset'
    }


def run_valuation(method: str, financials: dict) -> dict:
    """
    Main entry point: route to appropriate valuation method.
    """
    calculators = {
        'DCF': calculate_dcf_valuation,
        'Becker': calculate_becker_valuation,
        'Asset': calculate_asset_valuation,
        # 'Comparable': calculate_comparable_valuation  # Future
    }
    
    calculator = calculators.get(method)
    if not calculator:
        return {'error': f'Unknown valuation method: {method}', 'valuation': None}
    
    return calculator(financials)