from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime
import sqlite3
import json
import re
import os
from dotenv import load_dotenv
from functools import wraps
from twilio.request_validator import RequestValidator
from paynow import Paynow
from typing import Dict
import time
import requests
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Initialize Twilio Client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Helper function to send messages
def send_message(to_number, message):
    try:
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        return True
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return False

# Database initialization
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (phone_number TEXT PRIMARY KEY,
                  first_name TEXT,
                  surname TEXT,
                  nationality TEXT,
                  address TEXT,
                  id_type TEXT,
                  id_number TEXT,
                  verification_method TEXT,
                  passcode TEXT,
                  registration_complete BOOLEAN,
                  current_state TEXT,
                  wallet_balance REAL DEFAULT 0.0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone_number TEXT,
                  transaction_type TEXT,
                  amount REAL,
                  timestamp DATETIME,
                  description TEXT)''')
    conn.commit()
    conn.close()

# User state management
class UserState:
    WELCOME = "welcome"
    NAME = "name"
    SURNAME = "surname"
    NATIONALITY = "nationality"
    ADDRESS = "address"
    ID_TYPE = "id_type"
    ID_NUMBER = "id_number"
    VERIFICATION = "verification"
    PASSCODE = "passcode"
    MAIN_MENU = "main_menu"
    WALLET_MENU = "wallet_menu"
    SERVICES_MENU = "services_menu"
    EFT_MENU = "eft_menu"
    VOUCHER_MENU = "voucher_menu"
    BUY_VOUCHER_MENU = "buy_voucher_menu"
    ZIM_SERVICES_MENU = "zim_services_menu"
    AIRTIME_MENU = "airtime_menu"
    DATA_MENU = "data_menu"
    DSTV_MENU = "dstv_menu"
    ZESA_MENU = "zesa_menu"
    ECOCASH_PHONE = "ecocash_phone"
    ECOCASH_AMOUNT = "ecocash_amount"
    ECOCASH_CONFIRM = "ecocash_confirm"
    AIRTIME_NETWORK = "airtime_network"
    AIRTIME_NUMBER = "airtime_number"
    AIRTIME_AMOUNT = "airtime_amount"
    AIRTIME_CONFIRM = "airtime_confirm"
    ZIM_SERVICES = "zim_services"
    AIRTIME_PROVIDER = "airtime_provider"
    DATA_PROVIDER = "data_provider"
    DATA_NUMBER = "data_number"
    DATA_BUNDLE = "data_bundle" 
    DATA_CONFIRM = "data_confirm"

class IDTypes:
    OPTIONS = [
        "National ID",
        "Passport",
        "Drivers License"
    ]

class VerificationMethods:
    OPTIONS = [
        "SMS",
        "Email",
        "Voice Call"
    ]

# User session management
class UserSession:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}

    def get_session(self, sender: str) -> dict:
        if sender not in self.sessions:
            self.sessions[sender] = {
                'state': UserState.MAIN_MENU,
                'data': {}
            }
        return self.sessions[sender]

    def update_state(self, sender: str, new_state: str):
        session = self.get_session(sender)
        session['state'] = new_state

    def update_data(self, sender: str, key: str, value: any):
        session = self.get_session(sender)
        if 'data' not in session:
            session['data'] = {}
        session['data'][key] = value

    def get_data(self, sender: str, key: str) -> any:
        session = self.get_session(sender)
        return session.get('data', {}).get(key)

# Initialize session manager
session_manager = UserSession()

# Update your helper functions
def update_user_state(sender: str, new_state: str):
    session_manager.update_state(sender, new_state)

def get_user_state(sender: str) -> str:
    return session_manager.get_session(sender)['state']

def update_user_data(sender: str, key: str, value: any):
    session_manager.update_data(sender, key, value)

def get_user_data(sender: str, key: str) -> any:
    return session_manager.get_data(sender, key)

def get_user(phone_number):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE phone_number = ?', (phone_number,))
    columns = [description[0] for description in c.description]
    result = c.fetchone()
    conn.close()
    
    if result:
        return dict(zip(columns, result))
    return None

def format_main_menu():
    return """Main Menu:
1. My Wallet
2. Zimbabwe Services
3. South Africa Services
4. Order Groceries
5. Merchant Services
6. Help & Support

Reply with a number to select an option."""

def format_wallet_menu(balance):
    return f"""My Wallet (Balance: ${balance:.2f})
1. EFT Deposit
2. Voucher Deposit
3. Buy Voucher
4. Send Token
5. Balance and History
5. Back to Main Menu

Reply with a number to select an option."""

def validate_twilio_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the request URL and POST data
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        request_valid = validator.validate(
            request.url,
            request.form,
            request.headers.get('X-Twilio-Signature', '')
        )
        
        # Validate the request actually came from Twilio
        if not request_valid and not app.debug:
            return 'Invalid request', 403
        return f(*args, **kwargs)
    return decorated_function

@app.errorhandler(Exception)
def handle_error(error):
    print(f"Error: {str(error)}")
    resp = MessagingResponse()
    resp.message("Sorry, something went wrong. Please try again later.")
    return str(resp)

# Add this state mapping after your UserState class
class MenuFlow:
    FLOW = {
        UserState.MAIN_MENU: None,  # Main menu has no previous state
        UserState.WALLET_MENU: UserState.MAIN_MENU,
        UserState.EFT_MENU: UserState.WALLET_MENU,
        UserState.VOUCHER_MENU: UserState.WALLET_MENU,
        UserState.BUY_VOUCHER_MENU: UserState.WALLET_MENU,
        UserState.ZIM_SERVICES_MENU: UserState.MAIN_MENU,
        UserState.AIRTIME_MENU: UserState.ZIM_SERVICES_MENU,
        UserState.DATA_MENU: UserState.ZIM_SERVICES_MENU,
        UserState.DSTV_MENU: UserState.ZIM_SERVICES_MENU,
        UserState.ZESA_MENU: UserState.ZIM_SERVICES_MENU,
        UserState.ECOCASH_PHONE: UserState.EFT_MENU,
        UserState.ECOCASH_AMOUNT: UserState.ECOCASH_PHONE,
        UserState.ECOCASH_CONFIRM: UserState.ECOCASH_AMOUNT,
        # Add other menu state mappings here
    }

# Update the handle_menu_command function to include back navigation
def handle_menu_command(incoming_msg, user, sender):
    """Handle menu commands (menu and back)"""
    incoming_msg = incoming_msg.lower()
    
    if incoming_msg == 'menu':
        update_user_state(sender, UserState.MAIN_MENU)
        return True, format_main_menu()
    
    elif incoming_msg == 'back':
        current_state = get_user_state(sender)
        if current_state in MenuFlow.FLOW and MenuFlow.FLOW[current_state]:
            previous_state = MenuFlow.FLOW[current_state]
            update_user_state(sender, previous_state)
            
            # Format appropriate menu based on state
            if previous_state == UserState.MAIN_MENU:
                return True, format_main_menu()
            elif previous_state == UserState.WALLET_MENU:
                user = get_user(sender)
                return True, format_wallet_menu(user['wallet_balance'])
            elif previous_state == UserState.ZIM_SERVICES_MENU:
                return True, format_zim_services_menu()
            # Add other menu formats as needed
            
        return True, "Cannot go back from here. Type 'menu' to return to main menu."
    
    return False, None

# Add EFT menu formatting function
def format_eft_menu():
    return """Select Payment Method:
1. ECOCASH
2. ONEMONEY
3. CBZ
4. STANDARD BANK

Reply with a number to select an option.
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu"""

# Add Voucher menu formatting function
def format_voucher_menu():
    return """Select Voucher Type:
1. NEDBANK CashOut
2. OTT
3. STANDARD BANK CashOut
4. 1 Voucher

Reply with a number to select an option.
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu"""

# Add Buy Voucher menu formatting function
def format_buy_voucher_menu():
    return """Select Voucher Type:
1. Blu Voucher
2. Hollywood

Reply with a number to select an option.
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu"""

# Add Zimbabwe Services menu formatting function
def format_zim_services_menu():
    return """Zimbabwe Services:
1. Buy Airtime
2. Buy Data
3. Pay DSTV
4. Pay ZESA
5. Pay Nyaradzo
6. Pay Liquid Home
7. Back to Main Menu

Type 'back' to return to Main Menu
Type 'menu' for Main Menu"""

# Add Airtime menu formatting function
def format_airtime_menu():
    return """Select Network Provider:
1. ECONET
2. NETONE
3. TELECEL
4. Airtime Voucher(PIN)

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""

# Add Data menu formatting function
def format_data_menu():
    return """Select Network Provider:
1. ECONET
2. NETONE
3. TELECEL

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""

# Add DSTV payment menu formatting function
def format_dstv_menu():
    return """Select Payment Method:
1. Use my balance
2. Use Ecocash USD
3. Use Ecocash ZiG
4. Use InnBucks

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""

# Add ZESA services menu formatting function
def format_zesa_menu():
    return """ZESA Services:
1. Buy Token
2. View Token

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""

# Add Paynow initialization with test credentials
paynow = Paynow(
    integration_id="19542",  # Replace with your test integration ID
    integration_key="e104d8ee-feb0-46ba-97eb-bc7f882ee17b",  # Replace with your test integration key
    return_url="http://localhost:8000/paynow/return",  # Replace with your return URL
    result_url="http://localhost:8000/paynow/result"   # Replace with your result URL
)

# Add ECOCASH transaction handler
def process_ecocash_payment(phone, amount, email):
    try:
        # Create the payment
        payment = paynow.create_payment(f"EFT Deposit {phone}", email)
        
        # Add the payment details
        payment.add("EFT Deposit", float(amount))
        
        # Send mobile money request
        response = paynow.send_mobile(payment, phone, 'ecocash')
        
        if response.success:
            return True, response.instructions, response.poll_url
        else:
            return False, "Payment initiation failed. Please try again.", None
            
    except Exception as e:
        print(f"Paynow Error: {str(e)}")  # Add logging
        return False, f"An error occurred: {str(e)}", None

# Add HotRecharge API integration
class HotRecharge:
    def __init__(self, config):
        self.base_url = "https://ssl.hot.co.zw/api/v3"
        self.access_code = config["ACCESS_CODE"]
        self.password = config["PASSWORD"]
        self.token = None
        
    def login(self):
        """Get authentication token"""
        try:
            response = requests.post(f"{self.base_url}/login", json={
                "accessCode": self.access_code,
                "password": self.password
            })
            data = response.json()
            self.token = data["token"]
            return True
        except Exception as e:
            logging.error(f"HotRecharge login error: {str(e)}")
            return False

    def buy_airtime(self, network: str, phone: str, amount: float) -> dict:
        """Purchase airtime"""
        try:
            if not self.token and not self.login():
                return {"success": False, "error": "Authentication failed"}

            # Map networks to product IDs based on API docs
            product_ids = {
                "econet": 3,    # Econet USD Airtime
                "netone": 35,   # NetOne USD
                "telecel": 11   # Telecel USD
            }
            
            product_id = product_ids.get(network.lower())
            if not product_id:
                return {"success": False, "error": "Network not supported"}

            # Generate unique reference
            ref = f"AIR_{datetime.now().strftime('%Y%m%d%H%M%S')}_{phone[-4:]}"

            payload = {
                "agentReference": ref,
                "productId": product_id,
                "target": phone,
                "amount": amount,
                "customSMS": f"%COMPANYNAME% topped up your account with $%AMOUNT%. Your new balance is $%BALANCE%."
            }

            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{self.base_url}/products/recharge",
                json=payload,
                headers=headers
            )
            
            result = response.json()
            
            if result.get("successful"):
                return {
                    "success": True,
                    "reference": ref,
                    "message": result.get("message", "Airtime purchase successful"),
                    "recharge_data": result.get("rechargeData", {})
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Purchase failed")
                }

        except Exception as e:
            logging.error(f"HotRecharge purchase error: {str(e)}")
            return {"success": False, "error": str(e)}

    def check_transaction(self, reference: str) -> dict:
        """Check transaction status"""
        try:
            if not self.token and not self.login():
                return {"success": False, "error": "Authentication failed"}

            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/transaction/{reference}",
                headers=headers
            )
            
            result = response.json()
            return {
                "success": True,
                "status": result.get("status"),
                "message": result.get("message")
            }

        except Exception as e:
            logging.error(f"HotRecharge status check error: {str(e)}")
            return {"success": False, "error": str(e)}

# Initialize HotRecharge
hot_recharge = HotRecharge({
    "ACCESS_CODE": "tatenda@contessasoft.co.zw",
    "PASSWORD": "casey899"
})

# Add these validation functions after your existing imports and before the routes

def validate_name(name: str) -> bool:
    """
    Validates names (first name, second name, surname)
    - Must be 2-50 characters
    - Can contain letters, spaces, hyphens, and apostrophes
    - Must start and end with a letter
    """
    if not name:
        return False
    
    # Remove extra spaces and standardize hyphens
    name = " ".join(name.split())
    
    # Updated pattern to include apostrophes
    pattern = r'^[A-Za-z][A-Za-z\s\-\']{0,48}[A-Za-z]$'
    return bool(re.match(pattern, name))

def validate_zim_address(address: str) -> bool:
    """
    Validates Zimbabwean addresses in a general way
    - Must be 5-200 characters
    - Can contain letters, numbers, spaces, and common punctuation
    - Must contain at least one number (for house/stand number)
    """
    if not address or len(address) < 5 or len(address) > 200:
        return False
    
    # Remove extra spaces
    address = " ".join(address.split())
    
    # Must contain at least one number
    if not any(char.isdigit() for char in address):
        return False
    
    # Basic pattern for addresses
    pattern = r'^[A-Za-z0-9\s\.,\-\/#\'\"]+$'
    if not re.match(pattern, address):
        return False
    
    # Check for common Zimbabwean address keywords
    common_keywords = ['street', 'road', 'ave', 'avenue', 'close', 'drive', 
                      'harare', 'bulawayo', 'mutare', 'gweru', 'masvingo',
                      'chitungwiza', 'stand']
    
    return any(keyword in address.lower() for keyword in common_keywords)

def validate_zim_id(id_number: str) -> bool:
    """Validates Zimbabwean National ID number format: 00-000000A00"""
    pattern = r'^\d{2}-\d{6}[A-Z]\d{2}$'
    return bool(re.match(pattern, id_number))

def validate_zim_passport(passport: str) -> bool:
    """Validates Zimbabwean Passport number format: CN123456"""
    pattern = r'^[A-Z]{2}\d{6}$'
    return bool(re.match(pattern, passport))

def validate_drivers_license(license: str) -> bool:
    """Validates Zimbabwean Driver's License number: 12 digits"""
    pattern = r'^\d{12}$'
    return bool(re.match(pattern, license))

def validate_passcode(passcode: str) -> bool:
    """Validates 6-digit passcode"""
    pattern = r'^\d{6}$'
    return bool(re.match(pattern, passcode))

def validate_zesa_meter(meter: str) -> bool:
    """Validates ZESA meter number format: 11 digits"""
    pattern = r'^\d{11}$'
    return bool(re.match(pattern, meter))

@app.route('/webhook', methods=['POST'])
@validate_twilio_request
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    resp = MessagingResponse()
    msg = resp.message()

    # Check if user exists
    user = get_user(sender)
    
    if user and user['registration_complete']:
        # Check for menu command first
        is_menu, menu_text = handle_menu_command(incoming_msg, user, sender)
        if is_menu:
            msg.body(menu_text)
            return str(resp)
    
    if not user and incoming_msg.lower() == 'hi':
        # New user registration
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (phone_number, current_state, registration_complete) VALUES (?, ?, ?)',
                 (sender, UserState.WELCOME, False))
        conn.commit()
        conn.close()
        
        msg.body("""Welcome to TISUWAY Wallet! 🌟
        
Let's get you registered. Please enter your Name.

Example: John

(Type 'menu' anytime to return to main menu after registration)
(Type 'back' to go back one step in the menu)""")
        update_user_state(sender, UserState.NAME)
        return str(resp)
    
    if user:
        current_state = get_user_state(sender)
        
        # Registration Flow
        if current_state == UserState.NAME:
            if validate_name(incoming_msg):
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('UPDATE users SET first_name = ?, current_state = ? WHERE phone_number = ?',
                         (incoming_msg, UserState.SURNAME, sender))
                conn.commit()
                conn.close()
                msg.body("Please enter your Surname")
                update_user_state(sender, UserState.SURNAME)
            else:
                msg.body("""Invalid name format. Please enter your name:
- Use only letters, spaces, hyphens, or apostrophes
- Must be 2-50 characters
- Must start and end with letters

Example: John""")

        elif current_state == UserState.SURNAME:
            if validate_name(incoming_msg):
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('UPDATE users SET surname = ?, current_state = ? WHERE phone_number = ?',
                         (incoming_msg, UserState.NATIONALITY, sender))
                conn.commit()
                conn.close()
                msg.body("Please enter your Nationality")
                update_user_state(sender, UserState.NATIONALITY)
            else:
                msg.body("""Invalid surname format. Please enter your surname:
- Use only letters, spaces, hyphens, or apostrophes
- Must be 2-50 characters
- Must start and end with letters

Example: Smith""")

        elif current_state == UserState.NATIONALITY:
            if validate_name(incoming_msg):  # Using same validation as names
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('UPDATE users SET nationality = ?, current_state = ? WHERE phone_number = ?',
                         (incoming_msg, UserState.ADDRESS, sender))
                conn.commit()
                conn.close()
                msg.body("""Please enter your Full Residential Address.
Example: 123 Smith Street, Avondale, Harare""")
                update_user_state(sender, UserState.ADDRESS)
            else:
                msg.body("""Invalid nationality format. Please enter a valid nationality:
- Use only letters
- Must be 2-50 characters

Example: Zimbabwean""")

        elif current_state == UserState.ADDRESS:
            if validate_zim_address(incoming_msg):
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('UPDATE users SET address = ?, current_state = ? WHERE phone_number = ?',
                         (incoming_msg, UserState.ID_TYPE, sender))
                conn.commit()
                conn.close()
                
                id_options = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(IDTypes.OPTIONS)])
                msg.body(f"Select ID Type:\n{id_options}")
                update_user_state(sender, UserState.ID_TYPE)
            else:
                msg.body("""Invalid address format. Please enter a valid Zimbabwean address:
- Must include house/stand number
- Must include street name or location
- Must include area/suburb/city
                
Example: 123 Smith Street, Avondale, Harare""")

        elif current_state == UserState.ID_TYPE:
            try:
                selection = int(incoming_msg)
                if 1 <= selection <= len(IDTypes.OPTIONS):
                    id_type = IDTypes.OPTIONS[selection-1]
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    c.execute('UPDATE users SET id_type = ?, current_state = ? WHERE phone_number = ?',
                             (id_type, UserState.ID_NUMBER, sender))
                    conn.commit()
                    conn.close()
                    
                    # Show format example based on ID type
                    format_examples = {
                        "National ID": "Format: 00-000000A00 (e.g., 63-123456A42)",
                        "Passport": "Format: 8 characters (e.g., CN123456)",
                        "Drivers License": "Format: 12 digits (e.g., 123456789012)"
                    }
                    msg.body(f"Please enter your {id_type} number:\n{format_examples[id_type]}")
                    update_user_data(sender, 'id_type', id_type)
                    update_user_state(sender, UserState.ID_NUMBER)
                else:
                    msg.body("Invalid selection. Please choose a number from the list.")
            except ValueError:
                msg.body("Please enter a valid number")

        elif current_state == UserState.ID_NUMBER:
            id_type = get_user_data(sender, 'id_type')
            is_valid = False
            
            if id_type == "National ID":
                is_valid = validate_zim_id(incoming_msg)
                error_msg = "Format: 00-000000A00 (e.g., 63-123456A42)"
            elif id_type == "Passport":
                is_valid = validate_zim_passport(incoming_msg)
                error_msg = "Format: 8 characters (e.g., CN123456)"
            elif id_type == "Drivers License":
                is_valid = validate_drivers_license(incoming_msg)
                error_msg = "Format: 12 digits (e.g., 123456789012)"
            
            if is_valid:
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('UPDATE users SET id_number = ?, current_state = ? WHERE phone_number = ?',
                         (incoming_msg, UserState.VERIFICATION, sender))
                conn.commit()
                conn.close()
                
                verification_options = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(VerificationMethods.OPTIONS)])
                msg.body(f"Select Verification Method:\n{verification_options}")
                update_user_state(sender, UserState.VERIFICATION)
            else:
                msg.body(f"""Invalid {id_type} format. Please enter a valid number:
{error_msg}""")

        elif current_state == UserState.VERIFICATION:
            try:
                selection = int(incoming_msg)
                if 1 <= selection <= len(VerificationMethods.OPTIONS):
                    verification_method = VerificationMethods.OPTIONS[selection-1]
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    c.execute('UPDATE users SET verification_method = ?, current_state = ? WHERE phone_number = ?',
                             (verification_method, UserState.PASSCODE, sender))
                    conn.commit()
                    conn.close()
                    msg.body("""Please create a 6-digit passcode for your wallet.
Example: 123456""")
                    update_user_state(sender, UserState.PASSCODE)
                else:
                    msg.body("Invalid selection. Please choose a number from the list.")
            except ValueError:
                msg.body("Please enter a valid number")

        elif current_state == UserState.PASSCODE:
            if validate_passcode(incoming_msg):
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('UPDATE users SET passcode = ?, current_state = ?, registration_complete = ? WHERE phone_number = ?',
                         (incoming_msg, UserState.MAIN_MENU, True, sender))
                conn.commit()
                conn.close()
                msg.body(f"""Registration Complete! 🎉

Navigation commands:
- Type 'menu' anytime to return to the main menu
- Type 'back' to go back one step in the menu

{format_main_menu()}""")
                update_user_state(sender, UserState.MAIN_MENU)
            else:
                msg.body("""Invalid passcode format. Please enter a 6-digit number:
Example: 123456""")

        # Main Menu Navigation
        elif current_state == UserState.MAIN_MENU:
            if incoming_msg == "1":  # My Wallet
                user = get_user(sender)
                msg.body(format_wallet_menu(user['wallet_balance']))
                update_user_state(sender, UserState.WALLET_MENU)
            elif incoming_msg == "2":  # Zimbabwe Services
                msg.body(format_zim_services_menu())
                update_user_state(sender, UserState.ZIM_SERVICES)
            elif incoming_msg in ["3", "4", "5", "6"]:
                menu_options = {
                    "3": "South Africa Services",
                    "4": "Order Groceries",
                    "5": "Merchant Services",
                    "6": "Help & Support"
                }
                msg.body(f"""You selected: {menu_options[incoming_msg]}

This feature is coming soon!
Type 'back' to return to Main Menu
Type 'menu' for Main Menu""")
            else:
                msg.body(format_main_menu())

        # ... [Rest of your existing menu navigation code remains unchanged] ...

    return str(resp)

if __name__ == '__main__':
    # Verify environment variables are set
    required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        exit(1)
        
    # Initialize database
    init_db()
    
    # Development configuration
    class Config:
        DEBUG = False

    class DevelopmentConfig(Config):
        DEBUG = True

    class ProductionConfig(Config):
        DEBUG = False
        
    # Set the configuration
    app.config.from_object(DevelopmentConfig if app.debug else ProductionConfig)
    
    # Run the app
    app.run(debug=True)