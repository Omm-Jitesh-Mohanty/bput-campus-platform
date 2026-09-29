"""
SMS provider abstraction.

Providers implement `send(phone, message) -> {'ok': bool, 'error': str|None}`.

Currently:
  - LogProvider  (dev/demo — just logs)
  - MSG91Provider (India — requires SMS_API_KEY)
  - TwilioProvider (global — requires keys)

Select via settings.SMS_PROVIDER = 'log' | 'msg91' | 'twilio'
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseSMSProvider:
    name = 'base'

    def send(self, phone, message):
        raise NotImplementedError


class LogSMSProvider(BaseSMSProvider):
    name = 'log'

    def send(self, phone, message):
        logger.info(f"[SMS-LOG] → {phone}: {message}")
        return {'ok': True, 'provider': 'log', 'message_id': None}


class MSG91Provider(BaseSMSProvider):
    name = 'msg91'

    def __init__(self):
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.sender_id = getattr(settings, 'SMS_SENDER_ID', 'CAMPUS')

    def send(self, phone, message):
        if not self.api_key:
            return {'ok': False, 'error': 'MSG91 API key not configured'}

        import requests
        url = 'https://api.msg91.com/api/v5/flow/'
        headers = {
            'authkey': self.api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            'sender': self.sender_id,
            'mobiles': phone,
            'message': message,
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                return {'ok': True, 'provider': 'msg91', 'message_id': r.json().get('message')}
            return {'ok': False, 'error': f'HTTP {r.status_code}'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


class TwilioProvider(BaseSMSProvider):
    name = 'twilio'

    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.from_number = getattr(settings, 'TWILIO_FROM', '')

    def send(self, phone, message):
        if not (self.account_sid and self.auth_token):
            return {'ok': False, 'error': 'Twilio credentials missing'}
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            msg = client.messages.create(body=message, from_=self.from_number, to=phone)
            return {'ok': True, 'provider': 'twilio', 'message_id': msg.sid}
        except Exception as e:
            return {'ok': False, 'error': str(e)}


# =====================================================================
# Factory
# =====================================================================
def get_sms_provider():
    provider_name = getattr(settings, 'SMS_PROVIDER', 'log')
    mapping = {
        'log': LogSMSProvider,
        'msg91': MSG91Provider,
        'twilio': TwilioProvider,
    }
    return mapping.get(provider_name, LogSMSProvider)()