# app/valuations/services.py
"""
FR-30 + FR-31 + FR-32: Valuation Calculation Engines
Implements DCF, Becker, and Asset-Based methods with sensitivity analysis.
"""

from typing import Dict, List, Optional
from app.valuations.utils import (
    calculate_npv, calculate_terminal_value, calculate_irr,
    calculate_revenue_multiple, calculate_asset_based_valuation,
    calculate_confidence_score
)

def run_dcf_valuation(financials: Dict) -> Dict:
    """
    Discounted Cash Flow valuation method.
    
    Required inputs:
    - revenue_history: List of past 3 years revenue [y-3, y-2, y-1]
    - projected_growth: Annual growth rate for next 5 years (decimal)
    - operating_margin: Expected operating margin (decimal)
    - capex_percent: Capital expenditure as % of revenue (decimal)
    - working_capital_change: Annual change in working capital (decimal)
    - discount_rate: WACC (decimal)
    - terminal_growth: Perpetual growth rate post-projection (decimal)
    - tax_rate: Corporate tax rate (decimal)
    
    Returns:
        Dict with valuation, breakdown, IRR, and confidence
    """
    # Validate required inputs
    required = ['revenue_history', 'projected_growth', 'operating_margin', 
                'capex_percent', 'working_capital_change', 'discount_rate', 
                'terminal_growth', 'tax_rate']
    for field in required:
        if field not in financials:
            return {'error': f'Missing required field: {field}'}
    
    # Extract inputs
    revenue_history = financials['revenue_history'][-3:]  # Last 3 years
    last_revenue = revenue_history[-1] if revenue_history else 0
    growth = financials['projected_growth']
    margin = financials['operating_margin']
    capex_pct = financials['capex_percent']
    wc_change = financials['working_capital_change']
    discount_rate = financials['discount_rate']
    terminal_growth = financials['terminal_growth']
    tax_rate = financials['tax_rate']
    
    # Project revenues for 5 years
    projected_revenues = [last_revenue * ((1 + growth) ** t) for t in range(1, 6)]
    
    # Calculate Free Cash Flows (simplified)
    fcfs = []
    for revenue in projected_revenues:
        ebit = revenue * margin
        tax = ebit * tax_rate
        nopat = ebit - tax
        capex = revenue * capex_pct
        wc_investment = revenue * wc_change
        fcf = nopat - capex - wc_investment
        fcfs.append(fcf)
    
    # Calculate terminal value
    terminal_value = calculate_terminal_value(fcfs[-1], terminal_growth, discount_rate)
    
    # Calculate NPV of projection period + terminal value
    cash_flows = [-last_revenue * 0.1] + fcfs  # Assume 10% initial investment
    cash_flows[-1] += terminal_value  # Add terminal value to final year
    
    enterprise_value = calculate_npv(cash_flows, discount_rate)
    
    # Calculate IRR
    irr = calculate_irr(cash_flows)
    
    # Sensitivity analysis (±2% discount rate, ±1% growth)
    sensitivity = {
        'discount_rate': {
            'base': round(enterprise_value, 2),
            'low': round(calculate_npv(cash_flows, discount_rate - 0.02), 2),
            'high': round(calculate_npv(cash_flows, discount_rate + 0.02), 2)
        },
        'growth': {
            'base': round(enterprise_value, 2),
            'low': round(calculate_npv([cf * (0.98 if i > 0 else 1) for i, cf in enumerate(cash_flows)], discount_rate), 2),
            'high': round(calculate_npv([cf * (1.02 if i > 0 else 1) for i, cf in enumerate(cash_flows)], discount_rate), 2)
        }
    }
    
    # Calculate confidence score
    completeness = 100  # All required fields provided
    confidence = calculate_confidence_score(completeness, 'high', 'DCF')
    
    return {
        'valuation': max(enterprise_value, 0),
        'currency': 'GHS',
        'method': 'DCF',
        'breakdown': {
            'projected_revenues': [round(r, 2) for r in projected_revenues],
            'projected_fcfs': [round(f, 2) for f in fcfs],
            'terminal_value': round(terminal_value, 2),
            'discount_rate': discount_rate * 100,
            'terminal_growth': terminal_growth * 100
        },
        'irr': irr * 100 if irr else None,
        'sensitivity': sensitivity,
        'confidence': confidence,
        'assumptions': {
            'projection_years': 5,
            'terminal_model': 'Gordon Growth'
        }
    }

def run_becker_valuation(financials: Dict) -> Dict:
    """
    Becker Method valuation (simplified for early-stage startups).
    
    Required inputs:
    - revenue_history: List of past 2 years revenue
    - industry_multiple: Industry revenue multiple (e.g., 3.5 for agritech)
    - team_score: Team quality score 1-10
    - market_score: Market attractiveness score 1-10
    - traction_score: Customer traction score 1-10
    
    Returns:
        Dict with valuation, breakdown, and confidence
    """
    # Validate required inputs
    required = ['revenue_history', 'industry_multiple', 'team_score', 'market_score', 'traction_score']
    for field in required:
        if field not in financials:
            return {'error': f'Missing required field: {field}'}
    
    # Extract inputs
    revenue = financials['revenue_history'][-1] if financials['revenue_history'] else 0
    base_multiple = financials['industry_multiple']
    team_score = min(max(financials['team_score'], 1), 10)
    market_score = min(max(financials['market_score'], 1), 10)
    traction_score = min(max(financials['traction_score'], 1), 10)
    
    # Calculate adjustment factor (Becker methodology)
    # Base multiple adjusted by qualitative factors
    adjustment = 1.0
    adjustment += (team_score - 5) * 0.08  # ±0.4 max
    adjustment += (market_score - 5) * 0.06  # ±0.3 max
    adjustment += (traction_score - 5) * 0.04  # ±0.2 max
    adjusted_multiple = base_multiple * adjustment
    
    # Calculate valuation
    valuation = calculate_revenue_multiple(revenue, adjusted_multiple)
    
    # Sensitivity: show range based on multiple uncertainty
    sensitivity = {
        'multiple': {
            'base': round(valuation, 2),
            'low': round(calculate_revenue_multiple(revenue, adjusted_multiple * 0.8), 2),
            'high': round(calculate_revenue_multiple(revenue, adjusted_multiple * 1.2), 2)
        }
    }
    
    # Confidence based on data quality
    completeness = 100
    confidence = calculate_confidence_score(completeness, 'medium', 'Becker')
    
    return {
        'valuation': valuation,
        'currency': 'GHS',
        'method': 'Becker',
        'breakdown': {
            'base_multiple': base_multiple,
            'adjustment_factor': round(adjustment, 2),
            'adjusted_multiple': round(adjusted_multiple, 2),
            'latest_revenue': round(revenue, 2),
            'qualitative_scores': {
                'team': team_score,
                'market': market_score,
                'traction': traction_score
            }
        },
        'sensitivity': sensitivity,
        'confidence': confidence,
        'assumptions': {
            'methodology': 'Becker Early-Stage Valuation',
            'note': 'Best for startups with <3 years revenue history'
        }
    }

def run_asset_valuation(financials: Dict) -> Dict:
    """
    Asset-Based valuation method.
    
    Required inputs:
    - total_assets: Total assets in GHS
    - total_liabilities: Total liabilities in GHS
    - intangible_assets: Optional intangible asset value
    - asset_quality: 'high', 'medium', or 'low'
    
    Returns:
        Dict with valuation, breakdown, and confidence
    """
    # Validate required inputs
    required = ['total_assets', 'total_liabilities']
    for field in required:
        if field not in financials:
            return {'error': f'Missing required field: {field}'}
    
    # Extract inputs
    total_assets = financials['total_assets']
    total_liabilities = financials['total_liabilities']
    intangible = financials.get('intangible_assets', 0)
    asset_quality = financials.get('asset_quality', 'medium')
    
    # Calculate net asset value
    valuation = calculate_asset_based_valuation(total_assets, total_liabilities, intangible)
    
    # Apply quality adjustment
    quality_factors = {'high': 1.0, 'medium': 0.9, 'low': 0.75}
    adjusted_valuation = valuation * quality_factors.get(asset_quality, 0.9)
    
    # Sensitivity based on asset quality uncertainty
    sensitivity = {
        'asset_quality': {
            'base': round(adjusted_valuation, 2),
            'low': round(valuation * 0.75, 2),
            'high': round(valuation * 1.0, 2)
        }
    }
    
    # Confidence based on asset tangibility
    completeness = 100 if 'intangible_assets' in financials else 80
    confidence = calculate_confidence_score(completeness, asset_quality, 'Asset')
    
    return {
        'valuation': round(adjusted_valuation, 2),
        'currency': 'GHS',
        'method': 'Asset',
        'breakdown': {
            'total_assets': round(total_assets, 2),
            'total_liabilities': round(total_liabilities, 2),
            'intangible_assets': round(intangible, 2),
            'net_book_value': round(valuation, 2),
            'quality_adjustment': quality_factors.get(asset_quality, 0.9)
        },
        'sensitivity': sensitivity,
        'confidence': confidence,
        'assumptions': {
            'methodology': 'Adjusted Net Asset Value',
            'note': 'Best for asset-heavy businesses (manufacturing, agriculture)'
        }
    }

def run_valuation(method: str, financials: Dict) -> Dict:
    """
    Main entry point: Route to appropriate valuation method.
    
    Args:
        method: One of 'DCF', 'Becker', 'Asset'
        financials: Dict of financial inputs for the chosen method
    
    Returns:
        Valuation result dict or error dict
    """
    methods = {
        'DCF': run_dcf_valuation,
        'Becker': run_becker_valuation,
        'Asset': run_asset_valuation
    }
    
    if method not in methods:
        return {'error': f'Unknown valuation method: {method}. Available: {list(methods.keys())}'}
    
    try:
        result = methods[method](financials)
        result['calculated_at'] = None  # Will be set by route layer
        return result
    except Exception as e:
        return {'error': f'Valuation calculation failed: {str(e)}'}