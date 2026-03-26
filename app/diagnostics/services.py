"""
Scoring engine and recommendation logic for FR-21 + FR-22.
"""

from app.diagnostics.questions import DIAGNOSTIC_QUESTIONS, STAGE_THRESHOLDS


def calculate_dimension_score(dimension: str, responses: dict) -> dict:
    """
    Calculate score for a single dimension (governance, financial, etc.)
    
    Returns:
        Dict with score (0-100), max_possible, and percentage
    """
    questions = DIAGNOSTIC_QUESTIONS.get(dimension, [])
    if not questions:
        return {"score": 0, "max_possible": 0, "percentage": 0}
    
    total_score = 0
    max_possible = 0
    
    for q in questions:
        q_id = q["id"]
        answer = responses.get(q_id)
        
        if answer is None:
            # Unanswered questions don't contribute to score
            continue
        
        weights = q.get("weights", {})
        points = weights.get(str(answer), 0)
        
        # Max possible for this question is the highest weight
        max_for_q = max(weights.values()) if weights else 10
        max_possible += max_for_q
        total_score += points
    
    percentage = round((total_score / max_possible * 100)) if max_possible > 0 else 0
    
    return {
        "score": total_score,
        "max_possible": max_possible,
        "percentage": percentage
    }


def calculate_overall_score(responses: dict) -> dict:
    """
    Calculate overall diagnostic score and stage classification (FR-21).
    
    Returns:
        Dict with overall_score, stage, and sub_scores
    """
    dimensions = ["governance", "financial", "operations", "market"]
    sub_scores = {}
    total_percentage = 0
    
    for dim in dimensions:
        result = calculate_dimension_score(dim, responses)
        sub_scores[dim] = result["percentage"]
        total_percentage += result["percentage"]
    
    # Average of all dimension percentages
    overall_score = round(total_percentage / len(dimensions)) if dimensions else 0
    
    # Classify stage based on thresholds
    stage = "Early"  # default
    for stage_name, thresholds in STAGE_THRESHOLDS.items():
        if thresholds["min"] <= overall_score <= thresholds["max"]:
            stage = stage_name
            break
    
    return {
        "overall_score": overall_score,
        "stage": stage,
        "sub_scores": sub_scores
    }


def generate_recommendations(stage: str, sub_scores: dict) -> list:
    """
    Generate actionable recommendations based on stage and weak areas (FR-22).
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Stage-based baseline recommendations
    if stage == "Early":
        recommendations.extend([
            "Focus on formalizing your business structure and legal registration.",
            "Create basic financial records to track revenue and expenses.",
            "Document your core value proposition and target customer."
        ])
    elif stage == "Growth":
        recommendations.extend([
            "Develop standard operating procedures (SOPs) for key processes.",
            "Implement basic KPIs to track business performance.",
            "Consider running a business valuation to prepare for investment."
        ])
    elif stage == "Maturity":
        recommendations.extend([
            "Prepare investor-ready documents (pitch deck, financial model).",
            "Consider applying for verification to build investor trust.",
            "Explore scaling strategies and market expansion opportunities."
        ])
    
    # Dimension-specific recommendations for weak areas (< 50%)
    if sub_scores.get("governance", 100) < 50:
        recommendations.append("Strengthen governance: document roles, hold regular meetings, consider an advisory board.")
    
    if sub_scores.get("financial", 100) < 50:
        recommendations.append("Improve financial management: separate business/personal finances, create a budget, track KPIs.")
    
    if sub_scores.get("operations", 100) < 50:
        recommendations.append("Standardize operations: document SOPs for key processes, track delivery metrics.")
    
    if sub_scores.get("market", 100) < 50:
        recommendations.append("Clarify market strategy: define target customers, document go-to-market plan, track customer acquisition.")
    
    # Remove duplicates and limit to top 5
    recommendations = list(dict.fromkeys(recommendations))[:5]
    
    return recommendations


def run_diagnostic(responses: dict) -> dict:
    """
    Main entry point: run full diagnostic and return results.
    """
    # Calculate scores
    scoring = calculate_overall_score(responses)
    
    # Generate recommendations
    recommendations = generate_recommendations(scoring["stage"], scoring["sub_scores"])
    
    return {
        **scoring,
        "recommendations": recommendations,
        "dimensions_assessed": list(DIAGNOSTIC_QUESTIONS.keys())
    }