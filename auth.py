# Probably will be using flask, for now no imports.

# hardcoded user as placeholder

# auth.py

# ─────────────────────────────────────────
# Role constants
# ─────────────────────────────────────────
ROLE_ADMIN = "admin"           # System Administrator
ROLE_HOMEOWNER = "homeowner"   # Homeowner
ROLE_FAMILY = "family"         # Family Member
ROLE_GUEST = "guest"           # Guest User

USERS = {
    "homeowner@gmail.com": {
        "password": "password123",
        "role": ROLE_HOMEOWNER,
        "active": True,
        "cameras": ["front_door", "backyard", "basement"],
    },
     "admin@system.local": {
        "password": "admin123",
        "role": ROLE_ADMIN,
        "active": True,
    },
}
# Time-bounded guest / shared camera constraints are stored
# directly on the user object for simplicity.
#
# For ROLE_GUEST:
#   {
#       "role": "guest",
#       "active": True,
#       "allowed_cameras": ["backyard"],
#       "access_start": 1732400000,   # numeric timestamp / app-defined
#       "access_end": 1732403600,
#   }
#
# For ROLE_FAMILY:
#   {
#       "role": "family",
#       "active": True,
#       "allowed_cameras": ["front_door"],
#   }

# ─────────────────────────────────────────
# Logged-in user tracking (placeholder for Flask session)
# ─────────────────────────────────────────
_CURRENT_USER_EMAIL = None


def login_user(email):
    # Mark the user as logged in
    # Implement: logging a user and saving their email.
    global _CURRENT_USER_EMAIL

    user = USERS.get(email)
    if not user:
        _CURRENT_USER_EMAIL = None
        return False
    
    if not user.get("active", True):
        _CURRENT_USER_EMAIL = None
        return False
    
    _CURRENT_USER_EMAIL = email
    return False

def logout_user():
    """
    Clear the currently logged-in user.
    """
    global _CURRENT_USER_EMAIL
    _CURRENT_USER_EMAIL = None

def current_user():
    # Check if there is a user logged in.
    # Return None if not found and user dict. if found.
    if _CURRENT_USER_EMAIL is None:
        return None

    user = USERS.get(_CURRENT_USER_EMAIL)
    if not user or not user.get("active", True):
        return None

    return user

def current_user():
    """
    Return the currently logged-in user dict, or None
    if nobody is logged in or user is not found.
    """
    if _CURRENT_USER_EMAIL is None:
        return None

    user = USERS.get(_CURRENT_USER_EMAIL)
    if not user or not user.get("active", True):
        return None

    return user

def login_req():
    """
    Ensure only logged-in users have camera access.

    Returns:
        (user_dict) on success.
    Raises:
        PermissionError if not logged in or deactivated.
    """
    user = current_user()
    if user is None:
        raise PermissionError("Authentication required.")
    return user


# ─────────────────────────────────────────
# Role helpers
# ─────────────────────────────────────────
def has_role(user, role):
    return user is not None and user.get("role") == role


def is_admin(user):
    return has_role(user, ROLE_ADMIN)


def is_homeowner(user):
    return has_role(user, ROLE_HOMEOWNER)


def is_family(user):
    return has_role(user, ROLE_FAMILY)


def is_guest(user):
    return has_role(user, ROLE_GUEST)

# ─────────────────────────────────────────
# Admin capabilities (System Administrator)
# ─────────────────────────────────────────
def admin_create_user(email, password, role):
    """
    Admin can create users and assign them a role.
    Requires current_user() to be an admin.
    """
    admin = current_user()
    if not is_admin(admin):
        raise PermissionError("Only administrators can create users.")

    if email in USERS:
        raise ValueError("User already exists.")

    USERS[email] = {
        "password": password,
        "role": role,
        "active": True,
    }
    return USERS[email]


def admin_deactivate_user(email):
    """
    Admin can deactivate a user.
    """
    admin = current_user()
    if not is_admin(admin):
        raise PermissionError("Only administrators can deactivate users.")

    user = USERS.get(email)
    if not user:
        raise ValueError("User not found.")

    user["active"] = False
    return user


def admin_delete_user(email):
    """
    Admin can delete a user.
    """
    admin = current_user()
    if not is_admin(admin):
        raise PermissionError("Only administrators can delete users.")

    if email not in USERS:
        raise ValueError("User not found.")

    del USERS[email]

# ─────────────────────────────────────────
# Homeowner capabilities (Guest / Family management)
# ─────────────────────────────────────────
def homeowner_create_guest(
    guest_email,
    password,
    allowed_cameras,
    access_start,
    access_end,
):
    """
    Homeowner creates a time-bounded guest with access
    to specific cameras.

    access_start / access_end are opaque numeric values
    comparison is done as simple numbers.
    """
    owner = current_user()
    if not is_homeowner(owner):
        raise PermissionError("Only homeowners can create guest users.")

    if guest_email in USERS:
        raise ValueError("Guest email already exists as a user.")

    USERS[guest_email] = {
        "password": password,
        "role": ROLE_GUEST,
        "active": True,
        "allowed_cameras": list(allowed_cameras),
        "access_start": access_start,
        "access_end": access_end,
    }
    return USERS[guest_email]


def homeowner_share_camera_with_family(
    family_email,
    password,
    allowed_cameras,
):
    """
    Homeowner creates or updates a family member account
    with access to specific cameras.
    """
    owner = current_user()
    if not is_homeowner(owner):
        raise PermissionError("Only homeowners can manage family access.")

    if family_email in USERS:
        user = USERS[family_email]
        user["role"] = ROLE_FAMILY
        user["allowed_cameras"] = list(allowed_cameras)
    else:
        USERS[family_email] = {
            "password": password,
            "role": ROLE_FAMILY,
            "active": True,
            "allowed_cameras": list(allowed_cameras),
        }

    return USERS[family_email]

# ─────────────────────────────────────────
# Permission checks for camera / system actions
# ─────────────────────────────────────────
def can_view_camera(user, camera_id, current_time, action="live"):
    """
    Generic permission function that encodes the user stories.

    Args:
        user: current_user() result
        camera_id: string ID of the camera (e.g. "backyard")
        current_time: a numeric value comparable to access_start/end
        action: "live", "playback", "settings", "user_mgmt"

    Returns:
        (allowed: bool, message: str)
    """

    if user is None or not user.get("active", True):
        return False, "You must be logged in."

    role = user.get("role")

    # System Administrator:
    # Not explicitly described for camera, but we usually allow full access.
    if role == ROLE_ADMIN:
        return True, "Administrator access granted."

    # Homeowner:
    # - Can view all cameras configured on their account.
    # - Access restricted to authenticated homeowners.
    if role == ROLE_HOMEOWNER:
        if action in ("live", "playback"):
            # If you want stronger enforcement, check camera_id
            # is in homeowner's camera list:
            cameras = user.get("cameras", [])
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
        allowed_cameras = user.get("allowed_cameras", [])
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
        allowed_cameras = user.get("allowed_cameras", [])
        start = user.get("access_start")
        end = user.get("access_end")

        if camera_id not in allowed_cameras:
            return False, "This guest invite does not include that camera."

        if start is not None and current_time < start:
            return False, "Guest access has not started yet."
        if end is not None and current_time > end:
            return False, "Guest access has expired."

        if action == "live":
            return True, "Guest can view this camera during the invite window."

        # Block everything else clearly
        if action in ("playback", "settings", "user_mgmt"):
            return False, (
                "Guests cannot access video playback, system settings, "
                "or user management."
            )

    # Fallback: deny if role is unknown
    return False, "Access denied for this user role."