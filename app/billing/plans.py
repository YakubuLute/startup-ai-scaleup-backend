"""
Default subscription plan definitions for FR-60.
These can be modified by admins or loaded from config.
"""

DEFAULT_PLANS = [
    {
        "name": "Free",
        "description": "Get started with essential features",
        "price": None,  # Free tier
        "billing_cycle": "monthly",
        "limits": {
            "max_documents_per_month": 1,
            "max_valuations_per_month": 0,
            "max_diagnostics_per_month": 1,
            "max_team_members": 1,
            "max_storage_mb": 100
        },
        "features": [
            "Basic document templates",
            "Stage diagnostic (basic)",
            "Email support",
            "Community access"
        ],
        "is_active": True
    },
    {
        "name": "Starter",
        "description": "For early-stage startups building foundations",
        "price": 50.00,  # GHS
        "billing_cycle": "monthly",
        "limits": {
            "max_documents_per_month": 5,
            "max_valuations_per_month": 2,
            "max_diagnostics_per_month": 3,
            "max_team_members": 3,
            "max_storage_mb": 500
        },
        "features": [
            "All Free features",
            "Premium document templates",
            "Business valuations (DCF, Becker)",
            "Team collaboration (3 members)",
            "Priority email support"
        ],
        "is_active": True
    },
    {
        "name": "Growth",
        "description": "For scaling startups preparing for investment",
        "price": 150.00,  # GHS
        "billing_cycle": "monthly",
        "limits": {
            "max_documents_per_month": -1,  # -1 = unlimited
            "max_valuations_per_month": -1,
            "max_diagnostics_per_month": -1,
            "max_team_members": 10,
            "max_storage_mb": 2000
        },
        "features": [
            "All Starter features",
            "Unlimited documents & valuations",
            "Priority verification queue",
            "Investor portal access",
            "Advanced analytics",
            "Dedicated support"
        ],
        "is_active": True
    },
    {
        "name": "Enterprise",
        "description": "Custom solutions for organizations & accelerators",
        "price": None,  # Contact sales
        "billing_cycle": "custom",
        "limits": {
            "max_documents_per_month": -1,
            "max_valuations_per_month": -1,
            "max_diagnostics_per_month": -1,
            "max_team_members": -1,
            "max_storage_mb": -1
        },
        "features": [
            "All Growth features",
            "White-label options",
            "API access",
            "Custom integrations",
            "SLA guarantee",
            "Account manager"
        ],
        "is_active": True
    }
]

# Helper to check if a limit is exceeded
def check_limit(current_usage: int, plan_limit: int) -> bool:
    """
    Returns True if usage is within limit.
    -1 means unlimited.
    """
    if plan_limit == -1:
        return True  # Unlimited
    return current_usage < plan_limit