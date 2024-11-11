from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime
import sqlite3
import re
import os
from dotenv import load_dotenv
from functools import wraps
from twilio.request_validator import RequestValidator
from typing import Dict
import time
from db import init_db
from config import TWILIO_ACCOUNT_SID ,TWILIO_AUTH_TOKEN,TWILIO_PHONE_NUMBER,DEBUG 
from states import  UserState,IDTypes,VerificationMethods
from twilio_utils import validate_twilio_request
from session import session_manager
from utils import format_main_menu, format_wallet_menu,format_zim_services_menu,format_eft_menu,format_voucher_menu,format_buy_voucher_menu

# Load environment variables
load_dotenv()

app = Flask(__name__)


# Initialize Twilio Client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Update your helper functions
def update_user_state(sender: str, new_state: str):
    session_manager.update_state(sender, new_state)


def get_user_state(sender: str) -> str:
    return session_manager.get_session(sender)["state"]


def update_user_data(sender: str, key: str, value: any):
    session_manager.update_data(sender, key, value)


def get_user_data(sender: str, key: str) -> any:
    return session_manager.get_data(sender, key)


def get_user(phone_number):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
        columns = [description[0] for description in c.description]
        result = c.fetchone()
        return dict(zip(columns, result)) if result else None


@app.errorhandler(Exception)
def handle_error(error):
    print(f"Error: {str(error)}")
    resp = MessagingResponse()
    resp.message("Sorry, something went wrong. Please try again later.")
    return str(resp)


class MenuFlow:
    FLOW = {
        UserState.MAIN_MENU: None,
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
    }


def handle_menu_command(incoming_msg, user, sender):
    incoming_msg = incoming_msg.lower()

    if incoming_msg == "menu":
        update_user_state(sender, UserState.MAIN_MENU)
        return True, format_main_menu()

    elif incoming_msg == "back":
        current_state = get_user_state(sender)
        if current_state in MenuFlow.FLOW and MenuFlow.FLOW[current_state]:
            previous_state = MenuFlow.FLOW[current_state]
            update_user_state(sender, previous_state)

            if previous_state == UserState.MAIN_MENU:
                return True, format_main_menu()
            elif previous_state == UserState.WALLET_MENU:
                user = get_user(sender)
                return True, format_wallet_menu(user["wallet_balance"])
            elif previous_state == UserState.ZIM_SERVICES_MENU:
                return True, format_zim_services_menu()

        return True, "Cannot go back from here. Type 'menu' to return to main menu."

    return False, None


@app.route("/webhook", methods=["POST"])
@validate_twilio_request
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")

    resp = MessagingResponse()
    msg = resp.message()

    user = get_user(sender)

    if user and user["registration_complete"]:
        is_menu, menu_text = handle_menu_command(incoming_msg, user, sender)
        if is_menu:
            msg.body(menu_text)
            return str(resp)

    if not user and incoming_msg.lower() == "hi":
        with sqlite3.connect("users.db") as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (phone_number, current_state, registration_complete) VALUES (?, ?, ?)",
                (sender, UserState.WELCOME, False),
            )
            conn.commit()

        msg.body(
            """Welcome to TISUWAY Wallet! 🌟
        
Let's get you registered. Please enter your First Name and Last Name.

(Type 'menu' anytime to return to main menu after registration)
(Type 'back' to go back one step in the menu)"""
        )
        update_user_state(sender, UserState.FIRST_NAME)
        return str(resp)

    if user:
        current_state = get_user_state(sender)

        if current_state == UserState.FIRST_NAME:
            names = incoming_msg.split()
            if len(names) >= 2:
                with sqlite3.connect("users.db") as conn:
                    c = conn.cursor()
                    c.execute(
                        "UPDATE users SET first_name = ?, last_name = ?, current_state = ? WHERE phone_number = ?",
                        (names[0], names[1], UserState.SURNAME, sender),
                    )
                    conn.commit()
                msg.body("Please enter your Surname")
                update_user_state(sender, UserState.SURNAME)
            else:
                msg.body(
                    "Please enter both your First Name and Last Name separated by a space"
                )

        elif current_state == UserState.SURNAME:
            with sqlite3.connect("users.db") as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE users SET surname = ?, current_state = ? WHERE phone_number = ?",
                    (incoming_msg, UserState.NATIONALITY, sender),
                )
                conn.commit()
            msg.body("Please enter your Nationality")
            update_user_state(sender, UserState.NATIONALITY)

        elif current_state == UserState.NATIONALITY:
            with sqlite3.connect("users.db") as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE users SET nationality = ?, current_state = ? WHERE phone_number = ?",
                    (incoming_msg, UserState.ADDRESS, sender),
                )
                conn.commit()
            msg.body("Please enter your Full Residential Address")
            update_user_state(sender, UserState.ADDRESS)

        elif current_state == UserState.ADDRESS:
            with sqlite3.connect("users.db") as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE users SET address = ?, current_state = ? WHERE phone_number = ?",
                    (incoming_msg, UserState.ID_TYPE, sender),
                )
                conn.commit()

            id_options = "\n".join(
                [f"{i+1}. {opt}" for i, opt in enumerate(IDTypes.OPTIONS)]
            )
            msg.body(f"Select ID Type:\n{id_options}")
            update_user_state(sender, UserState.ID_TYPE)

        elif current_state == UserState.ID_TYPE:
            try:
                selection = int(incoming_msg)
                if 1 <= selection <= len(IDTypes.OPTIONS):
                    id_type = IDTypes.OPTIONS[selection - 1]
                    with sqlite3.connect("users.db") as conn:
                        c = conn.cursor()
                        c.execute(
                            "UPDATE users SET id_type = ?, current_state = ? WHERE phone_number = ?",
                            (id_type, UserState.ID_NUMBER, sender),
                        )
                        conn.commit()
                    msg.body(f"Please enter your {id_type} number")
                    update_user_state(sender, UserState.ID_NUMBER)
                else:
                    msg.body("Invalid selection. Please choose a number from the list.")
            except ValueError:
                msg.body("Please enter a valid number")

        elif current_state == UserState.ID_NUMBER:
            with sqlite3.connect("users.db") as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE users SET id_number = ?, current_state = ? WHERE phone_number = ?",
                    (incoming_msg, UserState.VERIFICATION, sender),
                )
                conn.commit()

            verification_options = "\n".join(
                [f"{i+1}. {opt}" for i, opt in enumerate(VerificationMethods.OPTIONS)]
            )
            msg.body(f"Select Verification Method:\n{verification_options}")
            update_user_state(sender, UserState.VERIFICATION)

        elif current_state == UserState.VERIFICATION:
            try:
                selection = int(incoming_msg)
                if 1 <= selection <= len(VerificationMethods.OPTIONS):
                    verification_method = VerificationMethods.OPTIONS[selection - 1]
                    with sqlite3.connect("users.db") as conn:
                        c = conn.cursor()
                        c.execute(
                            "UPDATE users SET verification_method = ?, current_state = ? WHERE phone_number = ?",
                            (verification_method, UserState.PASSCODE, sender),
                        )
                        conn.commit()
                    msg.body("Please create a 4-digit passcode for your wallet")
                    update_user_state(sender, UserState.PASSCODE)
                else:
                    msg.body("Invalid selection. Please choose a number from the list.")
            except ValueError:
                msg.body("Please enter a valid number")

        elif current_state == UserState.PASSCODE:
            if re.match(r"^\d{4}$", incoming_msg):
                with sqlite3.connect("users.db") as conn:
                    c = conn.cursor()
                    c.execute(
                        "UPDATE users SET passcode = ?, current_state = ?, registration_complete = ? WHERE phone_number = ?",
                        (incoming_msg, UserState.MAIN_MENU, True, sender),
                    )
                    conn.commit()
                msg.body(
                    f"""Registration Complete! 🎉

Navigation commands:
- Type 'menu' anytime to return to the main menu
- Type 'back' to go back one step in the menu

{format_main_menu()}"""
                )
                update_user_state(sender, UserState.MAIN_MENU)
            else:
                msg.body("Please enter a valid 4-digit passcode")

        elif current_state == UserState.MAIN_MENU:
            if incoming_msg == "1":  # My Wallet
                user = get_user(sender)
                msg.body(format_wallet_menu(user["wallet_balance"]))
                update_user_state(sender, UserState.WALLET_MENU)
            elif incoming_msg == "2":  # Zimbabwe Services
                msg.body(format_zim_services_menu())
                update_user_state(sender, UserState.ZIM_SERVICES_MENU)
            elif incoming_msg in ["3", "4", "5", "6"]:
                menu_options = {
                    "3": "South Africa Services",
                    "4": "Order Groceries",
                    "5": "Merchant Services",
                    "6": "Help & Support",
                }
                msg.body(
                    f"""You selected: {menu_options[incoming_msg]}

This feature is coming soon!
Type 'back' to return to Main Menu
Type 'menu' for Main Menu"""
                )
            else:
                msg.body(format_main_menu())

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
                wallet_options = {"4": "Send Token", "5": "Balance and History"}
                msg.body(
                    f"""You selected: {wallet_options[incoming_msg]}

This feature is coming soon!
Type 'back' to return to Wallet Menu
Type 'menu' for Main Menu"""
                )
            else:
                user = get_user(sender)
                msg.body(format_wallet_menu(user["wallet_balance"]))

        elif current_state == UserState.VOUCHER_MENU:
            voucher_options = {
                "1": "NEDBANK CashOut",
                "2": "OTT",
                "3": "STANDARD BANK CashOut",
                "4": "1 Voucher",
            }

            if incoming_msg in voucher_options:
                voucher_type = voucher_options[incoming_msg]
                msg.body(
                    f"""You selected: {voucher_type}
                
Please enter your voucher number.
Type 'back' to return to voucher types
Type 'menu' for Main Menu"""
                )
            else:
                msg.body(format_voucher_menu())

        elif current_state == UserState.EFT_MENU:
            if incoming_msg == "1":  # ECOCASH
                msg.body(
                    """Please enter your EcoCash registered phone number:
                
Format: 077xxxxxxx
Type 'back' to return to payment methods
Type 'menu' for Main Menu"""
                )
                update_user_state(sender, UserState.ECOCASH_PHONE)
            elif incoming_msg == "2":  # ONEMONEY
                msg.body(
                    """Please enter your OneMoney registered phone number:
                
Format : 071xxxxxxx
Type 'back' to return to payment methods
Type 'menu' for Main Menu"""
                )
                # You can set the state for OneMoney phone input here if needed

            elif incoming_msg in ["3", "4"]:  # CBZ or STANDARD BANK
                eft_options = {"3": "CBZ", "4": "STANDARD BANK"}
                msg.body(
                    f"""You selected: {eft_options[incoming_msg]}

This feature is coming soon!
Type 'back' to return to payment methods
Type 'menu' for Main Menu"""
                )
            else:
                msg.body(format_eft_menu())

        elif current_state == UserState.ECOCASH_PHONE:
            if re.match(r"^077\d{7}$", incoming_msg):
                update_user_data(sender, "ecocash_phone", incoming_msg)
                msg.body(
                    """Enter the amount you want to deposit:
Type 'back' to return to phone number input
Type 'menu' for Main Menu"""
                )
                update_user_state(sender, UserState.ECOCASH_AMOUNT)
            else:
                msg.body(
                    "Please enter a valid EcoCash phone number in the format: 077xxxxxxx"
                )

        elif current_state == UserState.ECOCASH_AMOUNT:
            try:
                amount = float(incoming_msg)
                if amount > 0:
                    update_user_data(sender, "ecocash_amount", amount)
                    ecocash_phone = get_user_data(sender, "ecocash_phone")
                    msg.body(
                        f"""Confirm your deposit:
- Phone: {ecocash_phone}
- Amount: ${amount:.2f}

Reply 'yes' to confirm or 'no' to cancel.
Type 'back' to return to amount input
Type 'menu' for Main Menu"""
                    )
                    update_user_state(sender, UserState.ECOCASH_CONFIRM)
                else:
                    msg.body("Please enter a valid amount greater than 0")
            except ValueError:
                msg.body("Please enter a valid amount")

        elif current_state == UserState.ECOCASH_CONFIRM:
            if incoming_msg.lower() == "yes":
                ecocash_phone = get_user_data(sender, "ecocash_phone")
                amount = get_user_data(sender, "ecocash_amount")
                # Process deposit transaction here
                with sqlite3.connect("users.db") as conn:
                    c = conn.cursor()
                    c.execute(
                        "UPDATE users SET wallet_balance = wallet_balance + ? WHERE phone_number = ?",
                        (amount, sender),
                    )
                    c.execute(
                        "INSERT INTO transactions (phone_number, transaction_type, amount, timestamp, description) VALUES (?, ?, ?, ?, ?)",
                        (
                            sender,
                            "Deposit",
                            amount,
                            datetime.now(),
                            f"EcoCash deposit from {ecocash_phone}",
                        ),
                    )
                    conn.commit()

                msg.body(f"Deposit successful! Your new balance is: ${amount:.2f}")
                update_user_state(sender, UserState.WALLET_MENU)
                user = get_user(sender)
                msg.body(format_wallet_menu(user["wallet_balance"]))
            elif incoming_msg.lower() == "no":
                msg.body("Deposit canceled. Returning to payment methods.")
                update_user_state(sender, UserState.EFT_MENU)
                msg.body(format_eft_menu())
            else:
                msg.body("Please reply with 'yes' to confirm or 'no' to cancel.")

    return str(resp)


if __name__ == "__main__":
    init_db()
    app.run(debug=DEBUG)