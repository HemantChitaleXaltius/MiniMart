"""Create a user with a hashed password. Run: python create_user.py"""

import sqlite3
import config

from getpass import getpass

from werkzeug.security import generate_password_hash

DATABASE = config.DATABASE_PATH

username = input("Username: ").strip()
role = input("Role (admin or shopper): ").strip()
password = getpass("Password (hidden as you type): ")
repeat = getpass("Repeat password: ")

if not username:
    raise SystemExit("Username cannot be empty.")
if role not in ("admin", "shopper"):
    raise SystemExit("Role must be exactly admin or shopper.")
if len(password) < 8:
    raise SystemExit("Password must be at least 8 characters.")
if password != repeat:
    raise SystemExit("The two passwords do not match.")

connection = sqlite3.connect(DATABASE)
try:
    connection.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), role),
    )
    connection.commit()
    print(f"Created {role} account '{username}'.")
except sqlite3.IntegrityError:
    print(f"A user called '{username}' already exists.")
except sqlite3.OperationalError:
    print("The users table is missing. Start the app once so it creates the tables, then try again.")
finally:
    connection.close()