import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from app import init_db, get_user

def test_database_operations():
    print("\n=== Testing Database Operations ===")
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    print("✓ Database initialized")
    
    # Test user creation
    print("\nTesting user creation...")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    test_user = {
        'phone_number': '+263777777777',
        'first_name': 'Test',
        'last_name': 'User',
        'surname': 'Testing',
        'nationality': 'Zimbabwean',
        'address': '123 Test Street, Harare',
        'id_type': 'National ID',
        'id_number': '63-123456A42',
        'verification_method': 'SMS',
        'passcode': '123456',
        'registration_complete': True,
        'current_state': 'main_menu',
        'wallet_balance': 0.0
    }
    
    try:
        c.execute('''INSERT INTO users 
                     (phone_number, first_name, last_name, surname, nationality,
                      address, id_type, id_number, verification_method, passcode,
                      registration_complete, current_state, wallet_balance)
                     VALUES 
                     (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 tuple(test_user.values()))
        conn.commit()
        print("✓ Test user created")
        
        # Test user retrieval
        print("\nTesting user retrieval...")
        retrieved_user = get_user(test_user['phone_number'])
        if retrieved_user:
            print("✓ User retrieved successfully")
            print("\nUser data:")
            for key, value in retrieved_user.items():
                print(f"{key}: {value}")
        else:
            print("✗ Failed to retrieve user")
        
    except sqlite3.IntegrityError:
        print("! Test user already exists")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    finally:
        # Cleanup
        print("\nCleaning up test data...")
        c.execute('DELETE FROM users WHERE phone_number = ?', (test_user['phone_number'],))
        conn.commit()
        conn.close()
        print("✓ Test data cleaned up")

if __name__ == "__main__":
    test_database_operations()