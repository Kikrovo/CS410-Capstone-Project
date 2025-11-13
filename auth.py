# Probably will be using flask, for now no imports.

# hardcoded user as placeholder

USERS = {
    "homeowner@gmail.com": {
        "password": "password123",
        "role": "homeowner"
    }
}

def login_user(email):
    # Mark the user as logged in
    # Implement: logging a user and saving their email.


def current_user():
    # Check if there is a user logged in.
    # Return None if not found and user dict. if found.


def login_req():
    # Ensure only logged in user has camera access.