"""
Unified PowerBI-style executive dashboard.
"""

import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import User
from apps.core.permissions import require_perm, Perm
from apps.core.services import ConfigService
from apps.tickets.models import CampusTicket

from ai_engine.llm.ollama_client import generate_text
from ai_engine.prompts import (
    EXECUTIVE_SYSTEM,
    build_executive_prompt,
    fallback_executive_recommendations,
)

from . import analytics_v2 as A


logger = logging.getLogger(__name__)


def _normalize_ai_recommendations(data):
    """
    Validate and normalize LLM-generated recommendations.
    """

    if not isinstance(data, dict):
        return []

    recommendations = data.get("recommendations", [])

    if not isinstance(recommendations, list):
        return []

    allowed_priorities = {
        "critical",
        "high",
        "medium",
        "low",
    }

    cleaned = []

    for item in recommendations[:5]:

        if not isinstance(item, dict):
            continue

        title = str(
            item.get("title", "")
        ).strip()

        priority = str(
            item.get("priority", "medium")
        ).strip().lower()

        evidence = str(
            item.get("evidence", "")
        ).strip()

        action = str(
            item.get("action", "")
        ).strip()

        if not title or not evidence or not action:
            continue

        if priority not in allowed_priorities:
            priority = "medium"

        cleaned.append({
            "title": title[:80],
            "priority": priority,
            "evidence": evidence[:180],
            "action": action[:220],
        })

    return cleaned


def _generate_ai_recommendations(dashboard_data):
    """
    Generate executive recommendations using the existing Ollama engine.

    Falls back to rule-based recommendations when the LLM is unavailable
    or returns invalid JSON.
    """

    fallback = fallback_executive_recommendations(
        kpis=dashboard_data.get("kpis"),
        dept_performance=dashboard_data.get("dept_performance"),
        ageing=dashboard_data.get("ageing"),
        academic_risk=dashboard_data.get("academic_risk"),
        complaint_intel=dashboard_data.get("complaint_intel"),
        notice_intel=dashboard_data.get("notice_intel"),
        feedback_intel=dashboard_data.get("feedback_intel"),
        bottlenecks=dashboard_data.get("bottlenecks"),
    )

    try:

        prompt = build_executive_prompt(
            kpis=dashboard_data.get("kpis"),
            type_breakdown=dashboard_data.get("type_breakdown"),
            volume_trend=dashboard_data.get("volume_trend"),
            dept_performance=dashboard_data.get("dept_performance"),
            ageing=dashboard_data.get("ageing"),
            bottlenecks=dashboard_data.get("bottlenecks"),
            academic_risk=dashboard_data.get("academic_risk"),
            complaint_intel=dashboard_data.get("complaint_intel"),
            notice_intel=dashboard_data.get("notice_intel"),
            feedback_intel=dashboard_data.get("feedback_intel"),
        )

        response = generate_text(
            prompt,
            system=EXECUTIVE_SYSTEM,
            json_mode=True,
            temperature=0.2,
            max_tokens=100,
        )

        if not response.success or not response.text:
            logger.warning(
                "Executive AI recommendation generation returned no response."
            )
            return {
                "recommendations": fallback.get(
                    "recommendations",
                    []
                ),
                "source": "fallback",
            }

        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.replace(
                "```json",
                "",
                1,
            ).replace(
                "```",
                "",
            ).strip()

        parsed = json.loads(raw_text)

        recommendations = _normalize_ai_recommendations(
            parsed
        )

        if not recommendations:
            logger.warning(
                "Executive AI returned no valid recommendations."
            )

            return {
                "recommendations": fallback.get(
                    "recommendations",
                    []
                ),
                "source": "fallback",
            }

        return {
            "recommendations": recommendations,
            "source": "llm",
            "model": getattr(
                response,
                "model",
                "",
            ),
            "latency_ms": getattr(
                response,
                "latency_ms",
                0,
            ),
        }

    except json.JSONDecodeError as exc:

        logger.warning(
            "Executive AI returned invalid JSON: %s",
            exc,
        )

    except Exception as exc:

        logger.warning(
            "Executive AI recommendation generation failed: %s",
            exc,
        )

    return {
        "recommendations": fallback.get(
            "recommendations",
            []
        ),
        "source": "fallback",
    }


def _build_dashboard_data(qs, filters):
    """
    Build all dashboard intelligence in one place.
    """

    return {
        "kpis": A.compute_kpis(qs),

        "type_breakdown": A.requests_by_type(qs),

        "volume_trend": A.request_volume_trend(
            qs,
            days=int(filters.get("days") or 30),
        ),

        "dept_performance": A.department_performance(qs)[:8],

        "ageing": A.ageing_buckets(qs),

        "bottlenecks": A.workflow_bottlenecks(qs),

        "academic_risk": A.academic_risk(
            filters.get("batch")
        ),

        "complaint_intel": A.complaint_intelligence(qs),

        "notice_intel": A.notice_intelligence(),

        "feedback_intel": A.feedback_intelligence(),
    }


def _get_ai_recommendations(dashboard_data, filters):
    """
    Return cached AI recommendations for the current dashboard filters.

    Recommendations are generated again whenever the dashboard filter
    combination changes or the cache expires.
    """

    ai_cache_key = "exec_ai_v2_" + "_".join(
        f"{key}={filters.get(key, '')}"
        for key in [
            "days",
            "department",
            "batch",
            "type",
            "priority",
            "status",
            "authority",
            "hostel",
        ]
    )

    cached = cache.get(ai_cache_key)

    if cached is not None:
        return cached

    recommendations = _generate_ai_recommendations(
        dashboard_data
    )

    cache.set(
        ai_cache_key,
        recommendations,
        timeout=180,
    )

    return recommendations


@require_perm(Perm.VIEW_ADMIN_DASHBOARD)
def executive_view(request):
    """
    PowerBI-style Principal Command Center dashboard.
    """

    filters = {
        "days": request.GET.get("days", "30"),
        "department": request.GET.get("department", ""),
        "batch": request.GET.get("batch", ""),
        "type": request.GET.get("type", ""),
        "priority": request.GET.get("priority", ""),
        "status": request.GET.get("status", ""),
        "authority": request.GET.get("authority", ""),
        "hostel": request.GET.get("hostel", ""),
    }

    cache_key = "exec_dash_v4_" + "_".join(
        f"{key}={value}"
        for key, value in filters.items()
    )

    cached = cache.get(cache_key)

    if cached is None:

        qs = CampusTicket.objects.filter(
            is_deleted=False
        )

        qs = A.apply_dashboard_filters(
            qs,
            filters,
        )

        cached = _build_dashboard_data(
            qs,
            filters,
        )

        cache.set(
            cache_key,
            cached,
            timeout=180,
        )

    ai_recommendations = _get_ai_recommendations(
        cached,
        filters,
    )

    filter_options = {
        "departments": ConfigService.department_choices(),

        "batches": [
            ("2022", "2022"),
            ("2023", "2023"),
            ("2024", "2024"),
            ("2025", "2025"),
            ("2026", "2026"),
        ],

        "types": ConfigService.ticket_type_choices(),

        "priorities": ConfigService.priority_choices(),

        "statuses": [
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
            ("reopened", "Reopened"),
        ],

        "authorities": [
            (
                u.username,
                u.get_full_name() or u.username,
            )
            for u in User.objects.filter(
                role__in=[
                    "chairman",
                    "director",
                    "principal",
                    "dean",
                    "ao",
                    "hod",
                    "warden",
                    "asst_prof",
                    "teacher",
                    "lab_asst",
                    "clerk",
                ]
            ).order_by(
                "role",
                "first_name",
                "last_name",
                "username",
            )
        ],

        "hostels": [
            ("A", "Block A"),
            ("B", "Block B"),
            ("C", "Block C"),
            ("D", "Block D"),
            ("DAY", "Day Scholar"),
        ],
    }

    context = {
        **cached,

        "ai_recommendations": ai_recommendations,

        "filters": filters,

        "filter_options": filter_options,

        "user": request.user,

        "last_updated": timezone.now(),
    }

    return render(
        request,
        "dashboard/executive.html",
        context,
    )


@require_perm(Perm.VIEW_ADMIN_DASHBOARD)
def dashboard_data_ajax(request):
    """
    AJAX endpoint for live dashboard filter updates.
    """

    filters = {
        key: request.GET.get(key, "")
        for key in [
            "days",
            "department",
            "batch",
            "type",
            "priority",
            "status",
            "authority",
            "hostel",
        ]
    }

    qs = CampusTicket.objects.filter(
        is_deleted=False
    )

    qs = A.apply_dashboard_filters(
        qs,
        filters,
    )

    dashboard_data = _build_dashboard_data(
        qs,
        filters,
    )

    ai_recommendations = _get_ai_recommendations(
        dashboard_data,
        filters,
    )

    return JsonResponse({
        **dashboard_data,

        "ai_recommendations": ai_recommendations,

        "last_updated": timezone.now().isoformat(),
    })