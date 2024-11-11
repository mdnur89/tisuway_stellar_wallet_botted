import os
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from functools import wraps
from flask import request
from config import DEBUG

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Validate Twilio request
def validate_twilio_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        request_valid = validator.validate(
            request.url, request.form, request.headers.get("X-Twilio-Signature", "")
        )

        if not request_valid and not DEBUG:
            return "Invalid request", 403
        return f(*args, **kwargs)

    return decorated_function
