import os
import uuid
from functools import wraps

from flask import current_app, abort
from flask_login import current_user
from werkzeug.utils import secure_filename

from models import ROLE_ADMIN, ROLE_OWNER


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_product_image(file_storage, product_id):
    """Save one uploaded image for a product and return its stored filename."""
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(product_id))
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, unique_name))

    return f"{product_id}/{unique_name}"


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != ROLE_OWNER:
            abort(403)
        return view(*args, **kwargs)
    return wrapped
