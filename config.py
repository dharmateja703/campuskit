import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'campuskit.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "products")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB total upload cap

    # Business rules
    RETURN_WINDOW_DAYS = 3

    # The very first account ever registered on the site automatically
    # becomes the Owner (super admin). Everyone else starts as a customer.
    OWNER_EMAIL = os.environ.get("OWNER_EMAIL")  # optional: force a specific email to be owner
