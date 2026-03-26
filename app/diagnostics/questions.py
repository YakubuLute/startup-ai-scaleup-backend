"""
Diagnostic questionnaire definitions for FR-20.
Organized by dimension with scoring rules.
"""

DIAGNOSTIC_QUESTIONS = {
    "governance": [
        {
            "id": "gov_01",
            "question": "Is your business legally registered?",
            "type": "boolean",
            "weights": {"yes": 10, "no": 0}
        },
        {
            "id": "gov_02",
            "question": "Do you have documented roles & responsibilities for your team?",
            "type": "scale",
            "options": ["Not at all", "Partially", "Mostly", "Fully"],
            "weights": {"Not at all": 0, "Partially": 3, "Mostly": 7, "Fully": 10}
        },
        {
            "id": "gov_03",
            "question": "Do you hold regular team/leadership meetings with documented minutes?",
            "type": "scale",
            "options": ["Never", "Rarely", "Sometimes", "Often", "Always"],
            "weights": {"Never": 0, "Rarely": 2, "Sometimes": 5, "Often": 8, "Always": 10}
        },
        {
            "id": "gov_04",
            "question": "Do you have a formal board of directors or advisory board?",
            "type": "boolean",
            "weights": {"yes": 10, "no": 0}
        }
    ],
    
    "financial": [
        {
            "id": "fin_01",
            "question": "Do you maintain formal financial records (income statement, balance sheet)?",
            "type": "scale",
            "options": ["No records", "Basic spreadsheet", "Accounting software", "Audited statements"],
            "weights": {"No records": 0, "Basic spreadsheet": 3, "Accounting software": 7, "Audited statements": 10}
        },
        {
            "id": "fin_02",
            "question": "Do you have a documented budget or financial forecast?",
            "type": "boolean",
            "weights": {"yes": 10, "no": 0}
        },
        {
            "id": "fin_03",
            "question": "Is your business currently profitable or on track to profitability within 12 months?",
            "type": "scale",
            "options": ["Not profitable, no clear path", "Not profitable, path defined", "Break-even", "Profitable"],
            "weights": {"Not profitable, no clear path": 0, "Not profitable, path defined": 4, "Break-even": 7, "Profitable": 10}
        },
        {
            "id": "fin_04",
            "question": "Do you separate business and personal finances?",
            "type": "boolean",
            "weights": {"yes": 10, "no": 0}
        }
    ],
    
    "operations": [
        {
            "id": "ops_01",
            "question": "Do you have documented standard operating procedures (SOPs) for key processes?",
            "type": "scale",
            "options": ["None", "1-2 processes", "Most processes", "All key processes"],
            "weights": {"None": 0, "1-2 processes": 3, "Most processes": 7, "All key processes": 10}
        },
        {
            "id": "ops_02",
            "question": "Do you track key performance indicators (KPIs) for your business?",
            "type": "boolean",
            "weights": {"yes": 10, "no": 0}
        },
        {
            "id": "ops_03",
            "question": "Is your product/service delivery process standardized and repeatable?",
            "type": "scale",
            "options": ["Ad-hoc", "Partially defined", "Mostly standardized", "Fully standardized"],
            "weights": {"Ad-hoc": 0, "Partially defined": 4, "Mostly standardized": 7, "Fully standardized": 10}
        }
    ],
    
    "market": [
        {
            "id": "mkt_01",
            "question": "Do you have a documented target customer profile?",
            "type": "boolean",
            "weights": {"yes": 10, "no": 0}
        },
        {
            "id": "mkt_02",
            "question": "Do you have paying customers or confirmed pilot users?",
            "type": "scale",
            "options": ["None", "1-5", "6-20", "21-50", "50+"],
            "weights": {"None": 0, "1-5": 3, "6-20": 6, "21-50": 8, "50+": 10}
        },
        {
            "id": "mkt_03",
            "question": "Do you have a documented go-to-market or sales strategy?",
            "type": "boolean",
            "weights": {"yes": 10, "no": 0}
        },
        {
            "id": "mkt_04",
            "question": "Do you have recurring revenue or repeat customers?",
            "type": "scale",
            "options": ["No", "Some", "Most", "All"],
            "weights": {"No": 0, "Some": 4, "Most": 7, "All": 10}
        }
    ]
}

# Stage classification thresholds (FR-21)
STAGE_THRESHOLDS = {
    "Early": {"min": 0, "max": 49},
    "Growth": {"min": 50, "max": 79},
    "Maturity": {"min": 80, "max": 100}
}