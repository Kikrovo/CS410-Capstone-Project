# auth.py
# Probably will be using Flask later — for now no imports.

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

# ─────────────────────────────────────────
# Role constants
# ─────────────────────────────────────────
ROLE_ADMIN = "admin"
ROLE_HOMEOWNER = "homeowner"
ROLE_FAMILY = "family"
ROLE_GUEST = "guest"


# ─────────────────────────────────────────
# User Class (replaces old dictionary users)
# ─────────────────────────────────────────
@dataclass
class User:
    email: str
    password: str
    role: str
    active: bool = True

    # Homeowner-only
    cameras: List[str] = field(default_factory=list)

    # Family/Guest-only
    allowed_cameras: List[str] = field(default_factory=list)
    access_start: Optional[int] = None
    access_end: Optional[int] = None


# ─────────────────────────────────────────
# Auth Manager (replaces globals + free functions)
# ─────────────────────────────────────────
class AuthManager:
    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._current_user_email: Optional[str] = None
        self._bootstrap_default_users()

    # Default required users
    def _bootstrap_default_users(self) -> None:
        homeowner = User(
            email="homeowner@gmail.com",
            password="password123",
            role=ROLE_HOMEOWNER,
            cameras=["front_door", "backyard", "basement"],
        )
        admin = User(
            email="admin@system.local",
            password="admin123",
            role=ROLE_ADMIN,
        )

        self._users[homeowner.email] = homeowner
        self._users[admin.email] = admin

    # ─────────────────────────────────────────
    # Login / Logout / Current User
    # ─────────────────────────────────────────
    def login_user(self, email: str, password: Optional[str] = None) -> bool:
        user = self._users.get(email)
        if not user or not user.active:
            self._current_user_email = None
            return False

        if password is not None and password != user.password:
            self._current_user_email = None
            return False

        self._current_user_email = email
        return True

    def logout_user(self) -> None:
        self._current_user_email = None

    def current_user(self) -> Optional[User]:
        if self._current_user_email is None:
            return None

        user = self._users.get(self._current_user_email)
        if not user or not user.active:
            return None

        return user

    def login_req(self) -> User:
        user = self.current_user()
        if user is None:
            raise PermissionError("Authentication required.")
        return user

    # ─────────────────────────────────────────
    # Role Helpers
    # ─────────────────────────────────────────
    @staticmethod
    def has_role(user: Optional[User], role: str) -> bool:
        return user is not None and user.role == role

    def is_admin(self, user: Optional[User]) -> bool:
        return self.has_role(user, ROLE_ADMIN)

    def is_homeowner(self, user: Optional[User]) -> bool:
        return self.has_role(user, ROLE_HOMEOWNER)

    def is_family(self, user: Optional[User]) -> bool:
        return self.has_role(user, ROLE_FAMILY)

    def is_guest(self, user: Optional[User]) -> bool:
        return self.has_role(user, ROLE_GUEST)

    # ─────────────────────────────────────────
    # Admin Actions
    # ─────────────────────────────────────────
    def admin_create_user(self, email: str, password: str, role: str) -> User:
        admin = self.current_user()
        if not self.is_admin(admin):
            raise PermissionError("Only administrators can create users.")

        if email in self._users:
            raise ValueError("User already exists.")

        user = User(email=email, password=password, role=role)
        self._users[email] = user
        return user

    def admin_deactivate_user(self, email: str) -> User:
        admin = self.current_user()
        if not self.is_admin(admin):
            raise PermissionError("Only administrators can deactivate users.")

        user = self._users.get(email)
        if not user:
            raise ValueError("User not found.")

        user.active = False
        return user

    def admin_delete_user(self, email: str) -> None:
        admin = self.current_user()
        if not self.is_admin(admin):
            raise PermissionError("Only administrators can delete users.")

        if email not in self._users:
            raise ValueError("User not found.")

        del self._users[email]

    # ─────────────────────────────────────────
    # Homeowner Actions
    # ─────────────────────────────────────────
    def homeowner_create_guest(
        self,
        guest_email: str,
        password: str,
        allowed_cameras: List[str],
        access_start: int,
        access_end: int,
    ) -> User:
        owner = self.current_user()
        if not self.is_homeowner(owner):
            raise PermissionError("Only homeowners can create guest users.")

        if guest_email in self._users:
            raise ValueError("Guest email already exists.")

        guest = User(
            email=guest_email,
            password=password,
            role=ROLE_GUEST,
            allowed_cameras=list(allowed_cameras),
            access_start=access_start,
            access_end=access_end,
        )
        self._users[guest_email] = guest
        return guest

    def homeowner_share_camera_with_family(
        self,
        family_email: str,
        password: str,
        allowed_cameras: List[str],
    ) -> User:
        owner = self.current_user()
        if not self.is_homeowner(owner):
            raise PermissionError(
                "Only homeowners can manage family accounts."
            )

        if family_email in self._users:
            member = self._users[family_email]
            member.role = ROLE_FAMILY
            member.allowed_cameras = list(allowed_cameras)
        else:
            member = User(
                email=family_email,
                password=password,
                role=ROLE_FAMILY,
                allowed_cameras=list(allowed_cameras),
            )
            self._users[family_email] = member

        return member

    # ─────────────────────────────────────────
    # Permission Checks
    # ─────────────────────────────────────────
    def can_view_camera(
        self,
        user: Optional[User],
        camera_id: str,
        current_time: int,
        action: str = "live",
    ) -> Tuple[bool, str]:

        if user is None or not user.active:
            return False, "You must be logged in."

        # Admin = full access
        if user.role == ROLE_ADMIN:
            return True, "Administrator access granted."

        # Homeowner
        if user.role == ROLE_HOMEOWNER:
            if action in ("live", "playback"):
                if camera_id in user.cameras:
                    return True, "Homeowner access granted."
                return False, "Camera not part of your system."

            if action == "settings":
                return True, "Homeowner may modify settings."

            if action == "user_mgmt":
                return False, "User management allowed only for admin."

        # Family
        if user.role == ROLE_FAMILY:
            if camera_id not in user.allowed_cameras:
                return False, "This camera is not shared with you."

            if action == "live":
                return True, "Family member live-view allowed."

            return False, (
                "Family accounts cannot view playback or change settings."
            )

        # Guest (time-limited)
        if user.role == ROLE_GUEST:
            if camera_id not in user.allowed_cameras:
                return False, "This guest invite does not include this camera."

            if user.access_start and current_time < user.access_start:
                return False, "Guest access not started."

            if user.access_end and current_time > user.access_end:
                return False, "Guest access expired."

            if action == "live":
                return True, "Guest live-view allowed within time window."

            return False, "Guests cannot access playback or settings."

        return False, "Unknown role — access denied."
