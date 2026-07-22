from __future__ import annotations

from datetime import timedelta
import hashlib
import hmac
import secrets

from agentsystem.config import Settings
from agentsystem.domain import (
    AuthSessionRecord,
    Permission,
    Principal,
    UserCreate,
    UserPublic,
    UserRecord,
    UserRole,
    UserStatus,
    UserUpdate,
    utcnow,
)
from agentsystem.store import AlreadyExistsError, InMemoryStore, NotFoundError


class AuthenticationError(RuntimeError):
    pass


class AuthorizationError(RuntimeError):
    pass


class AuthConfigurationError(RuntimeError):
    pass


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.OPERATOR: frozenset(
        {
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_CHAT,
            Permission.APPROVAL_DECIDE,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.AGENT_READ,
            Permission.OPERATIONS_READ,
            Permission.AUDIT_READ,
        }
    ),
    UserRole.REVIEWER: frozenset(
        {
            Permission.TASK_READ,
            Permission.TASK_CHAT,
            Permission.APPROVAL_DECIDE,
            Permission.PROJECT_READ,
            Permission.AGENT_READ,
            Permission.OPERATIONS_READ,
            Permission.AUDIT_READ,
        }
    ),
    UserRole.VIEWER: frozenset(
        {
            Permission.TASK_READ,
            Permission.PROJECT_READ,
            Permission.AGENT_READ,
        }
    ),
}


class AuthService:
    def __init__(self, store: InMemoryStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        if settings.auth_mode not in {"dev", "local"}:
            raise AuthConfigurationError("AGENTSYSTEM_AUTH_MODE must be 'dev' or 'local'")
        if settings.auth_mode == "local":
            self._bootstrap_local_admin()

    def principal_for_token(self, token: str | None) -> Principal:
        if self.settings.auth_mode == "dev":
            return self.dev_principal()
        if not token:
            raise AuthenticationError("Sign in is required")
        session = self.store.get_auth_session_by_token_hash(self._token_hash(token))
        now = utcnow()
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise AuthenticationError("The session is missing, expired, or revoked")
        try:
            user = self.store.get_user(session.user_id)
        except NotFoundError as exc:
            raise AuthenticationError("The session user no longer exists") from exc
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError("The user account is disabled")
        session.last_seen_at = now
        self.store.update_auth_session(session)
        return self._principal(user, auth_mode="local")

    def login(self, username: str, password: str) -> tuple[str | None, UserPublic]:
        if self.settings.auth_mode == "dev":
            return None, self.dev_user()
        user = self.store.find_user("default", username.strip())
        if user is None or not self.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError("The user account is disabled")
        token = secrets.token_urlsafe(48)
        now = utcnow()
        session = AuthSessionRecord(
            user_id=user.id,
            token_hash=self._token_hash(token),
            expires_at=now + timedelta(hours=self.settings.auth_session_ttl_hours),
        )
        self.store.add_auth_session(session)
        user.last_login_at = now
        self.store.update_user(user)
        return token, UserPublic.from_record(user)

    def logout(self, token: str | None) -> None:
        if not token or self.settings.auth_mode == "dev":
            return
        session = self.store.get_auth_session_by_token_hash(self._token_hash(token))
        if session is None or session.revoked_at is not None:
            return
        session.revoked_at = utcnow()
        self.store.update_auth_session(session)

    def require(self, principal: Principal, permission: Permission) -> None:
        if permission not in ROLE_PERMISSIONS[principal.role]:
            raise AuthorizationError(f"Role '{principal.role.value}' cannot perform '{permission.value}'")

    def list_users(self, principal: Principal) -> list[UserPublic]:
        self.require(principal, Permission.USER_MANAGE)
        if self.settings.auth_mode == "dev":
            return [self.dev_user()]
        return [UserPublic.from_record(item) for item in self.store.list_users(principal.tenant_id)]

    def create_user(self, principal: Principal, payload: UserCreate) -> UserPublic:
        self.require(principal, Permission.USER_MANAGE)
        if self.settings.auth_mode == "dev":
            raise AuthorizationError("Switch to local authentication before managing users")
        user = UserRecord(
            tenant_id=principal.tenant_id,
            username=payload.username.strip().lower(),
            display_name=payload.display_name.strip(),
            password_hash=self.hash_password(payload.password),
            role=payload.role,
        )
        try:
            self.store.add_user(user)
        except AlreadyExistsError as exc:
            raise AlreadyExistsError("A user with that username already exists") from exc
        return UserPublic.from_record(user)

    def update_user(self, principal: Principal, user_id: str, payload: UserUpdate) -> UserPublic:
        self.require(principal, Permission.USER_MANAGE)
        if self.settings.auth_mode == "dev":
            raise AuthorizationError("The development identity is managed by the server")
        user = self.store.get_user(user_id)
        if user.tenant_id != principal.tenant_id:
            raise NotFoundError(user_id)
        removing_admin = user.role == UserRole.ADMIN and (
            (payload.role is not None and payload.role != UserRole.ADMIN)
            or payload.status == UserStatus.DISABLED
        )
        if removing_admin:
            active_admins = [
                item
                for item in self.store.list_users(principal.tenant_id)
                if item.role == UserRole.ADMIN and item.status == UserStatus.ACTIVE
            ]
            if len(active_admins) <= 1:
                raise AuthorizationError("The last active administrator cannot be removed or disabled")
        if payload.display_name is not None:
            user.display_name = payload.display_name.strip()
        if payload.password is not None:
            user.password_hash = self.hash_password(payload.password)
            self.store.revoke_user_sessions(user.id)
        if payload.role is not None:
            user.role = payload.role
        if payload.status is not None:
            user.status = payload.status
            if payload.status == UserStatus.DISABLED:
                self.store.revoke_user_sessions(user.id)
        return UserPublic.from_record(self.store.update_user(user))

    def user_for_principal(self, principal: Principal) -> UserPublic:
        if principal.auth_mode == "dev":
            return self.dev_user()
        user = self.store.get_user(principal.user_id)
        if user.tenant_id != principal.tenant_id:
            raise AuthenticationError("The session tenant is invalid")
        return UserPublic.from_record(user)

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
        return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        try:
            algorithm, n_value, r_value, p_value, salt_hex, expected_hex = encoded.split("$", 5)
            if algorithm != "scrypt":
                return False
            actual = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=int(n_value),
                r=int(r_value),
                p=int(p_value),
                dklen=len(bytes.fromhex(expected_hex)),
            )
            return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _bootstrap_local_admin(self) -> None:
        if self.store.list_users("default"):
            return
        password = self.settings.bootstrap_admin_password
        if password is None:
            raise AuthConfigurationError(
                "AGENTSYSTEM_BOOTSTRAP_ADMIN_PASSWORD is required for the first local-auth startup"
            )
        self.store.add_user(
            UserRecord(
                id="user_local_admin",
                tenant_id="default",
                username=self.settings.bootstrap_admin_username.strip().lower(),
                display_name=self.settings.bootstrap_admin_display_name.strip(),
                password_hash=self.hash_password(password.get_secret_value()),
                role=UserRole.ADMIN,
            )
        )

    @staticmethod
    def dev_principal() -> Principal:
        return Principal(
            user_id="user_local_admin",
            tenant_id="default",
            username="local-admin",
            display_name="Local Administrator",
            role=UserRole.ADMIN,
            auth_mode="dev",
        )

    @classmethod
    def dev_user(cls) -> UserPublic:
        now = utcnow()
        principal = cls.dev_principal()
        return UserPublic(
            id=principal.user_id,
            tenant_id=principal.tenant_id,
            username=principal.username,
            display_name=principal.display_name,
            role=principal.role,
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _principal(user: UserRecord, auth_mode: str) -> Principal:
        return Principal(
            user_id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            auth_mode=auth_mode,
        )
