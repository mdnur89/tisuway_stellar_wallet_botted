import sqlite3

# Database initialization
def init_db():
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users
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
                      wallet_balance REAL DEFAULT 0.0)"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      phone_number TEXT,
                      transaction_type TEXT,
                      amount REAL,
                      timestamp DATETIME,
                      description TEXT)"""
        )
        conn.commit()
