"""One-off migration: move the users table to hashed passwords."""

import sqlite3

from werkzeug.security import generate_password_hash

DATABASE = os.environ.get("DATABASE_PATH", "minimart.db")

connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row

columns = [row["name"] for row in connection.execute("PRAGMA table_info(users)")]
if "password_hash" in columns:
    print("The users table is already migrated. Nothing to do.")
    connection.close()
    raise SystemExit

old_rows = []
if columns:
    old_rows = connection.execute("SELECT username, password, role FROM users").fetchall()

connection.execute("DROP TABLE IF EXISTS users_new")
connection.execute(
    "CREATE TABLE users_new ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "username TEXT NOT NULL UNIQUE, "
    "password_hash TEXT NOT NULL, "
    "role TEXT NOT NULL)"
)
for row in old_rows:
    connection.execute(
        "INSERT INTO users_new (username, password_hash, role) VALUES (?, ?, ?)",
        (row["username"], generate_password_hash(row["password"]), row["role"]),
    )
connection.execute("DROP TABLE IF EXISTS users")
connection.execute("ALTER TABLE users_new RENAME TO users")
connection.commit()
connection.close()
print(f"Migrated {len(old_rows)} user(s) to hashed passwords.")