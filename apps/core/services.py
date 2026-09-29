"""
ConfigService — the single source of truth for runtime configuration.

All apps should read config through this service, never directly from models.
This ensures:
  1. Caching (no N+1 queries)
  2. Fallback to constants.py if DB is empty
  3. Automatic cache invalidation on config change
  4. Type-safe accessors

Usage:
    from apps.core.services import ConfigService

    depts = ConfigService.departments()
    sla = ConfigService.sla_for('complaint', 'urgent')
    threshold = ConfigService.get_setting('attendance.threshold_pct', 75.0)
"""
import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any

from django.db.models import Q

from .models import (
    Department, PriorityLevel, TicketType, SLAPolicy,
    SystemSetting, AIPromptTemplate, NotificationTemplate,
)

logger = logging.getLogger(__name__)


# =====================================================================
# Internal cache
# =====================================================================
# Simple module-level cache with explicit invalidation.
# If you later move to Redis, swap this for django.core.cache.

_CACHE = {
    'departments': None,
    'active_departments': None,
    'priorities': None,
    'ticket_types': None,
    'sla_map': None,
    'settings_map': None,
}


def invalidate_cache(*args, **kwargs):
    """
    Clear the config cache. Called from signals when any config model saves.
    """
    for key in _CACHE:
        _CACHE[key] = None
    logger.debug('ConfigService cache invalidated')


# =====================================================================
# ConfigService
# =====================================================================
class ConfigService:

    # -----------------------------------------------------------------
    # Departments
    # -----------------------------------------------------------------
    @classmethod
    def departments(cls, active_only: bool = True) -> List[Department]:
        """Return all departments (cached)."""
        cache_key = 'active_departments' if active_only else 'departments'
        if _CACHE[cache_key] is None:
            qs = Department.objects.all().order_by('sort_order', 'name')
            if active_only:
                qs = qs.filter(is_active=True)
            _CACHE[cache_key] = list(qs)
        return _CACHE[cache_key]

    @classmethod
    def department_by_code(cls, code: str) -> Optional[Department]:
        for d in cls.departments(active_only=False):
            if d.code == code:
                return d
        return None

    @classmethod
    def department_by_id(cls, dept_id: int) -> Optional[Department]:
        for d in cls.departments(active_only=False):
            if d.id == dept_id:
                return d
        return None

    # -----------------------------------------------------------------
    # Priorities
    # -----------------------------------------------------------------
    @classmethod
    def priority_levels(cls, active_only: bool = True) -> List[PriorityLevel]:
        if _CACHE['priorities'] is None:
            qs = PriorityLevel.objects.all().order_by('-weight')
            if active_only:
                qs = qs.filter(is_active=True)
            _CACHE['priorities'] = list(qs)
        return _CACHE['priorities']

    @classmethod
    def priority_by_code(cls, code: str) -> Optional[PriorityLevel]:
        for p in cls.priority_levels(active_only=False):
            if p.code == code:
                return p
        return None

    # -----------------------------------------------------------------
    # Ticket Types
    # -----------------------------------------------------------------
    @classmethod
    def ticket_types(cls, active_only: bool = True) -> List[TicketType]:
        if _CACHE['ticket_types'] is None:
            qs = TicketType.objects.all().order_by('sort_order', 'name')
            if active_only:
                qs = qs.filter(is_active=True)
            _CACHE['ticket_types'] = list(qs)
        return _CACHE['ticket_types']

    @classmethod
    def ticket_type_by_code(cls, code: str) -> Optional[TicketType]:
        for t in cls.ticket_types(active_only=False):
            if t.code == code:
                return t
        return None

    # -----------------------------------------------------------------
    # SLA Policies
    # -----------------------------------------------------------------
    @classmethod
    def _sla_map(cls) -> Dict:
        """
        Build a dict of (ticket_type_code, priority_code) -> SLAPolicy.
        """
        if _CACHE['sla_map'] is None:
            policies = (
                SLAPolicy.objects
                .filter(is_active=True)
                .select_related('ticket_type', 'priority', 'escalation_target')
            )
            _CACHE['sla_map'] = {
                (p.ticket_type.code, p.priority.code): p
                for p in policies
            }
        return _CACHE['sla_map']

    @classmethod
    def sla_for(cls, ticket_type_code: str, priority_code: str) -> Optional[SLAPolicy]:
        """Return the SLA policy for a (ticket_type, priority) pair."""
        return cls._sla_map().get((ticket_type_code, priority_code))

    @classmethod
    def sla_hours_for(cls, ticket_type_code: str, priority_code: str) -> Dict:
        """
        Return {green, yellow, red, escalate_after} in hours.
        Falls back to ticket_type.sla_hours * priority.sla_multiplier if no policy.
        """
        policy = cls.sla_for(ticket_type_code, priority_code)
        if policy:
            return {
                'green': policy.green_hours,
                'yellow': policy.yellow_hours,
                'red': policy.red_hours,
                'escalate_after': policy.escalation_after_hours,
                'auto_escalate': policy.auto_escalate,
                'escalation_target_id': (
                    policy.escalation_target_id if policy.escalation_target else None
                ),
            }

        # Fallback: derive from ticket_type + priority
        tt = cls.ticket_type_by_code(ticket_type_code)
        prio = cls.priority_by_code(priority_code)
        if not tt or not prio:
            return {'green': 24, 'yellow': 48, 'red': 72,
                    'escalate_after': 72, 'auto_escalate': False,
                    'escalation_target_id': None}

        base = tt.sla_hours
        mult = float(prio.sla_multiplier or 1)
        adjusted = max(1, int(base * mult))
        return {
            'green': max(1, adjusted // 4),
            'yellow': max(1, adjusted // 2),
            'red': adjusted,
            'escalate_after': adjusted,
            'auto_escalate': False,
            'escalation_target_id': None,
        }

    # -----------------------------------------------------------------
    # Routing (used by AI / classifier)
    # -----------------------------------------------------------------
    @classmethod
    def route_to_department(cls, text: str) -> Optional[Department]:
        """
        Return the best-matching department for a given text.

        Uses keywords defined per department. Scores by number of matches.
        Returns None if nothing matches.
        """
        if not text:
            return None
        text_l = text.lower()
        scores = {}
        for dept in cls.departments(active_only=True):
            if not dept.auto_route_enabled:
                continue
            keywords = dept.all_keywords()  # includes children's keywords
            score = sum(1 for kw in keywords if kw and kw.lower() in text_l)
            if score > 0:
                scores[dept] = score

        if not scores:
            return None

        # Highest score wins; ties broken by sort_order then name
        best = max(scores.items(), key=lambda kv: (kv[1], -kv[0].sort_order))
        return best[0]

    # -----------------------------------------------------------------
    # System Settings
    # -----------------------------------------------------------------
    @classmethod
    def _settings_map(cls) -> Dict[str, Any]:
        if _CACHE['settings_map'] is None:
            _CACHE['settings_map'] = {
                s.key: s.value for s in SystemSetting.objects.all()
            }
        return _CACHE['settings_map']

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        """Read a system setting by key with fallback default."""
        return cls._settings_map().get(key, default)

    @classmethod
    def get_attendance_threshold(cls) -> float:
        return float(cls.get_setting('attendance.threshold_pct', 75.0))

    # -----------------------------------------------------------------
    # AI Prompt Templates
    # -----------------------------------------------------------------
    @classmethod
    def get_active_prompt(cls, key: str) -> Optional[AIPromptTemplate]:
        """Return the active prompt template for a given key."""
        return (
            AIPromptTemplate.objects
            .filter(key=key, is_active=True)
            .first()
        )

    # -----------------------------------------------------------------
    # Notification Templates
    # -----------------------------------------------------------------
    @classmethod
    def get_notification_template(
        cls, event_code: str, channel: str, language: str = 'en'
    ) -> Optional[NotificationTemplate]:
        # Try exact (event, channel, language)
        tpl = NotificationTemplate.objects.filter(
            event_code=event_code,
            channel=channel,
            language=language,
            is_active=True,
        ).first()
        if tpl:
            return tpl

        # Fallback to English
        if language != 'en':
            tpl = NotificationTemplate.objects.filter(
                event_code=event_code,
                channel=channel,
                language='en',
                is_active=True,
            ).first()
        return tpl

    # -----------------------------------------------------------------
    # Convenience: helpers for templates & views
    # -----------------------------------------------------------------
    @classmethod
    def department_choices(cls) -> List[tuple]:
        """Return [(code, name), ...] for use in forms."""
        return [(d.code, f"{d.icon} {d.name}") for d in cls.departments()]

    @classmethod
    def priority_choices(cls) -> List[tuple]:
        return [(p.code, f"{p.icon} {p.name}") for p in cls.priority_levels()]

    @classmethod
    def ticket_type_choices(cls) -> List[tuple]:
        return [(t.code, f"{t.icon} {t.name}") for t in cls.ticket_types()]