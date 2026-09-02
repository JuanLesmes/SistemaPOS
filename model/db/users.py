"""Usuarios, roles e inicio de sesión."""

from __future__ import annotations

import psycopg2
import psycopg2.errors

from model.db.mappers import user_from
from model.errors import AppError
from model.user import ROLE_ADMIN, ROLES, User
from utils.passwords import hash_password, verify_password


class UsersMixin:
    def count_users(self) -> int:
        with self._transaction() as cur:
            cur.execute("SELECT count(*) AS n FROM users")
            return int(cur.fetchone()["n"])

    def list_users(self) -> list[User]:
        with self._transaction() as cur:
            cur.execute("SELECT id, username, full_name, role, active FROM users ORDER BY active DESC, lower(username)")
            return [user_from(row) for row in cur.fetchall()]

    def get_user(self, username: str) -> User | None:
        with self._transaction() as cur:
            cur.execute(
                "SELECT id, username, full_name, role, active FROM users WHERE username = %s",
                (username.strip().lower(),),
            )
            row = cur.fetchone()
            return user_from(row) if row else None

    def create_user(self, username: str, full_name: str, role: str, password: str) -> User:
        username = username.strip().lower()
        if not username or not username.replace(".", "").replace("_", "").isalnum():
            raise AppError("El nombre de usuario solo puede tener letras, números, punto y guion bajo.")
        if role not in ROLES:
            raise AppError(f"Rol desconocido: {role}.")
        try:
            password_hash = hash_password(password)
        except ValueError as exc:
            raise AppError(str(exc)) from exc
        with self._transaction() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO users (username, full_name, password_hash, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, username, full_name, role, active
                    """,
                    (username, full_name.strip(), password_hash, role),
                )
            except psycopg2.errors.UniqueViolation as exc:
                raise AppError(f"Ya existe un usuario llamado '{username}'.") from exc
            user = user_from(cur.fetchone())
            self._log(cur, "add_user", details={"after": {"username": username, "full_name": full_name, "role": role}})
        return user

    def update_user(self, user_id: int, full_name: str, role: str, active: bool) -> None:
        """Cambia nombre, rol y estado. Nunca deja la base sin un administrador activo."""
        if role not in ROLES:
            raise AppError(f"Rol desconocido: {role}.")
        with self._transaction() as cur:
            cur.execute("SELECT id, username, full_name, role, active FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row is None:
                raise AppError("El usuario ya no existe.")
            previous = user_from(row)
            loses_admin = previous.role == ROLE_ADMIN and previous.active and (role != ROLE_ADMIN or not active)
            if loses_admin:
                cur.execute("SELECT count(*) AS n FROM users WHERE role = 'admin' AND active AND id <> %s", (user_id,))
                if int(cur.fetchone()["n"]) == 0:
                    raise AppError("No se puede: quedaría la aplicación sin ningún administrador activo.")
            cur.execute(
                "UPDATE users SET full_name = %s, role = %s, active = %s WHERE id = %s",
                (full_name.strip(), role, active, user_id),
            )
            self._log(
                cur,
                "modify_user",
                details={
                    "before": {"full_name": previous.full_name, "role": previous.role, "active": previous.active},
                    "after": {"full_name": full_name.strip(), "role": role, "active": active},
                },
            )

    def set_password(self, user_id: int, password: str) -> None:
        try:
            password_hash = hash_password(password)
        except ValueError as exc:
            raise AppError(str(exc)) from exc
        with self._transaction() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s RETURNING username", (password_hash, user_id)
            )
            row = cur.fetchone()
            if row is None:
                raise AppError("El usuario ya no existe.")
            self._log(cur, "change_password", details={"username": row["username"]})

    def authenticate(self, username: str, password: str) -> User | None:
        """Devuelve el usuario si la clave es correcta y está activo; en ese caso queda como usuario actual."""
        with self._transaction() as cur:
            cur.execute(
                "SELECT id, username, full_name, role, active, password_hash FROM users WHERE username = %s",
                (username.strip().lower(),),
            )
            row = cur.fetchone()
            if row is None or not row["active"] or not verify_password(password, row["password_hash"]):
                return None
            cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (row["id"],))
            user = user_from(row)
        self.current_user = user.username
        return user
