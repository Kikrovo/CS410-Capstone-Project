from flask import Flask, render_template, request, redirect, url_for, session, abort
from functools import wraps
import time

from auth import AuthManager

app = Flask(__name__)
app.secret_key = "change-this-for-demo"  # encryption layer

auth_manager = AuthManager()



CAMERA_ENDPOINTS = {
    "main_cam": "http://192.168.4.1/sustain?stream=0",

}


def get_current_user():
    email = session.get("user_email")
    if not email:
        return None
    return auth_manager._users.get(email)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def camera_access_required(action="live"):
    def decorator(f):
        @wraps(f)
        def wrapper(camera_id, *args, **kwargs):
            user = get_current_user()
            now = int(time.time())
            ok, msg = auth_manager.can_view_camera(user, camera_id, now, action=action)
            if not ok:
                return f"Access denied: {msg}", 403
            return f(camera_id, *args, **kwargs)
        return wrapper
    return decorator


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]
        ok = auth_manager.login_user(email, password)
        if not ok:
            error = "Invalid email or password"
        else:
            session["user_email"] = email
            # 👇 direct to camera route that we know exists
            return redirect(url_for("index"))
    return render_template("login.html", error=error, user=None)


@app.route("/")
@login_required
def index():
    user = get_current_user()
    camera_url = CAMERA_ENDPOINTS["main_cam"]
    return render_template("index.html", user=user, camera_url=camera_url)


@app.route("/camera/<camera_id>")
@login_required
@camera_access_required(action="live")
def camera_view(camera_id):
    user = get_current_user()
    base_url = CAMERA_ENDPOINTS.get(camera_id)
    if not base_url:
        return "Unknown camera", 404

    return render_template(
        "camera.html",
        user=user,
        camera_id=camera_id,
        camera_url=base_url,
    )


@app.route("/logout")
def logout():
    session.pop("user_email", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    # For development & demo
    app.run(host="0.0.0.0", port=5000, debug=True)
