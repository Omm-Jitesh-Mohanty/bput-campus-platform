"""
SOS escalation engine.

Algorithm:
  1. On trigger, build priority-ordered contact list (custom + system defaults).
  2. Call first contact. If no ack within N seconds, call next.
  3. Once a contact acknowledges, stop.
  4. Log everything.
"""

import logging
import threading
from time import sleep

from django.utils import timezone

from .models import EmergencyAlert, EmergencyContact
from .providers import get_call_provider
from .voice import compose_message, synthesize_voice


logger = logging.getLogger(__name__)


CALL_ACK_WINDOW = 30
MAX_ATTEMPTS = 2


def build_call_list(alert):
    """
    Return ordered list of {name, phone, source} to call.
    Priority: user's custom contacts (1, 2, 3...) then system defaults.
    """
    user = alert.user
    contacts = []

    # 1. User's saved emergency contacts
    for c in EmergencyContact.objects.filter(user=user).order_by('priority'):
        contacts.append({
            'name': c.name,
            'phone': c.phone,
            'relation': c.relation,
            'source': 'custom',
        })

    # 2. System defaults (warden for their block, security desk)
    if user.hostel_block:
        from apps.accounts.models import User

        warden = User.objects.filter(
            role='warden',
            hostel_block=user.hostel_block,
        ).first()

        if warden and warden.phone:
            contacts.append({
                'name': warden.get_full_name() or warden.username,
                'phone': warden.phone,
                'relation': 'warden',
                'source': 'system',
            })

    # 3. Campus security (a system setting)
    from apps.core.services import ConfigService

    security_phone = ConfigService.get_setting(
        'sos.security_phone',
        '',
    )

    if security_phone:
        contacts.append({
            'name': 'Campus Security',
            'phone': security_phone,
            'relation': 'security',
            'source': 'system',
        })

    return contacts


def trigger_alert(user, trigger_type='sos_button', reason='', location=''):
    """Create an alert and start the escalation thread."""

    alert = EmergencyAlert.objects.create(
        user=user,
        trigger_type=trigger_type,
        reason=reason,
        location=location or f"Hostel {user.hostel_block}-{user.room_number}",
        status='triggered',
    )

    # Fire escalation in background
    thread = threading.Thread(
        target=_run_escalation,
        args=(alert.id,),
    )

    thread.daemon = True
    thread.start()

    return alert


def _run_escalation(alert_id):
    """Background worker: call contacts in order until ack."""

    try:
        alert = EmergencyAlert.objects.get(pk=alert_id)
    except EmergencyAlert.DoesNotExist:
        return

    provider = get_call_provider()

    message = compose_message(alert)
    voice_file = synthesize_voice(message)

    contacts = build_call_list(alert)

    if not contacts:
        alert.status = 'failed'
        alert.call_log = [
            {'error': 'no contacts available'}
        ]
        alert.save()

        logger.error(
            f"SOS #{alert.id}: no contacts available"
        )

        return

    alert.status = 'calling'
    alert.save(
        update_fields=['status', 'updated_at']
    )

    log = list(alert.call_log or [])

    for contact in contacts:

        for attempt in range(MAX_ATTEMPTS):

            # Reload to check if acknowledged meanwhile
            alert.refresh_from_db()

            if alert.status == 'acknowledged':
                logger.info(
                    f"SOS #{alert.id}: acknowledged, stopping"
                )
                return

            logger.info(
                f"SOS #{alert.id}: calling "
                f"{contact['name']} "
                f"({contact['phone']}) "
                f"attempt {attempt + 1}"
            )

            result = provider.call(
                to_phone=contact['phone'],
                message_text=message,
                voice_file=voice_file,
                alert_id=alert.id,
            )

            log.append({
                'contact_name': contact['name'],
                'phone': contact['phone'],
                'relation': contact.get('relation', ''),
                'source': contact['source'],
                'attempt': attempt + 1,
                'at': timezone.now().isoformat(),
                'result': result,
            })

            alert.call_log = log
            alert.save(
                update_fields=['call_log', 'updated_at']
            )

            # Wait for potential ack
            sleep(CALL_ACK_WINDOW)

        # Moved to next contact — this one didn't ack

    # Nobody acknowledged
    alert.refresh_from_db()

    if alert.status not in ('acknowledged', 'resolved'):
        alert.status = 'failed'

        alert.save(
            update_fields=['status', 'updated_at']
        )

        logger.error(
            f"SOS #{alert.id}: nobody acknowledged"
        )


def acknowledge_alert(alert_id, user, note=''):
    """Mark an alert as acknowledged (stops escalation)."""

    try:
        alert = EmergencyAlert.objects.get(pk=alert_id)
    except EmergencyAlert.DoesNotExist:
        return None

    alert.status = 'acknowledged'
    alert.acknowledged_by = user
    alert.acknowledged_at = timezone.now()

    if note:
        alert.resolution_note = note

    alert.save()

    return alert


def resolve_alert(alert_id, user, note=''):
    """Mark an alert as resolved."""

    try:
        alert = EmergencyAlert.objects.get(pk=alert_id)
    except EmergencyAlert.DoesNotExist:
        return None

    alert.status = 'resolved'
    alert.resolved_at = timezone.now()

    if note:
        alert.resolution_note = note

    alert.save()

    return alert