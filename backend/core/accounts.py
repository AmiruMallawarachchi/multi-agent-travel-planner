"""Account authentication and per-user conversation storage.

The implementation uses stdlib SQLite so local development stays dependency
light. The API is intentionally repository-shaped so production can swap this
module for Postgres without changing HTTP routes or frontend contracts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from fastapi import Header, HTTPException, status

try:  # Optional unless DATABASE_URL points at Postgres/Supabase.
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised by deployments without psycopg
    psycopg = None
    dict_row = None

INTEGRITY_ERRORS = (
    (sqlite3.IntegrityError, psycopg.IntegrityError)
    if psycopg is not None
    else (sqlite3.IntegrityError,)
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_ITERATIONS = 210_000
TOKEN_TTL_DAYS = 30


class AccountError(ValueError):
    """Raised when account input is invalid or conflicts with stored state."""


@dataclass(frozen=True)
class AccountUser:
    id: str
    email: str
    name: str
    created_at: str

    def public(self) -> dict[str, str]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at,
        }


def _utc_now() -> datetime:
    return datetime.now(UTC)


class _Connection(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> Any: ...

    def commit(self) -> None: ...


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def _uses_postgres() -> bool:
    url = _database_url()
    return url.startswith(("postgres://", "postgresql://"))


def _db_path() -> Path:
    configured = os.getenv("TRIPWEAVER_DB_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "data" / "tripweaver.sqlite3"


def _sql(query: str) -> str:
    """Translate SQLite placeholders to psycopg placeholders when needed."""
    return query.replace("?", "%s") if _uses_postgres() else query


def _connect() -> _Connection:
    if _uses_postgres():
        if psycopg is None or dict_row is None:
            raise RuntimeError(
                "DATABASE_URL is configured for Postgres but psycopg is not installed"
            )
        url = _database_url()
        if url.startswith("postgres://"):
            url = f"postgresql://{url.removeprefix('postgres://')}"
        connection = psycopg.connect(url, connect_timeout=5, row_factory=dict_row)
        _ensure_schema(connection)
        return connection

    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    _ensure_schema(connection)
    return connection


def account_storage_status() -> dict[str, str]:
    """Return a sanitized health summary for account persistence."""
    backend = "postgres" if _uses_postgres() else "sqlite"
    try:
        with _connect() as connection:
            connection.execute(_sql("SELECT 1"))
        return {"backend": backend, "status": "available"}
    except Exception:  # noqa: BLE001 - health must not leak connection details
        return {"backend": backend, "status": "unavailable"}


def _ensure_schema(connection: _Connection) -> None:
    statements = (
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (id, user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS auth_identities (
            provider TEXT NOT NULL,
            subject TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            PRIMARY KEY (provider, subject)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS plans (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (id, user_id)
        )
        """,
    )
    for statement in statements:
        connection.execute(statement)
    connection.commit()


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_RE.fullmatch(normalized):
        raise AccountError("Enter a valid email address")
    return normalized


def _normalize_name(name: str | None, email: str) -> str:
    value = (name or "").strip()
    if not value:
        value = email.split("@", 1)[0]
    if len(value) > 80:
        raise AccountError("Name must be 80 characters or fewer")
    return value


def _validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AccountError("Password must be at least 8 characters")
    if len(password) > 256:
        raise AccountError("Password is too long")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        padded_salt = salt + "=" * (-len(salt) % 4)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(padded_salt),
            int(iterations),
        )
        return hmac.compare_digest(_b64(candidate), digest)
    except (ValueError, TypeError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _row_to_user(row: sqlite3.Row | dict[str, Any]) -> AccountUser:
    return AccountUser(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        created_at=row["created_at"],
    )


def _create_session(connection: _Connection, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = _utc_now()
    connection.execute(
        _sql(
        """
        INSERT INTO auth_sessions (token_hash, user_id, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        ),
        (
            _hash_token(token),
            user_id,
            (now + timedelta(days=TOKEN_TTL_DAYS)).isoformat(),
            now.isoformat(),
        ),
    )
    return token


def register_user(email: str, password: str, name: str | None = None) -> tuple[str, AccountUser]:
    normalized_email = _normalize_email(email)
    _validate_password(password)
    normalized_name = _normalize_name(name, normalized_email)
    now = _utc_now().isoformat()
    user_id = uuid.uuid4().hex

    with _connect() as connection:
        try:
            connection.execute(
                _sql(
                """
                INSERT INTO users (id, email, name, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ),
                (
                    user_id,
                    normalized_email,
                    normalized_name,
                    _hash_password(password),
                    now,
                ),
            )
        except INTEGRITY_ERRORS as exc:
            raise AccountError("An account with this email already exists") from exc

        token = _create_session(connection, user_id)
        connection.commit()
        user = AccountUser(
            id=user_id,
            email=normalized_email,
            name=normalized_name,
            created_at=now,
        )
        return token, user


def authenticate_user(email: str, password: str) -> tuple[str, AccountUser] | None:
    normalized_email = _normalize_email(email)
    with _connect() as connection:
        row = connection.execute(
            _sql("SELECT * FROM users WHERE email = ?"), (normalized_email,)
        ).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            return None
        token = _create_session(connection, row["id"])
        connection.commit()
        return token, _row_to_user(row)


def authenticate_external_user(
    provider: str,
    subject: str,
    email: str,
    name: str | None = None,
) -> tuple[str, AccountUser]:
    normalized_provider = provider.strip().lower()
    normalized_subject = subject.strip()
    if normalized_provider != "google":
        raise AccountError("Unsupported identity provider")
    if not normalized_subject or len(normalized_subject) > 255:
        raise AccountError("Invalid identity provider subject")

    normalized_email = _normalize_email(email)
    normalized_name = _normalize_name(name, normalized_email)
    now = _utc_now().isoformat()

    with _connect() as connection:
        row = connection.execute(
            _sql(
                """
                SELECT users.*
                FROM auth_identities
                JOIN users ON users.id = auth_identities.user_id
                WHERE auth_identities.provider = ? AND auth_identities.subject = ?
                """
            ),
            (normalized_provider, normalized_subject),
        ).fetchone()

        if not row:
            row = connection.execute(
                _sql("SELECT * FROM users WHERE email = ?"), (normalized_email,)
            ).fetchone()
            if not row:
                user_id = uuid.uuid4().hex
                connection.execute(
                    _sql(
                        """
                        INSERT INTO users (id, email, name, password_hash, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """
                    ),
                    (user_id, normalized_email, normalized_name, "external_only", now),
                )
                row = connection.execute(
                    _sql("SELECT * FROM users WHERE id = ?"), (user_id,)
                ).fetchone()

            connection.execute(
                _sql(
                    """
                    INSERT INTO auth_identities (provider, subject, user_id, created_at)
                    VALUES (?, ?, ?, ?)
                    """
                ),
                (normalized_provider, normalized_subject, row["id"], now),
            )

        token = _create_session(connection, row["id"])
        connection.commit()
        return token, _row_to_user(row)


def user_from_token(token: str) -> AccountUser | None:
    with _connect() as connection:
        row = connection.execute(
            _sql(
            """
            SELECT users.*
            FROM auth_sessions
            JOIN users ON users.id = auth_sessions.user_id
            WHERE auth_sessions.token_hash = ? AND auth_sessions.expires_at > ?
            """,
            ),
            (_hash_token(token), _utc_now().isoformat()),
        ).fetchone()
        return _row_to_user(row) if row else None


def revoke_token(token: str) -> None:
    with _connect() as connection:
        connection.execute(
            _sql("DELETE FROM auth_sessions WHERE token_hash = ?"),
            (_hash_token(token),),
        )
        connection.commit()


async def require_user(authorization: str | None = Header(default=None)) -> AccountUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing account session")
    token = authorization.removeprefix("Bearer ").strip()
    user = user_from_token(token)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired account session")
    return user


def list_user_conversations(user_id: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            _sql(
            """
            SELECT payload
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            ),
            (user_id,),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]


def upsert_user_conversation(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    conversation_id = str(payload.get("id", "")).strip()
    title = str(payload.get("title", "New trip")).strip() or "New trip"
    created_at = str(payload.get("createdAt", _utc_now().isoformat()))
    updated_at = str(payload.get("updatedAt", created_at))
    if not conversation_id or len(conversation_id) > 128:
        raise AccountError("Conversation id is required")

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _connect() as connection:
        connection.execute(
            _sql(
            """
            INSERT INTO conversations (id, user_id, title, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, user_id) DO UPDATE SET
                title = excluded.title,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            ),
            (conversation_id, user_id, title[:160], serialized, created_at, updated_at),
        )
        connection.commit()
    return payload


def clear_user_conversations(user_id: str) -> None:
    with _connect() as connection:
        connection.execute(
            _sql("DELETE FROM conversations WHERE user_id = ?"), (user_id,)
        )
        connection.commit()


def delete_user_conversation(user_id: str, conversation_id: str) -> bool:
    normalized_id = conversation_id.strip()
    if not normalized_id or len(normalized_id) > 128:
        raise AccountError("Conversation id is required")
    with _connect() as connection:
        cursor = connection.execute(
            _sql("DELETE FROM conversations WHERE user_id = ? AND id = ?"),
            (user_id, normalized_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def list_user_plans(user_id: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            _sql(
            """
            SELECT payload
            FROM plans
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            ),
            (user_id,),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]


def upsert_user_plan(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    plan_id = str(payload.get("id", "")).strip()
    name = str(payload.get("name", "")).strip()
    created_at = str(payload.get("createdAt", _utc_now().isoformat()))
    updated_at = str(payload.get("updatedAt", created_at))
    if not plan_id or len(plan_id) > 128:
        raise AccountError("Plan id is required")
    if not name:
        raise AccountError("Plan name is required")
    if len(name) > 80:
        raise AccountError("Plan name must be 80 characters or fewer")

    normalized = {
        **payload,
        "id": plan_id,
        "name": name,
        "createdAt": created_at,
        "updatedAt": updated_at,
    }
    serialized = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    with _connect() as connection:
        connection.execute(
            _sql(
            """
            INSERT INTO plans (id, user_id, name, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, user_id) DO UPDATE SET
                name = excluded.name,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            ),
            (plan_id, user_id, name, serialized, created_at, updated_at),
        )
        connection.commit()
    return normalized


def delete_user_plan(user_id: str, plan_id: str) -> bool:
    normalized_id = plan_id.strip()
    if not normalized_id or len(normalized_id) > 128:
        raise AccountError("Plan id is required")

    with _connect() as connection:
        cursor = connection.execute(
            _sql("DELETE FROM plans WHERE user_id = ? AND id = ?"),
            (user_id, normalized_id),
        )
        rows = connection.execute(
            _sql("SELECT id, payload FROM conversations WHERE user_id = ?"),
            (user_id,),
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload"])
            if payload.get("planId") != normalized_id:
                continue
            payload.pop("planId", None)
            connection.execute(
                _sql("UPDATE conversations SET payload = ? WHERE user_id = ? AND id = ?"),
                (
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    user_id,
                    row["id"],
                ),
            )
        connection.commit()
        return cursor.rowcount > 0

