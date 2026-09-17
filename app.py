import os
from flask import Flask

from config import Config
from extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.instance_path), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.shop import shop_bp
    from blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        from flask_login import current_user as cu
        from flask import session
        from models import AdminInvite

        cart_count = sum(session.get("cart", {}).values()) if session.get("cart") else 0

        has_pending_invite = False
        if cu.is_authenticated and not cu.is_admin:
            has_pending_invite = (
                AdminInvite.query.filter_by(email=cu.email, status="pending").first() is not None
            )

        return {"cart_count": cart_count, "has_pending_invite": has_pending_invite}

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("error.html", code=403, message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("error.html", code=404, message="That page doesn't exist."), 404

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
