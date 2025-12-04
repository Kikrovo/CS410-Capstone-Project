# Probably will be using flask, for now no imports.

# auth.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

# ─────────────────────────────────────────
# Role constants
# ─────────────────────────────────────────
ROLE_ADMIN = "admin"           # System Administrator
ROLE_HOMEOWNER = "homeowner"   # Homeowner
ROLE_FAMILY = "family"         # Family Member
ROLE_GUEST = "guest"           # Guest User


# ─────────────────────────────────────────
# User class
# ─────────────────────────────────────────
@dataclass
class User:
    email: str
    password: str
    role: str
    active: bool = True

    # For homeowners: list of all cameras they own
    cameras: List[str] = field(default_factory=list)

    # For guests / family: cameras shared with them
    allowed_cameras: List[str] = field(default_factory=list)

    # For guests: numeric timestamps defining the access window
    access_start: Optional[int] = None
    access_end: Optional[int] = None


# ─────────────────────────────────────────
# Auth manager: no globals, all state here
# ─────────────────────────────────────────
class AuthManager:
    def __init__(self) -> None:
        # Internal user store: email -> User
        self._users: Dict[str, User] = {}

        # "Session" tracking: email of currently logged in user, or None
        self._current_user_email: Optional[str] = None

        # Seed with your hardcoded users
        self._bootstrap_default_users()

    def _bootstrap_default_users(self) -> None:
        """Initialize the built-in users from your original dictionary."""
        homeowner = User(
            email="homeowner@gmail.com",
            password="password123",
            role=ROLE_HOMEOWNER,
            active=True,
            cameras=["front_door", "backyard", "basement"],
        )
        admin = User(
            email="admin@system.local",
            password="admin123",
            role=ROLE_ADMIN,
            active=True,
        )

        self._users[homeowner.email] = homeowner
        self._users[admin.email] = admin

    # ─────────────────────────────────────────
    # Basic session / login helpers
    # ─────────────────────────────────────────
    def login_user(self, email: str, password: Optional[str] = None) -> bool:
        """
        Mark the user as logged in.

        Returns:
            True on success, False on failure.
        """
        user = self._users.get(email)
        if not user:
            self._current_user_email = None
            return False

        if not user.active:
            self._current_user_email = None
            return False

        # If you want password checking, do it here.
        if password is not None and user.password != password:
            self._current_user_email = None
            return False

        self._current_user_email = email
        return True

    def logout_user(self) -> None:
        """Clear the currently logged-in user."""
        self._current_user_email = None

    def current_user(self) -> Optional[User]:
        """
        Return the currently logged-in User, or None
        if nobody is logged in or user is not found/inactive.
        """
        if self._current_user_email is None:
            return None

        user = self._users.get(self._current_user_email)
        if user is None or not user.active:
            return None

        return user

    def login_req(self) -> User:
        """
        Ensure only logged-in users have camera access.

        Returns:
            User object on success.
        Raises:
            PermissionError if not logged in or deactivated.
        """
        user = self.current_user()
        if user is None:
            raise PermissionError("Authentication required.")
        return user

    # ─────────────────────────────────────────
    # Role helpers
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
    # Admin capabilities (System Administrator)
    # ─────────────────────────────────────────
    def admin_create_user(self, email: str, password: str, role: str) -> User:
        """
        Admin can create users and assign them a role.
        Requires current_user() to be an admin.
        """
        admin = self.current_user()
        if not self.is_admin(admin):
            raise PermissionError("Only administrators can create users.")

        if email in self._users:
            raise ValueError("User already exists.")

        user = User(
            email=email,
            password=password,
            role=role,
            active=True,
        )
        self._users[email] = user
        return user

    def admin_deactivate_user(self, email: str) -> User:
        """
        Admin can deactivate a user.
        """
        admin = self.current_user()
        if not self.is_admin(admin):
            raise PermissionError("Only administrators can deactivate users.")

        user = self._users.get(email)
        if not user:
            raise ValueError("User not found.")

        user.active = False
        return user

    def admin_delete_user(self, email: str) -> None:
        """
        Admin can delete a user.
        """
        admin = self.current_user()
        if not self.is_admin(admin):
            raise PermissionError("Only administrators can delete users.")

        if email not in self._users:
            raise ValueError("User not found.")

        del self._users[email]

    # ─────────────────────────────────────────
    # Homeowner capabilities (Guest / Family management)
    # ─────────────────────────────────────────
    def homeowner_create_guest(
        self,
        guest_email: str,
        password: str,
        allowed_cameras: List[str],
        access_start: int,
        access_end: int,
    ) -> User:
        """
        Homeowner creates a time-bounded guest with access
        to specific cameras.

        access_start / access_end are opaque numeric values;
        comparison is done as simple numbers.
        """
        owner = self.current_user()
        if not self.is_homeowner(owner):
            raise PermissionError("Only homeowners can create guest users.")

        if guest_email in self._users:
            raise ValueError("Guest email already exists as a user.")

        guest = User(
            email=guest_email,
            password=password,
            role=ROLE_GUEST,
            active=True,
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
        """
        Homeowner creates or updates a family member account
        with access to specific cameras.
        """
        owner = self.current_user()
        if not self.is_homeowner(owner):
            raise PermissionError("Only homeowners can manage family access.")

        if family_email in self._users:
            user = self._users[family_email]
            user.role = ROLE_FAMILY
            user.allowed_cameras = list(allowed_cameras)
        else:
            user = User(
                email=family_email,
                password=password,
                role=ROLE_FAMILY,
                active=True,
                allowed_cameras=list(allowed_cameras),
            )
            self._users[family_email] = user

        return user

    # ─────────────────────────────────────────
    # Permission checks for camera / system actions
    # ─────────────────────────────────────────
    def can_view_camera(
        self,
        user: Optional[User],
        camera_id: str,
        current_time: int,
        action: str = "live",
    ) -> Tuple[bool, str]:
        """
        Generic permission function that encodes the user stories.

        Args:
            user: current_user() result (User or None)
            camera_id: string ID of the camera (e.g. "backyard")
            current_time: a numeric value comparable to access_start/end
            action: "live", "playback", "settings", "user_mgmt"

        Returns:
            (allowed: bool, message: str)
        """

        if user is None or not user.active:
            return False, "You must be logged in."

        role = user.role

        # System Administrator:
        # Not explicitly described for camera, but we usually allow full access.
        if role == ROLE_ADMIN:
            return True, "Administrator access granted."

        # Homeowner:
        # - Can view all cameras configured on their account.
        # - Access restricted to authenticated homeowners.
        if role == ROLE_HOMEOWNER:
            if action in ("live", "playback"):
                cameras = user.cameras or []
                if camera_id in cameras:
                    return True, "Homeowner access granted."
                return False, "Camera not part of this homeowner's account."

            if action in ("settings", "user_mgmt"):
                # Homeowner can manage own system settings but not other users'
                if action == "user_mgmt":
                    return False, "User management is restricted to administrators."
                return True, "Homeowner can change camera settings."

        # Family Member:
        # - Only view explicitly shared cameras.
        # - No settings, no delete, no sharing access.
        if role == ROLE_FAMILY:
            allowed_cameras = user.allowed_cameras or []
            if camera_id not in allowed_cameras:
                return False, "This camera has not been shared with your account."

            if action == "live":
                return True, "Family member can view this live feed."
            elif action in ("playback", "settings", "user_mgmt"):
                return False, (
                    "Family members cannot view playback, change settings, "
                    "or manage users."
                )

        # Guest User:
        # - Time-bounded access to specific cameras.
        # - No playback, no system settings, no user management.
        if role == ROLE_GUEST:
            allowed_cameras = user.allowed_cameras or []
            start = user.access_start
            end = user.access_end

            if camera_id not in allowed_cameras:
                return False, "This guest invite does not include that camera."

            if start is not None and current_time < start:
                return False, "Guest access has not started yet."
            if end is not None and current_time > end:
                return False, "Guest access has expired."

            if action == "live":
                return True, "Guest can view this camera during the invite window."

            if action in ("playback", "settings", "user_mgmt"):
                return False, (
                    "Guests cannot access video playback, system settings, "
                    "or user management."
                )

        # Fallback: deny if role is unknown
        return False, "Access denied for this user role."
