"""
Analytics & Reporting services for FR-90 to FR-91.
Platform-wide metrics for SSDP stakeholder reporting.
"""

from datetime import datetime, timedelta
from app.models import (
    User, Startup, BusinessDocument, Valuation, DiagnosticSession,
    VerificationCase, Subscription, CohortEnrollment, Program,
    ConnectionRequest, Notification
)
from app.extensions import db


def get_platform_overview():
    """
    FR-90: High-level platform metrics.
    """
    # User metrics
    total_users = User.query.count()
    founders = User.query.filter_by(role='Founder').count()
    investors = User.query.filter_by(role='Investor').count()
    program_managers = User.query.filter_by(role='Program Manager').count()
    
    # Startup metrics
    total_startups = Startup.query.count()
    verified_startups = Startup.query.filter_by(is_verified=True).count()
    
    # Activity metrics
    total_documents = BusinessDocument.query.count()
    total_valuations = Valuation.query.count()
    total_diagnostics = DiagnosticSession.query.count()
    total_verifications = VerificationCase.query.count()
    
    # Connection metrics
    total_connections = ConnectionRequest.query.count()
    accepted_connections = ConnectionRequest.query.filter_by(status='accepted').count()
    
    return {
        "users": {
            "total": total_users,
            "founders": founders,
            "investors": investors,
            "program_managers": program_managers
        },
        "startups": {
            "total": total_startups,
            "verified": verified_startups,
            "verification_rate": round(verified_startups / total_startups * 100, 1) if total_startups > 0 else 0
        },
        "activity": {
            "documents_generated": total_documents,
            "valuations_completed": total_valuations,
            "diagnostics_run": total_diagnostics,
            "verifications_submitted": total_verifications
        },
        "connections": {
            "total_requests": total_connections,
            "accepted": accepted_connections,
            "success_rate": round(accepted_connections / total_connections * 100, 1) if total_connections > 0 else 0
        }
    }


def get_growth_metrics(days: int = 30):
    """
    FR-90: Growth trends over time.
    """
    cutoff = datetime.now() - timedelta(days=days)
    
    # New users over time
    new_users = User.query.filter(User.created_at >= cutoff).count()
    
    # New startups over time
    new_startups = Startup.query.filter(Startup.created_at >= cutoff).count()
    
    # Documents generated over time
    new_documents = BusinessDocument.query.filter(
        BusinessDocument.generated_at >= cutoff
    ).count()
    
    # Verifications completed over time
    new_verifications = VerificationCase.query.filter(
        VerificationCase.status == 'verified',
        VerificationCase.reviewed_at >= cutoff
    ).count()
    
    return {
        "period_days": days,
        "new_users": new_users,
        "new_startups": new_startups,
        "new_documents": new_documents,
        "new_verifications": new_verifications,
        "daily_averages": {
            "users": round(new_users / days, 1),
            "startups": round(new_startups / days, 1),
            "documents": round(new_documents / days, 1),
            "verifications": round(new_verifications / days, 1)
        }
    }


def get_program_analytics():
    """
    FR-90: Program & cohort performance metrics.
    """
    programs = Program.query.all()
    
    program_stats = []
    for program in programs:
        cohorts = CohortEnrollment.query.join(Cohort).filter(
            Cohort.program_id == program.id
        ).all()
        
        total = len(cohorts)
        accepted = len([c for c in cohorts if c.status == 'accepted'])
        graduated = len([c for c in cohorts if c.status == 'graduated'])
        
        avg_progress = sum([c.overall_progress or 0 for c in cohorts]) / total if total > 0 else 0
        
        program_stats.append({
            "program_id": program.id,
            "program_name": program.name,
            "total_enrollments": total,
            "accepted": accepted,
            "graduated": graduated,
            "graduation_rate": round(graduated / total * 100, 1) if total > 0 else 0,
            "average_progress": round(avg_progress, 1)
        })
    
    return {
        "total_programs": len(programs),
        "programs": program_stats
    }


def get_billing_analytics():
    """
    FR-90: Subscription & revenue metrics.
    """
    from app.models import SubscriptionPlan
    
    subscriptions = Subscription.query.filter_by(status='active').all()
    
    # Group by plan
    plan_distribution = {}
    total_mrr = 0  # Monthly Recurring Revenue
    
    for sub in subscriptions:
        plan_name = sub.plan.name if sub.plan else 'Unknown'
        plan_price = sub.plan.price or 0
        
        if plan_name not in plan_distribution:
            plan_distribution[plan_name] = {
                "count": 0,
                "revenue": 0
            }
        
        plan_distribution[plan_name]["count"] += 1
        plan_distribution[plan_name]["revenue"] += plan_price
        total_mrr += plan_price
    
    return {
        "active_subscriptions": len(subscriptions),
        "total_mrr": total_mrr,
        "plan_distribution": plan_distribution,
        "revenue_by_plan": [
            {"plan": k, "subscribers": v["count"], "revenue": v["revenue"]}
            for k, v in plan_distribution.items()
        ]
    }


def get_top_performers(limit: int = 10):
    """
    FR-90: Top performing startups by activity.
    """
    # Get startups with most documents
    from sqlalchemy import func
    
    top_by_documents = db.session.query(
        Startup.id, Startup.name, func.count(BusinessDocument.id).label('doc_count')
    ).join(BusinessDocument).group_by(Startup.id).order_by(
        db.desc('doc_count')
    ).limit(limit).all()
    
    # Get startups with valuations
    top_by_valuations = db.session.query(
        Startup.id, Startup.name, func.count(Valuation.id).label('val_count')
    ).join(Valuation).group_by(Startup.id).order_by(
        db.desc('val_count')
    ).limit(limit).all()
    
    return {
        "by_documents": [
            {"startup_id": s.id, "startup_name": s.name, "count": s.doc_count}
            for s in top_by_documents
        ],
        "by_valuations": [
            {"startup_id": s.id, "startup_name": s.name, "count": s.val_count}
            for s in top_by_valuations
        ]
    }


def generate_stakeholder_report(program_id: int = None):
    """
    FR-91: Generate comprehensive report for SSDP stakeholders.
    """
    overview = get_platform_overview()
    growth = get_growth_metrics(30)
    programs = get_program_analytics()
    billing = get_billing_analytics()
    top_performers = get_top_performers(5)
    
    report = {
        "report_title": "Agrico Hub SSDP Platform Report",
        "generated_at": datetime.now().isoformat(),
        "reporting_period": "Last 30 days",
        "executive_summary": {
            "total_startups_supported": overview['startups']['total'],
            "verified_startups": overview['startups']['verified'],
            "documents_generated": overview['activity']['documents_generated'],
            "valuations_completed": overview['activity']['valuations_completed'],
            "investor_connections": overview['connections']['accepted']
        },
        "platform_metrics": overview,
        "growth_metrics": growth,
        "program_performance": programs,
        "financial_metrics": billing,
        "success_stories": top_performers,
        "recommendations": [
            "Continue onboarding agritech startups to increase platform adoption",
            "Focus on verification completion to improve investor trust",
            "Expand investor network to increase connection success rate",
            "Develop targeted support for startups in Early stage"
        ]
    }
    
    return report