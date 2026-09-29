"""
AuditService — central API for recording audit events.

Usage:
    from apps.core.audit import AuditService

    AuditService.record(
        action='update',
        target=some_object,
        changes={'name': {'old': 'A', 'new': 'B'}},
    )

    # Or use the specialized helpers:
    AuditService.log_config_change(old_instance, new_instance, user=request.user)
    AuditService.log_action('resolve', target=ticket, metadata={'note': '...'})

Never raises. Errors are logged but never propagated.
"""
import logging
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction

from .models import AuditLog
from .middleware import (
    get_current_user, get_client_ip, get_user_agent,
)

logger = logging.getLogger(__name__)


class AuditService:

    # =================================================================
    # Core API
    # =================================================================
    @classmethod
    def record(
        cls,
        action: str,
        target=None,
        target_model: str = '',
        target_id: str = '',
        target_repr: str = '',
        changes: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        user=None,
    ) -> Optional[AuditLog]:
        """
        Record an audit event.

        All arguments are optional except `action`. Context is auto-filled
        from the request if available.
        """
        try:
            # Derive target info from object if provided
            if target is not None:
                target_model = target._meta.label  # e.g., "core.Department"
                target_id = str(target.pk)
                target_repr = str(target)[:200]

            # Auto-fill user/IP/UA from request if not provided
            if user is None:
                user = get_current_user()

            entry = AuditLog.objects.create(
                action=action,
                user=user if (user and user.is_authenticated) else None,
                target_model=target_model,
                target_id=target_id,
                target_repr=target_repr,
                changes=changes or {},
                metadata=metadata or {},
                ip_address=get_client_ip(),
                user_agent=get_user_agent(),
            )
            return entry

        except Exception as e:
            # Audit must NEVER break the app.
            logger.exception(f"Audit record failed: {e}")
            return None

    # =================================================================
    # Specialized Helpers
    # =================================================================
    @classmethod
    def log_config_change(
        cls,
        instance,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        user=None,
    ) -> Optional[AuditLog]:
        """
        Log a config model update with a diff of changed fields.
        """
        changes = {}
        for field, new_val in new_values.items():
            old_val = old_values.get(field)
            if old_val != new_val:
                changes[field] = {
                    'old': _serialize(old_val),
                    'new': _serialize(new_val),
                }

        if not changes:
            return None  # nothing actually changed

        return cls.record(
            action='config_change',
            target=instance,
            changes=changes,
            user=user,
        )

    @classmethod
    def log_action(
        cls,
        action: str,
        target=None,
        metadata: Optional[Dict] = None,
        user=None,
    ) -> Optional[AuditLog]:
        """Log a domain action (resolve, escalate, approve, etc.)."""
        return cls.record(
            action=action,
            target=target,
            metadata=metadata or {},
            user=user,
        )

    @classmethod
    def log_login(cls, user, success: bool = True, reason: str = '') -> Optional[AuditLog]:
        """Log login attempt."""
        return cls.record(
            action='login',
            metadata={
                'success': success,
                'reason': reason,
            },
            user=user if success else None,
        )

    @classmethod
    def log_logout(cls, user) -> Optional[AuditLog]:
        return cls.record(action='logout', user=user)


# =====================================================================
# Serialization helper
# =====================================================================
def _serialize(value):
    """
    Convert Python objects to JSON-safe values for storage.
    Handles: datetime, Decimal, Model, list, dict, set, etc.
    """
    from decimal import Decimal
    from django.db.models import Model
    from datetime import datetime, date

    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Model):
        return f"{value._meta.label}#{value.pk}"
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(str(v) for v in value)
    return str(value)