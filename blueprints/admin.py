import os
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models import (
    Product, ProductImage, CATEGORY_CHOICES, User, AdminInvite,
    Order, ReturnRequest, OrderItem, ContactMessage,
    ROLE_ADMIN, ROLE_OWNER,
)
from utils import admin_required, owner_required, allowed_file, save_product_image

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    stats = {
        "product_count": Product.query.filter_by(is_active=True).count(),
        "order_count": Order.query.count(),
        "pending_returns": ReturnRequest.query.filter_by(status="requested").count(),
        "unread_messages": ContactMessage.query.filter_by(is_read=False).count(),
    }
    my_products = Product.query.filter_by(added_by_id=current_user.id).order_by(Product.created_at.desc()).limit(6).all()
    return render_template("admin/dashboard.html", stats=stats, my_products=my_products)


# ---------- Products ----------

@admin_bp.route("/products")
@login_required
@admin_required
def products():
    if current_user.is_owner:
        items = Product.query.order_by(Product.created_at.desc()).all()
    else:
        items = Product.query.filter_by(added_by_id=current_user.id).order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=items)


@admin_bp.route("/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        brand = request.form.get("brand", "").strip()
        price = request.form.get("price", "").strip()
        stock = request.form.get("stock", "0").strip()
        files = [f for f in request.files.getlist("images") if f and f.filename]

        error = None
        if not name or not category or not price:
            error = "Name, category and price are required."
        elif not files:
            error = "Please upload at least one product image."
        else:
            for f in files:
                if not allowed_file(f.filename):
                    error = f"'{f.filename}' isn't a supported image type."
                    break

        if error:
            flash(error, "error")
            return render_template("admin/add_product.html", categories=CATEGORY_CHOICES, form=request.form)

        product = Product(
            name=name,
            description=description,
            category=category,
            brand=brand,
            price=price,
            stock=int(stock or 0),
            added_by_id=current_user.id,
        )
        db.session.add(product)
        db.session.flush()  # get product.id for the upload folder

        for f in files:
            filename = save_product_image(f, product.id)
            db.session.add(ProductImage(product_id=product.id, filename=filename))

        db.session.commit()
        flash(f"'{product.name}' has been added to the store.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/add_product.html", categories=CATEGORY_CHOICES, form={})


def _product_editable_or_403(product):
    if not (current_user.is_owner or product.added_by_id == current_user.id):
        abort(403)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    _product_editable_or_403(product)

    if request.method == "POST":
        product.name = request.form.get("name", product.name).strip()
        product.description = request.form.get("description", product.description).strip()
        product.category = request.form.get("category", product.category).strip()
        product.brand = request.form.get("brand", product.brand).strip()
        product.price = request.form.get("price", product.price)
        product.stock = int(request.form.get("stock", product.stock) or 0)
        product.is_active = bool(request.form.get("is_active"))

        new_files = [f for f in request.files.getlist("images") if f and f.filename]
        for f in new_files:
            if allowed_file(f.filename):
                filename = save_product_image(f, product.id)
                db.session.add(ProductImage(product_id=product.id, filename=filename))

        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/edit_product.html", product=product, categories=CATEGORY_CHOICES)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_product(product_id):
    import shutil
    from flask import current_app

    product = Product.query.get_or_404(product_id)
    _product_editable_or_403(product)

    # Remove uploaded image files from disk for this product.
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(product.id))
    if os.path.isdir(folder):
        shutil.rmtree(folder, ignore_errors=True)

    db.session.delete(product)  # cascades to ProductImage rows
    db.session.commit()
    flash(f"'{product.name}' has been permanently deleted.", "info")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/image/<int:image_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_image(image_id):
    image = ProductImage.query.get_or_404(image_id)
    _product_editable_or_403(image.product)
    product_id = image.product_id
    db.session.delete(image)
    db.session.commit()
    flash("Image removed.", "info")
    return redirect(url_for("admin.edit_product", product_id=product_id))


# ---------- Admin management (owner only) ----------

@admin_bp.route("/team", methods=["GET", "POST"])
@login_required
@owner_required
def manage_admins():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        note = request.form.get("note", "").strip()

        if not email:
            flash("Please enter an email address to invite.", "error")
        elif AdminInvite.query.filter_by(email=email, status="pending").first():
            flash("There's already a pending invite for that email.", "info")
        else:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.role in (ROLE_ADMIN, ROLE_OWNER):
                flash(f"{email} is already an admin.", "info")
            else:
                db.session.add(AdminInvite(email=email, invited_by_id=current_user.id, note=note))
                db.session.commit()
                if existing_user:
                    flash(f"Invite sent — {email} can accept it next time they log in.", "success")
                else:
                    flash(f"Invite created for {email}. They'll be able to accept it once they register.", "success")

        return redirect(url_for("admin.manage_admins"))

    admins = User.query.filter(User.role.in_([ROLE_ADMIN, ROLE_OWNER])).order_by(User.created_at.asc()).all()
    invites = AdminInvite.query.order_by(AdminInvite.created_at.desc()).all()
    return render_template("admin/manage_admins.html", admins=admins, invites=invites)


@admin_bp.route("/team/invite/<int:invite_id>/revoke", methods=["POST"])
@login_required
@owner_required
def revoke_invite(invite_id):
    invite = AdminInvite.query.get_or_404(invite_id)
    if invite.status == "pending":
        invite.status = "revoked"
        invite.responded_at = datetime.utcnow()
        db.session.commit()
        flash("Invite revoked.", "info")
    return redirect(url_for("admin.manage_admins"))


@admin_bp.route("/team/<int:user_id>/remove", methods=["POST"])
@login_required
@owner_required
def remove_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == ROLE_OWNER:
        flash("The store owner can't be removed.", "error")
    else:
        user.role = "customer"
        db.session.commit()
        flash(f"{user.name} is no longer an admin.", "info")
    return redirect(url_for("admin.manage_admins"))


# ---------- Orders & returns ----------

@admin_bp.route("/orders")
@login_required
@admin_required
def orders():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=all_orders)


@admin_bp.route("/orders/<int:order_id>/mark-delivered", methods=["POST"])
@login_required
@admin_required
def mark_delivered(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "delivered"
    order.delivered_at = datetime.utcnow()
    db.session.commit()
    flash("Order marked as delivered. The 3-day return window now starts.", "success")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/returns")
@login_required
@admin_required
def returns():
    requests_ = ReturnRequest.query.order_by(ReturnRequest.created_at.desc()).all()
    return render_template("admin/returns.html", requests=requests_)


@admin_bp.route("/returns/<int:request_id>/<string:decision>", methods=["POST"])
@login_required
@admin_required
def decide_return(request_id, decision):
    if decision not in ("approved", "rejected"):
        abort(400)
    req = ReturnRequest.query.get_or_404(request_id)
    req.status = decision
    db.session.commit()
    flash(f"Return {decision}.", "success")
    return redirect(url_for("admin.returns"))


# ---------- Contact inbox ----------

@admin_bp.route("/messages")
@login_required
@admin_required
def messages():
    all_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=all_messages)


@admin_bp.route("/messages/<int:message_id>/read", methods=["POST"])
@login_required
@admin_required
def mark_message_read(message_id):
    msg = ContactMessage.query.get_or_404(message_id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for("admin.messages"))
