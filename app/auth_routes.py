from __future__ import annotations
from urllib.parse import urljoin, urlparse
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from pymysql import IntegrityError
from .auth import assign_role, create_user, load_user_by_email, load_user_by_username, verify_password

auth_bp = Blueprint("auth", __name__)

def _is_safe_url(target: str) -> bool:
    if not target:
        return False

    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        user_row = load_user_by_username(username)
        if not user_row or not verify_password(user_row.get("password_hash", ""), password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        if user_row.get("is_deleted"):
            flash("This account is deactivated.", "danger")
            return render_template("login.html")

        if user_row.get("is_banned"):
            flash("This account is banned.", "danger")
            return render_template("login.html")

        from .auth import User

        user = User(
            user_id=user_row["user_id"],
            username=user_row["username"],
            email=user_row["email"],
            display_name=user_row.get("display_name"),
            is_banned=bool(user_row.get("is_banned")),
            is_deleted=bool(user_row.get("is_deleted")),
        )

        login_user(user)
        next_url = request.args.get("next")
        if next_url and _is_safe_url(next_url):
            return redirect(next_url)

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        display_name = (request.form.get("display_name") or "").strip() or None

        if not username or not email or not password:
            flash("Username, email, and password are required.", "danger")
            return render_template("register.html")

        if len(password) < 10:
            flash("Password must be at least 10 characters.", "danger")
            return render_template("register.html")

        if load_user_by_username(username):
            flash("Username is already taken.", "danger")
            return render_template("register.html")

        if load_user_by_email(email):
            flash("Email is already registered.", "danger")
            return render_template("register.html")

        try:
            user = create_user(username=username, email=email, password=password, display_name=display_name)
            assign_role(user.user_id, "user")
        except IntegrityError:
            flash("Registration failed. Please try again.", "danger")
            return render_template("register.html")

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("dashboard"))
