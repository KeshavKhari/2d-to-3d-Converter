import sqlite3

# Create a new database or connect to the existing one
conn = sqlite3.connect('users.db')

# Create a cursor
c = conn.cursor()

# Create users table
c.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL
    )
''')

# Commit changes and close the connection
conn.commit()
conn.close()
