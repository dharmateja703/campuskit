from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, AdminInvite, ROLE_OWNER, ROLE_ADMIN, ROLE_CUSTOMER

auth_bp = Blueprint("auth", __name__)


def _pending_invite_for(email):
    return AdminInvite.query.filter_by(email=email.lower().strip(), status="pending").first()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        college = request.form.get("college", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not name or not email or not password:
            error = "Name, email and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."

        if error:
            flash(error, "error")
            return render_template("register.html", name=name, email=email, college=college)

        is_first_user = User.query.count() == 0
        user = User(name=name, email=email, college=college)
        user.set_password(password)
        user.role = ROLE_OWNER if is_first_user else ROLE_CUSTOMER
        db.session.add(user)
        db.session.commit()

        # If someone (the owner) already invited this email as an admin,
        # surface it so they can accept it right after registering.
        invite = _pending_invite_for(email)

        login_user(user)
        if is_first_user:
            flash("Welcome! Since you're the first account, you're the store Owner.", "success")
        elif invite:
            flash("Account created. You have a pending admin invitation below.", "success")
        else:
            flash("Account created. Welcome to CampusKit!", "success")
        return redirect(url_for("auth.accept_invite") if invite else url_for("main.home"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name.split()[0]}.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.home"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/admin-invite", methods=["GET", "POST"])
@login_required
def accept_invite():
    """A logged-in user can view and accept a pending admin invite matching their email."""
    invite = _pending_invite_for(current_user.email)

    if request.method == "POST" and invite:
        action = request.form.get("action")
        if action == "accept":
            current_user.role = ROLE_ADMIN
            invite.status = "accepted"
            invite.responded_at = datetime.utcnow()
            db.session.commit()
            flash("You're now an admin. You can add products from the admin panel.", "success")
            return redirect(url_for("admin.dashboard"))
        elif action == "decline":
            invite.status = "revoked"
            invite.responded_at = datetime.utcnow()
            db.session.commit()
            flash("Invitation declined.", "info")
            return redirect(url_for("main.home"))

    return render_template("accept_invite.html", invite=invite)
