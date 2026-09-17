import secrets
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

# Roles, in ascending order of privilege
ROLE_CUSTOMER = "customer"
ROLE_ADMIN = "admin"
ROLE_OWNER = "owner"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    college = db.Column(db.String(160))
    role = db.Column(db.String(20), nullable=False, default=ROLE_CUSTOMER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="added_by", lazy="dynamic")
    orders = db.relationship("Order", backref="customer", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role in (ROLE_ADMIN, ROLE_OWNER)

    @property
    def is_owner(self):
        return self.role == ROLE_OWNER

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class AdminInvite(db.Model):
    """
    An invitation the owner sends to let someone administer the store
    (e.g. a contact person at another college). Only the owner can create
    these. The invited person can only gain admin rights by accepting an
    invite that still matches their email and hasn't been revoked.
    """
    __tablename__ = "admin_invites"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(24))
    invited_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, accepted, revoked
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

    invited_by = db.relationship("User", foreign_keys=[invited_by_id])


CATEGORY_CHOICES = [
    "Scientific Calculator",
    "Drafter / Drawing Instruments",
    "Instrument Box (ICS)",
    "Electronic Gadgets",
    "Other",
]


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(80), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    brand = db.Column(db.String(80))
    is_active = db.Column(db.Boolean, default=True)
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship("ProductImage", backref="product", cascade="all, delete-orphan", lazy="joined")

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def primary_image(self):
        return self.images[0].filename if self.images else None


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)


ORDER_STATUS_PLACED = "placed"
ORDER_STATUS_DELIVERED = "delivered"
ORDER_STATUS_CANCELLED = "cancelled"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=ORDER_STATUS_PLACED)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping_address = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan", lazy="joined")

    @property
    def return_deadline(self):
        anchor = self.delivered_at or self.created_at
        return anchor + timedelta(days=3)

    def can_be_returned(self):
        return datetime.utcnow() <= self.return_deadline


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product_name = db.Column(db.String(160), nullable=False)  # snapshot, in case product changes later
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship("Product")
    return_request = db.relationship("ReturnRequest", backref="order_item", uselist=False)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class ReturnRequest(db.Model):
    __tablename__ = "return_requests"

    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_items.id"), nullable=False, unique=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="requested")  # requested, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
