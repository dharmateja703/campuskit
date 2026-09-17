# CampusKit — Campus Gadget Store (Flask)

A multi-admin e-commerce site for selling scientific calculators, drafters,
instrument boxes and electronic gadgets to students. Built with Flask,
SQLAlchemy and Flask-Login.

## Features

- **Storefront**: search + category filter, product pages with multiple
  images, cart, checkout, order history.
- **Multi-admin model**:
  - The **first person to register becomes the Owner** (super admin).
  - The Owner can invite other people (e.g. a contact at another college) to
    become **Admins** from *Admin Panel → Admin team*. An invite only takes
    effect once the invited person logs in and explicitly accepts it — no one
    can grant themselves admin access.
  - Admins can add/edit their own products (name, description, price, stock,
    category, one or more images). The Owner can see and manage every
    product; other admins only see their own.
- **Returns**: once an order is marked "delivered", the customer has a
  **3-day window** to request a return on any item. Admins approve/reject
  requests from *Admin Panel → Returns*.
- **Contact page**: a form that saves messages into an admin inbox
  (*Admin Panel → Messages*), plus store contact details.

## Getting started

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The app runs at `http://127.0.0.1:5000`. A SQLite database is created
automatically at `instance/campuskit.db` on first run — no separate database
setup needed. Uploaded product photos are saved under
`static/uploads/products/`.

### First-time setup

1. Go to **Sign up** and create the first account — it automatically becomes
   the store **Owner**.
2. Log in, open **Admin Panel → Products → Add product**, and start listing
   items (name, category, price, stock, description, and one or more
   images).
3. To let someone at another college add their own products, go to
   **Admin Panel → Admin team**, enter their email and send an invite. Once
   they register (or log in, if they already have an account) with that
   email, they'll see a banner to accept the invite — after accepting, they
   become an Admin and can add their own products.

## Project structure

```
app.py                 Flask app factory, error pages, template globals
config.py               Configuration (DB path, upload folder, return window)
extensions.py           Shared SQLAlchemy / Flask-Login instances
models.py               User, Product, ProductImage, Order, OrderItem,
                         ReturnRequest, AdminInvite, ContactMessage
utils.py                Role decorators, image upload helper
blueprints/
  auth.py               Register, login, logout, invite acceptance
  main.py                Home/search, product detail, contact, returns policy
  shop.py                 Cart, checkout, order history, return requests
  admin.py                Admin panel: products, admins, orders, returns, inbox
templates/               Jinja2 templates (storefront + admin/ subfolder)
static/css/style.css     Stylesheet
static/uploads/products/ Uploaded product images (created automatically)
```

## Notes for production use

This is a solid functional base, but before going live you should:

- Set a strong, secret `SECRET_KEY` via an environment variable (don't use
  the default in `config.py`).
- Switch the database from SQLite to Postgres/MySQL for concurrent traffic
  (`DATABASE_URL` env var is already read in `config.py`).
- Add real payment handling — checkout currently records orders for
  pay-on-pickup/delivery only.
- Put the app behind HTTPS and a production WSGI server (e.g. gunicorn +
  nginx) instead of `python app.py`.
- Consider email notifications for order confirmations, admin invites and
  return decisions (currently everything is shown in-app only).

## Environment variables (all optional)

| Variable       | Purpose                                   | Default                        |
|----------------|--------------------------------------------|---------------------------------|
| `SECRET_KEY`   | Flask session signing key                  | insecure dev value — change it |
| `DATABASE_URL` | SQLAlchemy database URL                    | local SQLite file              |
