"""
Call provider abstraction. Real telephony (Twilio, Exotel) plugs in here.

Default: LogCallProvider — logs calls without actually calling.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def normalize_phone_number(phone):
    phone = str(phone or "").strip().replace(" ", "").replace("-", "")

    if phone.startswith("+"):
        return phone

    if phone.startswith("00"):
        return "+" + phone[2:]

    if phone.startswith("0") and len(phone) == 11:
        return "+91" + phone[1:]

    if len(phone) == 10 and phone.isdigit():
        return "+91" + phone

    if len(phone) == 12 and phone.startswith("91") and phone.isdigit():
        return "+" + phone

    return phone


class BaseCallProvider:
    name = "base"

    def call(self, to_phone, message_text, voice_file=None, alert_id=None):
        """Initiate a call. Return {'ok': bool, 'call_id': str, 'error': str}."""
        raise NotImplementedError


class LogCallProvider(BaseCallProvider):
    name = "log"

    def call(self, to_phone, message_text, voice_file=None, alert_id=None):
        normalized_phone = normalize_phone_number(to_phone)

        logger.warning(
            f"[SOS-LOG] CALLING {normalized_phone}: {message_text[:100]}"
        )

        return {
            "ok": True,
            "call_id": f"log-{normalized_phone}",
            "error": None,
        }


class TwilioCallProvider(BaseCallProvider):
    name = "twilio"

    def call(self, to_phone, message_text, voice_file=None, alert_id=None):
        try:
            from twilio.rest import Client

            sid = settings.TWILIO_ACCOUNT_SID
            token = settings.TWILIO_AUTH_TOKEN
            from_number = settings.TWILIO_FROM
            public_base_url = settings.SOS_PUBLIC_BASE_URL.rstrip("/")

            normalized_phone = normalize_phone_number(to_phone)

            client = Client(sid, token)

            if not public_base_url:
                raise ValueError("SOS_PUBLIC_BASE_URL is not configured.")

            if not alert_id:
                raise ValueError("alert_id is required for Twilio SOS calls.")

            acknowledge_url = (
                f"{public_base_url}/emergency/twilio/{alert_id}/ack/"
            )

            twiml = f"""
            <Response>
                <Say voice="alice" language="en-IN">
                    {message_text}
                </Say>

                <Pause length="1"/>

                <Say voice="alice" language="en-IN">
                    Please press 1 to acknowledge this emergency alert.
                </Say>

                <Gather
                    numDigits="1"
                    timeout="5"
                    action="{acknowledge_url}"
                    method="POST"
                >
                    <Say voice="alice" language="en-IN">
                        Press 1 to acknowledge.
                    </Say>
                </Gather>

                <Say voice="alice" language="en-IN">
                    No acknowledgement received.
                </Say>
            </Response>
            """

            logger.info(
                f"[SOS-TWILIO] Calling normalized number: {normalized_phone}"
            )

            call = client.calls.create(
                twiml=twiml,
                from_=from_number,
                to=normalized_phone,
            )

            logger.warning(
                f"[SOS-TWILIO] CALL {normalized_phone} (sid={call.sid})"
            )

            return {
                "ok": True,
                "call_id": call.sid,
                "error": None,
            }

        except Exception as e:
            logger.exception(f"Twilio call failed: {e}")

            return {
                "ok": False,
                "call_id": None,
                "error": str(e),
            }


def get_call_provider():
    name = getattr(settings, "SOS_PROVIDER", "log")

    return {
        "log": LogCallProvider,
        "twilio": TwilioCallProvider,
    }.get(name, LogCallProvider)()