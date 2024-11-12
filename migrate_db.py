import sqlite3

def migrate_database():
    print("Starting database migration...")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Create temporary table with new schema
        c.execute('''CREATE TABLE users_new
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
        
        # Copy data from old table to new table
        c.execute('''INSERT INTO users_new 
                     (phone_number, first_name, surname, nationality, address,
                      id_type, id_number, verification_method, passcode,
                      registration_complete, current_state, wallet_balance)
                     SELECT phone_number, first_name, surname, nationality, address,
                            id_type, id_number, verification_method, passcode,
                            registration_complete, current_state, wallet_balance
                     FROM users''')
        
        # Drop old table
        c.execute('DROP TABLE users')
        
        # Rename new table to users
        c.execute('ALTER TABLE users_new RENAME TO users')
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()