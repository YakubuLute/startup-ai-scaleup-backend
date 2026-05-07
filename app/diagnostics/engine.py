# app/diagnostics/engine.py

# FR-20: Diagnostic Questionnaire Schema (v1 - easily migratable to DB per US-24)
DIAGNOSTIC_SCHEMA = {
    "governance": {
        "weight": 0.25,
        "questions": [
            {"id": "gov_1", "text": "Do you have a formalized business structure?", "type": "yes_no"},
            {"id": "gov_2", "text": "Are roles and responsibilities documented?", "type": "yes_no"},
            {"id": "gov_3", "text": "Do you hold regular board/advisor meetings?", "type": "yes_no"}
        ]
    },
    "financial": {
        "weight": 0.30,
        "questions": [
            {"id": "fin_1", "text": "Do you maintain formal accounting records?", "type": "yes_no"},
            {"id": "fin_2", "text": "Have you prepared 12-month financial projections?", "type": "yes_no"},
            {"id": "fin_3", "text": "Is your business bank account separate from personal accounts?", "type": "yes_no"}
        ]
    },
    "operations": {
        "weight": 0.20,
        "questions": [
            {"id": "ops_1", "text": "Do you have documented SOPs for core processes?", "type": "yes_no"},
            {"id": "ops_2", "text": "Is your supply chain/vendor list documented?", "type": "yes_no"},
            {"id": "ops_3", "text": "Do you track operational KPIs monthly?", "type": "yes_no"}
        ]
    },
    "market": {
        "weight": 0.25,
        "questions": [
            {"id": "mkt_1", "text": "Have you validated product-market fit?", "type": "yes_no"},
            {"id": "mkt_2", "text": "Do you have a documented customer acquisition strategy?", "type": "yes_no"},
            {"id": "mkt_3", "text": "Are you tracking customer retention/churn metrics?", "type": "yes_no"}
        ]
    }
}

def calculate_scores(responses):
    """FR-21: Rule-based scoring engine with weighted categories"""
    sub_scores = {}
    total_weighted = 0
    
    for category, config in DIAGNOSTIC_SCHEMA.items():
        category_questions = config["questions"]
        category_answers = [responses.get(q["id"]) for q in category_questions]
        # Score: yes=10, partial=5, no=0
        raw_score = sum(10 if a == "yes" else 5 if a == "partial" else 0 for a in category_answers if a is not None)
        max_possible = len(category_questions) * 10
        category_pct = round((raw_score / max_possible) * 100) if max_possible > 0 else 0
        
        sub_scores[category] = category_pct
        total_weighted += category_pct * config["weight"]
        
    overall_score = round(total_weighted)
    
    # FR-21: Stage classification
    if overall_score >= 80:
        stage = "Maturity"
    elif overall_score >= 50:
        stage = "Growth"
    else:
        stage = "Early"
        
    return overall_score, stage, sub_scores

def generate_recommendations(sub_scores, stage):
    """FR-22: Tailored roadmap based on diagnostic gaps"""
    recommendations = []
    
    if sub_scores.get("governance", 100) < 40:
        recommendations.append({
            "action": "Formalize governance structure",
            "module": "documents",
            "template": "Corporate Governance Policy",
            "priority": "high"
        })
    if sub_scores.get("financial", 100) < 40:
        recommendations.append({
            "action": "Create financial SOPs & projections",
            "module": "documents",
            "template": "Financial SOP & 12-Month Forecast",
            "priority": "high"
        })
    if sub_scores.get("operations", 100) < 50:
        recommendations.append({
            "action": "Document core operational processes",
            "module": "documents",
            "template": "Operations Manual",
            "priority": "medium"
        })
    if sub_scores.get("market", 100) < 40:
        recommendations.append({
            "action": "Validate market traction & update GTM strategy",
            "module": "diagnostics",
            "template": "Market Validation Checklist",
            "priority": "high"
        })
    if stage == "Early" and sub_scores.get("financial", 100) > 60:
        recommendations.append({
            "action": "Run your first business valuation",
            "module": "valuations",
            "template": None,
            "priority": "medium"
        })
        
    return recommendations