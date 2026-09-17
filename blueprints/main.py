from flask import Blueprint, render_template, request, flash, redirect, url_for

from extensions import db
from models import Product, CATEGORY_CHOICES, ContactMessage

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    products = Product.query.filter_by(is_active=True)
    if query:
        like = f"%{query}%"
        products = products.filter(
            db.or_(Product.name.ilike(like), Product.description.ilike(like), Product.brand.ilike(like))
        )
    if category:
        products = products.filter_by(category=category)

    products = products.order_by(Product.created_at.desc()).all()

    return render_template(
        "index.html",
        products=products,
        categories=CATEGORY_CHOICES,
        query=query,
        active_category=category,
    )


@main_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = (
        Product.query.filter(Product.category == product.category, Product.id != product.id, Product.is_active == True)
        .limit(4)
        .all()
    )
    return render_template("product_detail.html", product=product, related=related)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("Please fill in your name, email and message.", "error")
        else:
            db.session.add(ContactMessage(name=name, email=email, subject=subject or "General enquiry", message=message))
            db.session.commit()
            flash("Message sent. We'll get back to you within 2 working days.", "success")
            return redirect(url_for("main.contact"))

    return render_template("contact.html")


@main_bp.route("/returns-policy")
def returns_policy():
    return render_template("returns_policy.html")
