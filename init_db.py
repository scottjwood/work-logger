import sqlite3

def update_database():
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    # Adding the rate column if it doesn't exist
    try:
        cursor.execute('ALTER TABLE entries ADD COLUMN billing_rate REAL DEFAULT 0.0')
        print("Database updated with Billing Rate column!")
    except:
        print("Column already exists.")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_database()