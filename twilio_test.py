from dotenv import load_dotenv
load_dotenv()

import os
from twilio.rest import Client

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]

client = Client(account_sid, auth_token)

call = client.calls.create(
    twiml="<Response><Say>This is a test emergency SOS call from BPUT Campus Platform.</Say></Response>",
    to="+919348492941",
    from_="+13313069430",
)

print("Call started successfully!")
print("Call SID:", call.sid)