import os
import sys

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app import app, UserState, update_user_state, get_user_state

def test_zim_services_navigation():
    print("\n=== Testing Zimbabwe Services Navigation ===")
    sender = "test_user"
    
    # Test main menu to Zim services
    print("\nTesting Main Menu State:")
    update_user_state(sender, UserState.MAIN_MENU)
    current_state = get_user_state(sender)
    print(f"Expected: {UserState.MAIN_MENU}")
    print(f"Got: {current_state}")
    print("✓ PASS" if current_state == UserState.MAIN_MENU else "✗ FAIL")
    
    # Test Zim services menu
    print("\nTesting Zim Services Menu State:")
    update_user_state(sender, UserState.ZIM_SERVICES_MENU)
    current_state = get_user_state(sender)
    print(f"Expected: {UserState.ZIM_SERVICES_MENU}")
    print(f"Got: {current_state}")
    print("✓ PASS" if current_state == UserState.ZIM_SERVICES_MENU else "✗ FAIL")
    
    # Test Data menu
    print("\nTesting Data Menu State:")
    update_user_state(sender, UserState.DATA_MENU)
    current_state = get_user_state(sender)
    print(f"Expected: {UserState.DATA_MENU}")
    print(f"Got: {current_state}")
    print("✓ PASS" if current_state == UserState.DATA_MENU else "✗ FAIL")

def test_menu_flow():
    print("\n=== Testing Menu Flow Navigation ===")
    sender = "test_user"
    
    menu_flows = [
        (UserState.MAIN_MENU, "2", UserState.ZIM_SERVICES_MENU, "Main Menu → Zim Services"),
        (UserState.ZIM_SERVICES_MENU, "2", UserState.DATA_MENU, "Zim Services → Data Menu"),
        (UserState.DATA_MENU, "back", UserState.ZIM_SERVICES_MENU, "Data Menu → Back to Zim Services"),
        (UserState.ZIM_SERVICES_MENU, "menu", UserState.MAIN_MENU, "Zim Services → Main Menu")
    ]
    
    for current_state, input_msg, expected_state, description in menu_flows:
        print(f"\nTesting: {description}")
        print(f"Current State: {current_state}")
        print(f"Input Message: '{input_msg}'")
        print(f"Expected Next State: {expected_state}")
        
        try:
            # Set initial state
            update_user_state(sender, current_state)
            initial_state = get_user_state(sender)
            print(f"Initial State Set: {initial_state}")
            
            # Simulate message handling
            if input_msg == "back":
                print("Processing 'back' command...")
                update_user_state(sender, expected_state)
            elif input_msg == "menu":
                print("Processing 'menu' command...")
                update_user_state(sender, UserState.MAIN_MENU)
            else:
                print(f"Processing menu selection: {input_msg}")
                update_user_state(sender, expected_state)
            
            # Check final state
            final_state = get_user_state(sender)
            print(f"Final State: {final_state}")
            
            if final_state == expected_state:
                print("✓ PASS")
            else:
                print("✗ FAIL")
                print(f"Expected: {expected_state}")
                print(f"Got: {final_state}")
                
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")

def run_navigation_tests():
    """Run all navigation tests"""
    try:
        test_zim_services_navigation()
        test_menu_flow()
        print("\n=== Navigation Tests Complete ===")
    except Exception as e:
        print(f"\n✗ Test Suite Error: {str(e)}")

if __name__ == "__main__":
    run_navigation_tests()