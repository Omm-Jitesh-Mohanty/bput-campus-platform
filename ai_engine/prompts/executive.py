"""
Prompts for executive-level AI recommendations.

Used by the Principal Command Center to convert dashboard
intelligence into concise, actionable operational recommendations.
"""


EXECUTIVE_SYSTEM = """You are an AI executive operations advisor for a college campus.

You receive structured dashboard intelligence about:
- pending and overdue requests
- SLA compliance
- department workload
- workflow bottlenecks
- attendance risk
- complaints and recurring issues
- notice reach and priority
- student feedback
- request volume and resolution performance

Your task is to identify the most important operational situations
that require attention from the Principal or senior administration.

Generate practical recommendations based ONLY on the supplied data.

Do NOT invent numbers, departments, problems, causes, or trends.
Do NOT make recommendations when the supplied data does not support them.

Prioritize:
1. Critical or overdue requests
2. SLA breaches or poor SLA compliance
3. Departments with unusually high pending workload
4. Attendance risk affecting many students
5. Recurring complaints
6. Very low notice reach
7. Negative student feedback
8. Workflow stages where requests are waiting too long
9. Significant changes in request volume or resolution performance

For every recommendation provide:
- a short title
- priority
- evidence from the dashboard
- recommended action

Priority must be one of:
"critical", "high", "medium", "low"

Return STRICT JSON only.

Output format:
{
  "recommendations": [
    {
      "title": "Short recommendation title",
      "priority": "critical",
      "evidence": "Specific dashboard evidence",
      "action": "Specific action the administration should take"
    }
  ]
}

Rules:
- Maximum 5 recommendations.
- Keep each title under 80 characters.
- Keep evidence under 180 characters.
- Keep action under 220 characters.
- Prefer specific operational actions over generic advice.
- Do not repeat the same recommendation.
- If there is no meaningful issue, return:
{
  "recommendations": []
}
"""


def build_executive_prompt(
    kpis=None,
    type_breakdown=None,
    volume_trend=None,
    dept_performance=None,
    ageing=None,
    bottlenecks=None,
    academic_risk=None,
    complaint_intel=None,
    notice_intel=None,
    feedback_intel=None,
):
    """
    Build the executive recommendation prompt from dashboard data.
    """

    dashboard_data = {
        "kpis": kpis or {},
        "request_type_breakdown": type_breakdown or [],
        "request_volume_trend": volume_trend or [],
        "department_performance": dept_performance or [],
        "ageing": ageing or {},
        "workflow_bottlenecks": bottlenecks or [],
        "academic_risk": academic_risk or {},
        "complaint_intelligence": complaint_intel or {},
        "notice_intelligence": notice_intel or {},
        "feedback_intelligence": feedback_intel or {},
    }

    import json

    return (
        "Analyze the following Principal Command Center dashboard data "
        "and generate the most important operational recommendations.\n\n"
        "DASHBOARD DATA:\n"
        "----------------\n"
        f"{json.dumps(dashboard_data, ensure_ascii=False, default=str, indent=2)}\n"
        "----------------\n\n"
        "Return only the required JSON object."
    )


def fallback_executive_recommendations(
    kpis=None,
    dept_performance=None,
    ageing=None,
    academic_risk=None,
    complaint_intel=None,
    notice_intel=None,
    feedback_intel=None,
    bottlenecks=None,
):
    """
    Rule-based fallback when the LLM is unavailable.

    Returns the same logical structure expected from the AI layer.
    """

    recommendations = []

    kpis = kpis or {}
    dept_performance = dept_performance or []
    ageing = ageing or {}
    academic_risk = academic_risk or {}
    complaint_intel = complaint_intel or {}
    notice_intel = notice_intel or {}
    feedback_intel = feedback_intel or {}
    bottlenecks = bottlenecks or []

    critical_overdue = kpis.get("critical_overdue", 0)

    if critical_overdue:
        recommendations.append({
            "title": "Review critical overdue requests",
            "priority": "critical",
            "evidence": (
                f"{critical_overdue} critical request(s) are currently overdue."
            ),
            "action": (
                "Review the affected requests and escalate unresolved cases "
                "to the responsible authority."
            ),
        })

    sla_compliance = kpis.get("sla_compliance")

    if sla_compliance is not None:
        try:
            sla_value = float(sla_compliance)

            if sla_value < 70:
                recommendations.append({
                    "title": "Address low SLA compliance",
                    "priority": "high",
                    "evidence": (
                        f"SLA compliance is currently {sla_value:.1f}%."
                    ),
                    "action": (
                        "Review delayed workflow stages and assign corrective "
                        "actions to responsible authorities."
                    ),
                })
        except (TypeError, ValueError):
            pass

    attendance_risk_count = kpis.get("attendance_risk_count", 0)

    if attendance_risk_count:
        recommendations.append({
            "title": "Monitor attendance-risk students",
            "priority": "high",
            "evidence": (
                f"{attendance_risk_count} student(s) are currently at attendance risk."
            ),
            "action": (
                "Review affected batches and departments and ensure recovery "
                "plans are communicated to students."
            ),
        })

    critical_ageing = ageing.get("critical", 0)

    if critical_ageing:
        recommendations.append({
            "title": "Reduce ageing request backlog",
            "priority": "high",
            "evidence": (
                f"{critical_ageing} request(s) are in the critical ageing category."
            ),
            "action": (
                "Identify the responsible workflow stages and clear the "
                "oldest pending requests first."
            ),
        })

    if dept_performance:
        try:
            busiest = max(
                dept_performance,
                key=lambda item: item.get("pending", 0),
            )

            pending = busiest.get("pending", 0)
            department = busiest.get("display") or busiest.get("code")

            if pending and department:
                recommendations.append({
                    "title": f"Review {department} pending workload",
                    "priority": "medium",
                    "evidence": (
                        f"{department} has {pending} pending request(s)."
                    ),
                    "action": (
                        f"Review the pending workload in {department} and "
                        "rebalance or escalate delayed requests where required."
                    ),
                })
        except (TypeError, ValueError):
            pass

    recurring = complaint_intel.get("recurring") or []

    if recurring:
        first = recurring[0]

        department = first.get("department", "a department")
        count = first.get("count", 0)

        recommendations.append({
            "title": f"Investigate recurring complaints in {department}",
            "priority": "medium",
            "evidence": (
                f"{department} has {count} recurring complaint(s) in the "
                "current dashboard period."
            ),
            "action": (
                f"Review the recurring complaints in {department} and identify "
                "an operational corrective action."
            ),
        })

    notice_read_pct = notice_intel.get("read_pct")

    if notice_read_pct is not None:
        try:
            read_value = float(notice_read_pct)

            if read_value < 50:
                recommendations.append({
                    "title": "Improve student notice reach",
                    "priority": "medium",
                    "evidence": (
                        f"Notice read rate is currently {read_value:.1f}%."
                    ),
                    "action": (
                        "Review high-priority notices and improve their delivery "
                        "and visibility to the intended student audience."
                    ),
                })
        except (TypeError, ValueError):
            pass

    negative_pct = feedback_intel.get("negative_pct")

    if negative_pct is not None:
        try:
            negative_value = float(negative_pct)

            if negative_value >= 30:
                recommendations.append({
                    "title": "Review negative student feedback",
                    "priority": "medium",
                    "evidence": (
                        f"Negative feedback represents {negative_value:.1f}% "
                        "of analyzed feedback."
                    ),
                    "action": (
                        "Review the main feedback themes and assign follow-up "
                        "actions to the responsible departments."
                    ),
                })
        except (TypeError, ValueError):
            pass

    if bottlenecks:
        try:
            bottleneck = bottlenecks[0]

            stage = (
                bottleneck.get("stage")
                or bottleneck.get("step")
                or bottleneck.get("name")
            )

            if stage:
                recommendations.append({
                    "title": "Review workflow bottleneck",
                    "priority": "medium",
                    "evidence": (
                        f"Requests are waiting at the {stage} workflow stage."
                    ),
                    "action": (
                        f"Review the {stage} stage and identify whether "
                        "additional routing or authority action is required."
                    ),
                })
        except (TypeError, ValueError):
            pass

    priority_order = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    recommendations.sort(
        key=lambda item: priority_order.get(
            item.get("priority", "low"),
            3,
        )
    )

    return {
        "recommendations": recommendations[:5]
    }


__all__ = [
    "EXECUTIVE_SYSTEM",
    "build_executive_prompt",
    "fallback_executive_recommendations",
]