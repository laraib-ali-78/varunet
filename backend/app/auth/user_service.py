"""
Users Table Integration Service
Interacts with the Section 1 `users` table using bcrypt-hashed passwords.
"""

from typing import Dict, Any, Optional
from backend.app.auth.jwt_handler import hash_password, verify_password

# Demo seed accounts when DB is in memory or cold start
DEFAULT_USERS: Dict[str, Dict[str, Any]] = {
    "forecaster@varunet.in": {
        "user_id": 1,
        "email": "forecaster@varunet.in",
        "password_hash": hash_password("Forecaster@123"),
        "role": "forecaster",
    },
    "admin@varunet.in": {
        "user_id": 2,
        "email": "admin@varunet.in",
        "password_hash": hash_password("Admin@123"),
        "role": "admin",
    },
    "citizen@varunet.in": {
        "user_id": 3,
        "email": "citizen@varunet.in",
        "password_hash": hash_password("Citizen@123"),
        "role": "citizen",
    },
}


def get_user_by_email(db_session, email: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a user by email from the PostgreSQL users table or default store.
    """
    email_clean = email.strip().lower()

    if db_session is not None:
        sql = "SELECT user_id, email, password_hash, role FROM users WHERE email = :email LIMIT 1;"
        has_sqlalchemy = False
        try:
            from sqlalchemy import text
            has_sqlalchemy = True
        except ImportError:
            has_sqlalchemy = False

        try:
            if has_sqlalchemy and hasattr(db_session, "execute"):
                res = db_session.execute(text(sql), {"email": email_clean})
                row = res.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "email": row[1],
                        "password_hash": row[2],
                        "role": row[3],
                    }
        except Exception:
            pass

    # Check default in-memory registry
    return DEFAULT_USERS.get(email_clean)


def create_user(
    db_session,
    email: str,
    password: str,
    role: str = "citizen",
) -> Dict[str, Any]:
    """
    Creates a new user record with bcrypt-hashed password in the `users` table.
    """
    email_clean = email.strip().lower()
    pw_hash = hash_password(password)

    user_id = len(DEFAULT_USERS) + 1

    if db_session is not None:
        sql = """
        INSERT INTO users (email, password_hash, role)
        VALUES (:email, :password_hash, :role)
        RETURNING user_id;
        """
        try:
            from sqlalchemy import text
            res = db_session.execute(text(sql), {
                "email": email_clean,
                "password_hash": pw_hash,
                "role": role,
            })
            row = res.fetchone()
            if row:
                user_id = row[0]
            db_session.commit()
        except Exception:
            pass

    new_user = {
        "user_id": user_id,
        "email": email_clean,
        "password_hash": pw_hash,
        "role": role,
    }
    DEFAULT_USERS[email_clean] = new_user
    return new_user


def authenticate_user(
    db_session,
    email: str,
    password: str,
) -> Optional[Dict[str, Any]]:
    """
    Validates user credentials against stored bcrypt hash.
    """
    user = get_user_by_email(db_session, email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user
