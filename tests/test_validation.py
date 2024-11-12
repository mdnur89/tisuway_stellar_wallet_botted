import os
import sys

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app import (
    validate_name,
    validate_zim_address,
    validate_zim_id,
    validate_zim_passport,
    validate_drivers_license,
    validate_passcode,
    validate_zesa_meter,
)


def test_name_validation():
    print("\n=== Testing Name Validation ===")
    
    test_cases = [
        ("John", True),
        ("Mary-Jane", True),
        ("O'Connor", True),
        ("D'Angelo", True),
        ("McDonald's", False),  # Ends with apostrophe-s
        ("O'", False),         # Too short
        ("John Smith", True),
        ("123", False),
        ("John123", False),
        ("J", False),
        ("", False),
        (" ", False),
        ("John!!!", False),
        ("Very-Very-Very-Very-Very-Very-Long-Name", False),
        ("Mary-Kate O'Connor", True),  # Complex name with both hyphen and apostrophe
        ("d'Artagnan", True),          # French-style name
        ("O'Brien-Smith", True),       # Combined apostrophe and hyphen
    ]
    
    for name, expected in test_cases:
        result = validate_name(name)
        print(f"\nTesting name: '{name}'")
        print(f"Expected: {expected}, Got: {result}")
        if result == expected:
            print("✓ PASS")
        else:
            print("✗ FAIL")


def test_address_validation():
    print("\n=== Testing Address Validation ===")

    test_cases = [
        ("123 Smith Street, Avondale, Harare", True),
        ("Stand 123, Borrowdale Road, Harare", True),
        ("45 Mutare Road, Masvingo", True),
        ("32b, Helm Avenue, Hillside, Harare", True),
        ("No 12, Borrow Road, Harare", True),
        ("No address", False),
        ("123", False),
        ("No street number, Harare", False),
        ("!!!Invalid!!!", False),
        ("", False),
        (" ", False),
    ]

    for address, expected in test_cases:
        result = validate_zim_address(address)
        print(f"Testing address: '{address}'")
        print(f"Expected: {expected}, Got: {result}")
        print("✓ PASS" if result == expected else "✗ FAIL")


def test_id_validation():
    print("\n=== Testing ID Validation ===")

    # National ID
    print("\nNational ID Tests:")
    national_id_cases = [
        ("63-123456A42", True),
        ("12-345678B90", True),
        ("123456789", False),
        ("63-123456Z42", True),
        ("63-12345642", False),
        ("", False),
    ]

    for id_num, expected in national_id_cases:
        result = validate_zim_id(id_num)
        print(f"Testing ID: '{id_num}'")
        print(f"Expected: {expected}, Got: {result}")
        print("✓ PASS" if result == expected else "✗ FAIL")

    # Passport
    print("\nPassport Tests:")
    passport_cases = [
        ("CN123456", True),
        ("AB123456", True),
        ("12345678", False),
        ("ABC12345", False),
        ("", False),
    ]

    for passport, expected in passport_cases:
        result = validate_zim_passport(passport)
        print(f"Testing passport: '{passport}'")
        print(f"Expected: {expected}, Got: {result}")
        print("✓ PASS" if result == expected else "✗ FAIL")


def test_drivers_license_validation():
    print("\n=== Testing Driver's License Validation ===")

    test_cases = [
        ("123456789012", True),
        ("12345678901", False),
        ("1234567890123", False),
        ("12345A789012", False),
        ("", False),
    ]

    for license_num, expected in test_cases:
        result = validate_drivers_license(license_num)
        print(f"Testing license: '{license_num}'")
        print(f"Expected: {expected}, Got: {result}")
        print("✓ PASS" if result == expected else "✗ FAIL")


def test_passcode_validation():
    print("\n=== Testing Passcode Validation ===")

    test_cases = [
        ("123456", True),
        ("12345", False),
        ("1234567", False),
        ("12345A", False),
        ("", False),
    ]

    for passcode, expected in test_cases:
        result = validate_passcode(passcode)
        print(f"Testing passcode: '{passcode}'")
        print(f"Expected: {expected}, Got: {result}")
        print("✓ PASS" if result == expected else "✗ FAIL")


def test_zesa_meter_validation():
    print("\n=== Testing ZESA Meter Validation ===")

    test_cases = [
        ("37132456296", True),
        ("3713245629", False),
        ("371324562960", False),
        ("3713245629A", False),
        ("", False),
    ]

    for meter, expected in test_cases:
        result = validate_zesa_meter(meter)
        print(f"Testing meter: '{meter}'")
        print(f"Expected: {expected}, Got: {result}")
        print("✓ PASS" if result == expected else "✗ FAIL")


def run_all_tests():
    """Run all validation tests"""
    test_name_validation()
    test_address_validation()
    test_id_validation()
    test_drivers_license_validation()
    test_passcode_validation()
    test_zesa_meter_validation()


if __name__ == "__main__":
    run_all_tests()
