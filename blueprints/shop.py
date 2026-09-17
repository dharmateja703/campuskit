from decimal import Decimal

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from extensions import db
from models import Product, Order, OrderItem, ReturnRequest

shop_bp = Blueprint("shop", __name__)


def _get_cart():
    return session.setdefault("cart", {})


@shop_bp.route("/cart")
def view_cart():
    cart = _get_cart()
    items = []
    total = Decimal("0")
    for product_id, qty in cart.items():
        product = Product.query.get(int(product_id))
        if not product:
            continue
        line_total = product.price * qty
        total += line_total
        items.append({"product": product, "quantity": qty, "line_total": line_total})
    return render_template("cart.html", items=items, total=total)


@shop_bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty = max(1, int(request.form.get("quantity", 1)))

    cart = _get_cart()
    key = str(product_id)
    cart[key] = min(product.stock, cart.get(key, 0) + qty) if product.stock else 0
    session.modified = True

    flash(f"Added {product.name} to your cart.", "success")
    return redirect(request.referrer or url_for("main.home"))


@shop_bp.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    cart = _get_cart()
    qty = int(request.form.get("quantity", 0))
    key = str(product_id)
    if qty <= 0:
        cart.pop(key, None)
    else:
        product = Product.query.get_or_404(product_id)
        cart[key] = min(qty, product.stock)
    session.modified = True
    return redirect(url_for("shop.view_cart"))


@shop_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = _get_cart()
    cart.pop(str(product_id), None)
    session.modified = True
    return redirect(url_for("shop.view_cart"))


@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = _get_cart()
    if not cart:
        flash("Your cart is empty.", "info")
        return redirect(url_for("main.home"))

    items = []
    total = Decimal("0")
    for product_id, qty in cart.items():
        product = Product.query.get(int(product_id))
        if not product or qty < 1:
            continue
        items.append((product, qty))
        total += product.price * qty

    if request.method == "POST":
        address = request.form.get("address", "").strip()
        if not address:
            flash("Please enter a delivery address.", "error")
            return render_template("checkout.html", items=items, total=total)

        order = Order(customer_id=current_user.id, shipping_address=address, total_amount=total)
        db.session.add(order)
        db.session.flush()  # get order.id

        for product, qty in items:
            if product.stock < qty:
                flash(f"Not enough stock for {product.name}. Please update your cart.", "error")
                db.session.rollback()
                return redirect(url_for("shop.view_cart"))
            product.stock -= qty
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                unit_price=product.price,
                quantity=qty,
            ))

        db.session.commit()
        session["cart"] = {}
        flash("Order placed! You can request a return within 3 days if needed.", "success")
        return redirect(url_for("shop.order_detail", order_id=order.id))

    return render_template("checkout.html", items=items, total=total)


@shop_bp.route("/orders")
@login_required
def order_history():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders.html", orders=orders)


@shop_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id and not current_user.is_admin:
        from flask import abort
        abort(403)
    return render_template("order_detail.html", order=order)


@shop_bp.route("/orders/item/<int:item_id>/return", methods=["POST"])
@login_required
def request_return(item_id):
    item = OrderItem.query.get_or_404(item_id)
    order = item.order
    if order.customer_id != current_user.id:
        from flask import abort
        abort(403)

    if not order.can_be_returned():
        flash("Sorry, the 3-day return window for this order has passed.", "error")
        return redirect(url_for("shop.order_detail", order_id=order.id))

    if item.return_request:
        flash("A return has already been requested for this item.", "info")
        return redirect(url_for("shop.order_detail", order_id=order.id))

    reason = request.form.get("reason", "").strip() or "Not specified"
    db.session.add(ReturnRequest(order_item_id=item.id, reason=reason))
    db.session.commit()
    flash("Return requested. Our team will contact you shortly.", "success")
    return redirect(url_for("shop.order_detail", order_id=order.id))
