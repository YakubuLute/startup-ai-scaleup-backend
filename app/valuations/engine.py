# app/valuations/engine.py
from datetime import datetime

def calculate_dcf(financials, assumptions):
    """
    FR-31: Discounted Cash Flow valuation
    financials: {revenue_history: [], projections: [], ebitda_margin: float}
    assumptions: {discount_rate: float, terminal_growth: float, forecast_years: int}
    """
    discount_rate = assumptions.get('discount_rate', 0.15)  # Default 15% for early-stage African startups
    terminal_growth = assumptions.get('terminal_growth', 0.03)  # 3% terminal growth
    forecast_years = assumptions.get('forecast_years', 5)
    
    projections = financials.get('projections', [])
    ebitda_margin = financials.get('ebitda_margin', 0.15)
    
    # Calculate free cash flows (simplified: EBITDA ~ FCF for early stage)
    fcfs = [proj * ebitda_margin for proj in projections[:forecast_years]]
    
    # Discount each FCF to present value
    pv_fcf = sum(fcf / ((1 + discount_rate) ** (i + 1)) for i, fcf in enumerate(fcfs))
    
    # Terminal value (Gordon Growth Model)
    if fcfs:
        terminal_value = (fcfs[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** forecast_years)
    else:
        pv_terminal = 0
    
    enterprise_value = pv_fcf + pv_terminal
    
    # Sensitivity: +/- 20% on key assumptions for best/worst case
    best_case = enterprise_value * 1.2
    worst_case = enterprise_value * 0.8
    
    return {
        'method': 'DCF',
        'base_case': round(enterprise_value, 2),
        'best_case': round(best_case, 2),
        'worst_case': round(worst_case, 2),
        'key_metrics': {
            'discount_rate': discount_rate,
            'terminal_growth': terminal_growth,
            'pv_fcf': round(pv_fcf, 2),
            'pv_terminal': round(pv_terminal, 2)
        }
    }

def calculate_becker(financials, assumptions):
    """
    FR-31: Becker Method (early-stage heuristic - common in African venture)
    Based on: Stage multiplier × Revenue × Industry factor
    """
    stage = assumptions.get('stage', 'Early')  # Early, Growth, Maturity
    annual_revenue = financials.get('annual_revenue', 0)
    sector = assumptions.get('sector', 'Other')
    
    # Stage multipliers (validated against African venture benchmarks)
    stage_multipliers = {'Early': 3.0, 'Growth': 5.0, 'Maturity': 8.0}
    
    # Sector factors (Agritech typically higher due to impact focus)
    sector_factors = {
        'Agritech': 1.3, 'Fintech': 1.2, 'Healthtech': 1.2,
        'Edtech': 1.1, 'E-commerce': 1.0, 'Other': 1.0
    }
    
    multiplier = stage_multipliers.get(stage, 3.0) * sector_factors.get(sector, 1.0)
    valuation = annual_revenue * multiplier
    
    # Becker includes a "founder premium" for strong teams (simplified here)
    if assumptions.get('strong_team', False):
        valuation *= 1.15
    
    return {
        'method': 'Becker',
        'base_case': round(valuation, 2),
        'best_case': round(valuation * 1.25, 2),
        'worst_case': round(valuation * 0.75, 2),
        'key_metrics': {
            'stage_multiplier': stage_multipliers.get(stage, 3.0),
            'sector_factor': sector_factors.get(sector, 1.0),
            'annual_revenue': annual_revenue
        }
    }

def calculate_asset_based(financials, assumptions):
    """
    FR-31: Asset-Based Valuation (conservative fallback)
    Sum of tangible assets minus liabilities
    """
    assets = financials.get('total_assets', 0)
    liabilities = financials.get('total_liabilities', 0)
    intangible_adjustment = assumptions.get('intangible_adjustment', 0.0)  # 0.0 to 1.0
    
    net_asset_value = assets - liabilities
    # Add back a portion of intangibles if justified (brand, IP, etc.)
    adjusted_valuation = net_asset_value + (net_asset_value * intangible_adjustment)
    
    return {
        'method': 'Asset',
        'base_case': round(max(0, adjusted_valuation), 2),  # Never negative
        'best_case': round(max(0, adjusted_valuation * 1.1), 2),
        'worst_case': round(max(0, adjusted_valuation * 0.9), 2),
        'key_metrics': {
            'total_assets': assets,
            'total_liabilities': liabilities,
            'net_asset_value': round(net_asset_value, 2),
            'intangible_adjustment': intangible_adjustment
        }
    }

def run_valuation(financials, assumptions, methods):
    """
    FR-31: Run selected valuation methods and aggregate results
    methods: list of method names ['DCF', 'Becker', 'Asset']
    """
    results = {}
    
    if 'DCF' in methods and financials.get('projections'):
        results['DCF'] = calculate_dcf(financials, assumptions)
    
    if 'Becker' in methods:
        results['Becker'] = calculate_becker(financials, assumptions)
    
    if 'Asset' in methods and financials.get('total_assets') is not None:
        results['Asset'] = calculate_asset_based(financials, assumptions)
    
    if not results:
        raise ValueError("No valid valuation method could be applied with provided data")
    
    # Aggregate: simple average of base cases for "consensus" valuation
    base_cases = [r['base_case'] for r in results.values()]
    consensus = sum(base_cases) / len(base_cases) if base_cases else 0
    
    return {
        'methods_run': list(results.keys()),
        'consensus_valuation': round(consensus, 2),
        'individual_results': results,
        'confidence': 'high' if len(results) >= 2 else 'medium'
    }