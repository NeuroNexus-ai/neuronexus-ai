from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Default database path
DB_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "neuronexus.sqlite3"
USERNAME = "admin"
NEW_PASS = "admin123"

def main(db_path: Path) -> int:
    """
    Resets or inserts the admin user with default credentials into the SQLite database.

    Args:
        db_path (Path): Path to the SQLite database file.

    Returns:
        int: 0 if the operation was successful, 1 otherwise.

    Notes:
        - Creates the users table if it doesn't exist.
        - Updates existing admin user or inserts a new one with hashed password.
    """
    try:
        try:
            from passlib.hash import bcrypt
        except Exception as e:
            print("Warning: passlib not installed. Run: .venv\\Scripts\\python -m pip install passlib bcrypt")
            raise

        password_hash = bcrypt.hash(NEW_PASS)

        # Connect to SQLite
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA journal_mode=WAL;")
        cur = con.cursor()

        # Ensure the users table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(128) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_superuser BOOLEAN NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Update or insert the admin user
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("SELECT id FROM users WHERE username = ?", (USERNAME,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE users
                SET password_hash=?, is_active=1, is_superuser=1
                WHERE username=?
            """, (password_hash, USERNAME))
            action = "updated"
        else:
            cur.execute("""
                INSERT INTO users (username, password_hash, is_superuser, is_active, created_at)
                VALUES (?, ?, 1, 1, ?)
            """, (USERNAME, password_hash, now))
            action = "inserted"

        con.commit()
        con.close()
        print(f"Success: {action} admin.  username=admin  password={NEW_PASS}")
        return 0

    except sqlite3.OperationalError as e:
        print(f"SQLite error: {e}")
        print("Tip: Close the API server if you see a lock error, then retry.")
        return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_DEFAULT
    print(f"Database path: {db}")
    sys.exit(main(db))
