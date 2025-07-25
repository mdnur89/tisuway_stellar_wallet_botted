import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "users.db")

# Debug
DEBUG = os.getenv("DEBUG")