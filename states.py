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
    OPTIONS = ["National ID", "Passport", "Drivers License"]


class VerificationMethods:
    OPTIONS = ["SMS", "Email", "Voice Call"]