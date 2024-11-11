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
                  last_name TEXT,
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
    FIRST_NAME = "first_name"
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

# Initialize the payment processor
payment_processor = PaymentProcessor(PAYNOW_CONFIG)

# Update your webhook handler for ECOCASH flow
@app.route("/webhook", methods=['POST'])
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
        
Let's get you registered. Please enter your First Name and Last Name.

(Type 'menu' anytime to return to main menu after registration)
(Type 'back' to go back one step in the menu)""")
        update_user_state(sender, UserState.FIRST_NAME)
        return str(resp)
    
    if user:
        current_state = get_user_state(sender)
        
        # Registration Flow
        if current_state == UserState.FIRST_NAME:
            names = incoming_msg.split()
            if len(names) >= 2:
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('UPDATE users SET first_name = ?, last_name = ?, current_state = ? WHERE phone_number = ?',
                         (names[0], names[1], UserState.SURNAME, sender))
                conn.commit()
                conn.close()
                msg.body("Please enter your Surname")
                update_user_state(sender, UserState.SURNAME)
            else:
                msg.body("Please enter both your First Name and Last Name separated by a space")

        elif current_state == UserState.SURNAME:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET surname = ?, current_state = ? WHERE phone_number = ?',
                     (incoming_msg, UserState.NATIONALITY, sender))
            conn.commit()
            conn.close()
            msg.body("Please enter your Nationality")
            update_user_state(sender, UserState.NATIONALITY)

        elif current_state == UserState.NATIONALITY:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET nationality = ?, current_state = ? WHERE phone_number = ?',
                     (incoming_msg, UserState.ADDRESS, sender))
            conn.commit()
            conn.close()
            msg.body("Please enter your Full Residential Address")
            update_user_state(sender, UserState.ADDRESS)

        elif current_state == UserState.ADDRESS:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET address = ?, current_state = ? WHERE phone_number = ?',
                     (incoming_msg, UserState.ID_TYPE, sender))
            conn.commit()
            conn.close()
            
            id_options = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(IDTypes.OPTIONS)])
            msg.body(f"Select ID Type:\n{id_options}")
            update_user_state(sender, UserState.ID_TYPE)

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
                    msg.body(f"Please enter your {id_type} number")
                    update_user_state(sender, UserState.ID_NUMBER)
                else:
                    msg.body("Invalid selection. Please choose a number from the list.")
            except ValueError:
                msg.body("Please enter a valid number")

        elif current_state == UserState.ID_NUMBER:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('UPDATE users SET id_number = ?, current_state = ? WHERE phone_number = ?',
                     (incoming_msg, UserState.VERIFICATION, sender))
            conn.commit()
            conn.close()
            
            verification_options = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(VerificationMethods.OPTIONS)])
            msg.body(f"Select Verification Method:\n{verification_options}")
            update_user_state(sender, UserState.VERIFICATION)

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
                    msg.body("Please create a 4-digit passcode for your wallet")
                    update_user_state(sender, UserState.PASSCODE)
                else:
                    msg.body("Invalid selection. Please choose a number from the list.")
            except ValueError:
                msg.body("Please enter a valid number")

        elif current_state == UserState.PASSCODE:
            if re.match(r'^\d{4}$', incoming_msg):
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
                msg.body("Please enter a valid 4-digit passcode")

        # Main Menu Navigation
        elif current_state == UserState.MAIN_MENU:
            if incoming_msg == "1":  # My Wallet
                user = get_user(sender)
                msg.body(format_wallet_menu(user['wallet_balance']))
                update_user_state(sender, UserState.WALLET_MENU)
            elif incoming_msg == "2":  # Zimbabwe Services
                msg.body(format_zim_services_menu())
                update_user_state(sender, UserState.ZIM_SERVICES_MENU)
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

        # Wallet Menu Navigation
        elif current_state == UserState.WALLET_MENU:
            if incoming_msg == "6":  # Back to Main Menu
                msg.body(format_main_menu())
                update_user_state(sender, UserState.MAIN_MENU)
            elif incoming_msg == "1":  # EFT Deposit
                msg.body(format_eft_menu())
                update_user_state(sender, UserState.EFT_MENU)
            elif incoming_msg == "2":  # Voucher Deposit
                msg.body(format_voucher_menu())
                update_user_state(sender, UserState.VOUCHER_MENU)
            elif incoming_msg == "3":  # Buy Voucher
                msg.body(format_buy_voucher_menu())
                update_user_state(sender, UserState.BUY_VOUCHER_MENU)
            elif incoming_msg in ["4", "5"]:
                wallet_options = {
                    "4": "Send Token",
                    "5": "Balance and History"
                }
                msg.body(f"""You selected: {wallet_options[incoming_msg]}

This feature is coming soon!
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu""")
            else:
                user = get_user(sender)
                msg.body(format_wallet_menu(user['wallet_balance']))

        # Voucher Menu Navigation
        elif current_state == UserState.VOUCHER_MENU:
            voucher_options = {
                "1": "NEDBANK CashOut",
                "2": "OTT",
                "3": "STANDARD BANK CashOut",
                "4": "1 Voucher"
            }
            
            if incoming_msg in voucher_options:
                voucher_type = voucher_options[incoming_msg]
                msg.body(f"""You selected: {voucher_type}
                
Please enter your voucher number.
Type 'back' to return to voucher types
Type 'menu' for Main Menu""")
            else:
                msg.body(format_voucher_menu())

        # EFT Menu Navigation
        elif current_state == UserState.EFT_MENU:
            if incoming_msg == "1":  # ECOCASH
                msg.body("""Please enter your EcoCash registered phone number:
                
Format: 077xxxxxxx
Type 'back' to return to payment methods
Type 'menu' for Main Menu""")
                update_user_state(sender, UserState.ECOCASH_PHONE)
            elif incoming_msg == "2":  # ONEMONEY
                msg.body("""Please enter your OneMoney registered phone number:
                
Format: 078xxxxxxx
Type 'back' to return to payment methods
Type 'menu' for Main Menu""")
            elif incoming_msg == "3":  # CBZ
                msg.body("""Please enter your CBZ registered phone number:
                
Format: 077xxxxxxx
Type 'back' to return to payment methods
Type 'menu' for Main Menu""")
            elif incoming_msg == "4":  # STANDARD BANK
                msg.body("""Please enter your Standard Bank registered phone number:
                
Format: 077xxxxxxx
Type 'back' to return to payment methods
Type 'menu' for Main Menu""")
            else:
                msg.body(format_eft_menu())

        # Buy Voucher Menu Navigation
        elif current_state == UserState.BUY_VOUCHER_MENU:
            voucher_options = {
                "1": "Blu Voucher",
                "2": "Hollywood"
            }
            
            if incoming_msg in voucher_options:
                voucher_type = voucher_options[incoming_msg]
                msg.body(f"""You selected: {voucher_type}
                
Please enter the amount you want to purchase.
Type 'back' to return to voucher types
Type 'menu' for Main Menu""")
            else:
                msg.body(format_buy_voucher_menu())

        # Zimbabwe Services Menu Navigation
        elif current_state == UserState.ZIM_SERVICES_MENU:
            zim_services_options = {
                "1": "Buy Airtime",
                "2": "Buy Data",
                "3": "Pay DSTV",
                "4": "Pay ZESA",
                "5": "Pay Nyaradzo",
                "6": "Pay Liquid Home"
            }
            
            if incoming_msg == "7":  # Back to Main Menu
                msg.body(format_main_menu())
                update_user_state(sender, UserState.MAIN_MENU)
            elif incoming_msg == "1":  # Buy Airtime
                msg.body(format_airtime_menu())
                update_user_state(sender, UserState.AIRTIME_MENU)
            elif incoming_msg == "2":  # Buy Data
                msg.body(format_data_menu())
                update_user_state(sender, UserState.DATA_MENU)
            elif incoming_msg == "3":  # Pay DSTV
                msg.body(format_dstv_menu())
                update_user_state(sender, UserState.DSTV_MENU)
            elif incoming_msg == "4":  # Pay ZESA
                msg.body(format_zesa_menu())
                update_user_state(sender, UserState.ZESA_MENU)
            elif incoming_msg in ["5", "6"]:
                service = zim_services_options[incoming_msg]
                msg.body(f"""You selected: {service}
                
Please enter the {service.split()[-1]} number.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu""")
            else:
                msg.body(format_zim_services_menu())

        # Airtime Menu Navigation
        elif current_state == UserState.AIRTIME_MENU:
            airtime_options = {
                "1": "ECONET",
                "2": "NETONE",
                "3": "TELECEL",
                "4": "Airtime Voucher(PIN)"
            }
            
            if incoming_msg in airtime_options:
                provider = airtime_options[incoming_msg]
                if provider == "Airtime Voucher(PIN)":
                    msg.body(f"""You selected: {provider}
                    
Please enter your voucher PIN number.
Type 'back' to return to network selection
Type 'menu' for Main Menu""")
                else:
                    msg.body(f"""You selected: {provider}
                    
Please enter the phone number.
Type 'back' to return to network selection
Type 'menu' for Main Menu""")
            else:
                msg.body(format_airtime_menu())

        # Data Menu Navigation
        elif current_state == UserState.DATA_MENU:
            data_options = {
                "1": "ECONET",
                "2": "NETONE",
                "3": "TELECEL"
            }
            
            if incoming_msg in data_options:
                provider = data_options[incoming_msg]
                msg.body(f"""You selected: {provider}
                
Please enter the phone number.
Type 'back' to return to network selection
Type 'menu' for Main Menu""")
            else:
                msg.body(format_data_menu())

        # DSTV Menu Navigation
        elif current_state == UserState.DSTV_MENU:
            dstv_options = {
                "1": "Use my balance",
                "2": "Use Ecocash USD",
                "3": "Use Ecocash ZiG",
                "4": "Use InnBucks"
            }
            
            if incoming_msg in dstv_options:
                payment_method = dstv_options[incoming_msg]
                msg.body(f"""You selected: {payment_method}
                
Please enter your DSTV account number.
Type 'back' to return to payment methods
Type 'menu' for Main Menu""")
            else:
                msg.body(format_dstv_menu())

        # ZESA Menu Navigation
        elif current_state == UserState.ZESA_MENU:
            zesa_options = {
                "1": "Buy Token",
                "2": "View Token"
            }
            
            if incoming_msg in zesa_options:
                service = zesa_options[incoming_msg]
                if service == "Buy Token":
                    msg.body("""You selected: Buy Token
                    
Please enter your meter number.
Type 'back' to return to ZESA services
Type 'menu' for Main Menu""")
                else:  # View Token
                    msg.body("""You selected: View Token
                    
Please enter your reference number.
Type 'back' to return to ZESA services
Type 'menu' for Main Menu""")
            else:
                msg.body(format_zesa_menu())

        # ECOCASH Phone Number Handler
        elif current_state == UserState.ECOCASH_PHONE:
            phone = incoming_msg.strip()
            if re.match(r'^07[7-8][0-9]{7}$', phone):
                # Store phone number in session
                update_user_data(sender, 'ecocash_phone', phone)
                
                msg.body("""Enter amount to deposit (USD):

Type 'back' to re-enter phone number
Type 'menu' for Main Menu""")
                update_user_state(sender, UserState.ECOCASH_AMOUNT)
            else:
                msg.body("""Invalid phone number format. Please enter a valid EcoCash number:

Format: 077xxxxxxx or 078xxxxxxx
Type 'back' to return to payment methods
Type 'menu' for Main Menu""")

        # ECOCASH Amount Handler
        elif current_state == UserState.ECOCASH_AMOUNT:
            try:
                amount = float(incoming_msg.strip())
                if amount <= 0:
                    raise ValueError("Amount must be greater than 0")
                    
                # Store amount in session
                update_user_data(sender, 'ecocash_amount', amount)
                phone = get_user_data(sender, 'ecocash_phone')
                
                msg.body(f"""Confirm Payment Details:
Phone Number: {phone}
Amount: ${amount:.2f}

1. Confirm
2. Cancel

Type 'back' to re-enter amount
Type 'menu' for Main Menu""")
                update_user_state(sender, UserState.ECOCASH_CONFIRM)
            except ValueError:
                msg.body("""Invalid amount. Please enter a valid number:
Example: 10.00

Type 'back' to re-enter phone number
Type 'menu' for Main Menu""")

        # ECOCASH Confirmation Handler
        elif current_state == UserState.ECOCASH_CONFIRM:
            if incoming_msg == "1":  # Confirm
                try:
                    phone = get_user_data(sender, 'ecocash_phone')
                    amount = get_user_data(sender, 'ecocash_amount')
                    
                    # Generate unique reference
                    reference = f"EFT_{sender}_{int(time.time())}"
                    
                    # Process payment using PaymentProcessor
                    result = payment_processor.create_mobile_payment(
                        reference=reference,
                        phone=phone,
                        amount=amount,
                        method='ecocash'
                    )
                    
                    if result['success']:
                        # Store poll_url for status checking
                        update_user_data(sender, 'poll_url', result['poll_url'])
                        
                        msg.body(f"""Payment initiated successfully!

{result['instructions']}

Reference: {result['reference']}
We'll notify you once the payment is confirmed.

Type 'menu' for Main Menu""")
                        update_user_state(sender, UserState.MAIN_MENU)
                    else:
                        msg.body(f"""Payment initiation failed: {result['error']}

Type 'back' to try again
Type 'menu' for Main Menu""")
                
                except Exception as e:
                    print(f"Payment Error: {str(e)}")
                    msg.body("""Sorry, something went wrong. Please try again later.
                    
Type 'menu' for Main Menu""")
                
            elif incoming_msg == "2":  # Cancel
                msg.body(format_eft_menu())
                update_user_state(sender, UserState.EFT_MENU)
            else:
                msg.body("""Invalid selection. Please choose:
1. Confirm
2. Cancel

Type 'back' to re-enter amount
Type 'menu' for Main Menu""")

    return str(msg)

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