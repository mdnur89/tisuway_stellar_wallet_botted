import sqlite3
from session import session_manager
from states import UserState, IDTypes, VerificationMethods

def get_user(phone_number):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
        columns = [description[0] for description in c.description]
        result = c.fetchone()
        return dict(zip(columns, result)) if result else None


def update_user_state(sender: str, new_state: str):
    session_manager.update_state(sender, new_state)


def get_user_state(sender: str) -> str:
    return session_manager.get_session(sender)["state"]


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
6. Back to Main Menu

Reply with a number to select an option."""


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

def format_eft_menu():
    return """Select Payment Method:
1. ECOCASH
2. ONEMONEY
3. CBZ
4. STANDARD BANK

Reply with a number to select an option.
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu"""

def format_voucher_menu():
    return """Select Voucher Type:
1. NEDBANK CashOut
2. OTT
3. STANDARD BANK CashOut
4. 1 Voucher

Reply with a number to select an option.
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu"""

def format_buy_voucher_menu():
    return """Select Voucher Type:
1. Blu Voucher
2. Hollywood

Reply with a number to select an option.
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu"""

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

def format_airtime_menu():
    return """Select Network Provider:
1. ECONET
2. NETONE
3. TELECEL
4. Airtime Voucher(PIN)

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""

def format_data_menu():
    return """Select Network Provider:
1. ECONET
2. NETONE
3. TELECEL

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""

def format_dstv_menu():
    return """Select Payment Method:
1. Use my balance
2. Use Ecocash USD
3. Use Ecocash ZiG
4. Use InnBucks

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""

def format_zesa_menu():
    return """ZESA Services:
1. Buy Token
2. View Token

Reply with a number to select an option.
Type 'back' to return to Zimbabwe Services
Type 'menu' for Main Menu"""
