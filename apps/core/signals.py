"""
Signal handlers for:
  1. Cache invalidation (config changes)
  2. Audit logging (config + domain changes)
"""
import logging

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import (
    Department, DepartmentMembership, PriorityLevel, TicketType,
    SLAPolicy, SystemSetting, AIPromptTemplate, NotificationTemplate,
)
from .services import invalidate_cache
from .audit import AuditService

logger = logging.getLogger(__name__)


# =====================================================================
# 1. CACHE INVALIDATION
# =====================================================================
@receiver([post_save, post_delete], sender=Department)
@receiver([post_save, post_delete], sender=DepartmentMembership)
@receiver([post_save, post_delete], sender=PriorityLevel)
@receiver([post_save, post_delete], sender=TicketType)
@receiver([post_save, post_delete], sender=SLAPolicy)
@receiver([post_save, post_delete], sender=SystemSetting)
@receiver([post_save, post_delete], sender=AIPromptTemplate)
@receiver([post_save, post_delete], sender=NotificationTemplate)
def invalidate_config_cache(sender, instance, **kwargs):
    """Any config save/delete clears the whole config cache."""
    invalidate_cache()
    logger.debug(f"Config cache invalidated by {sender.__name__}#{instance.pk}")


# =====================================================================
# 2. AUDIT: PRE_SAVE — capture "old" values before change
# =====================================================================
# We snapshot the DB state in pre_save so post_save can compute a diff.

_AUDIT_SNAPSHOT_ATTR = '_audit_old_snapshot'

AUDITED_MODELS = [
    Department, DepartmentMembership, PriorityLevel, TicketType,
    SLAPolicy, SystemSetting, AIPromptTemplate, NotificationTemplate,
]


def _snapshot_instance(instance):
    """Return dict of field->value from DB (or None for new objects)."""
    if instance.pk is None:
        return None  # new object
    try:
        old = type(instance).objects.get(pk=instance.pk)
    except type(instance).DoesNotExist:
        return None

    snapshot = {}
    for field in instance._meta.fields:
        # Skip auto-managed timestamp fields
        if field.name in ('created_at', 'updated_at'):
            continue
        snapshot[field.name] = getattr(old, field.name)
    return snapshot


def _make_pre_save_handler(model_class):
    """Factory to attach the snapshot logic per model."""
    def handler(sender, instance, **kwargs):
        setattr(instance, _AUDIT_SNAPSHOT_ATTR, _snapshot_instance(instance))
    return handler


def _make_post_save_handler(model_class, action_new='create', action_update='config_change'):
    """Factory to attach audit logging per model."""
    def handler(sender, instance, created, **kwargs):
        try:
            if created:
                AuditService.log_action(
                    action=action_new,
                    target=instance,
                    metadata={'created_via': 'admin_or_api'},
                )
            else:
                old = getattr(instance, _AUDIT_SNAPSHOT_ATTR, None)
                if old is None:
                    return  # no snapshot — skip (e.g., raw save)
                # Build "new" values from current instance
                new = {}
                for field in instance._meta.fields:
                    if field.name in ('created_at', 'updated_at'):
                        continue
                    new[field.name] = getattr(instance, field.name)

                AuditService.log_config_change(
                    instance=instance,
                    old_values=old,
                    new_values=new,
                )
        except Exception as e:
            logger.exception(f"Audit failed on {sender.__name__}: {e}")
    return handler


# Connect pre_save and post_save for each audited model
for model in AUDITED_MODELS:
    pre_save.connect(
        _make_pre_save_handler(model),
        sender=model,
        dispatch_uid=f'audit_pre_save_{model._meta.label}',
    )
    post_save.connect(
        _make_post_save_handler(model),
        sender=model,
        dispatch_uid=f'audit_post_save_{model._meta.label}',
    )


# =====================================================================
# 3. AUDIT: post_delete
# =====================================================================
def _make_post_delete_handler(model_class):
    def handler(sender, instance, **kwargs):
        try:
            AuditService.log_action(
                action='delete',
                target=instance,
                metadata={'deleted_via': 'admin_or_api'},
            )
        except Exception as e:
            logger.exception(f"Audit failed on delete {sender.__name__}: {e}")
    return handler


for model in AUDITED_MODELS:
    post_delete.connect(
        _make_post_delete_handler(model),
        sender=model,
        dispatch_uid=f'audit_post_delete_{model._meta.label}',
    )