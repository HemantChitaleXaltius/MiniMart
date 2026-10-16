"""MiniMart Day 1 starter.

This application is deliberately flawed for a code-review exercise.
Do not use it as a production example.
"""

## a comment by Hemant

import sqlite3

import logging

import math

import config

from flask import Flask, redirect, render_template, request, session, url_for

from werkzeug.security import check_password_hash

from functools import wraps

import os
from dotenv import load_dotenv

app = Flask(__name__)

app.secret_key = config.SECRET_KEY
DATABASE = config.DATABASE_PATH

logging.basicConfig(
    filename=os.environ.get("LOG_FILE", "minimart.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("minimart")


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return render_template("forbidden.html"), 403
        return view(*args, **kwargs)

    return wrapped

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped

def init_db():
    try:
        connection = get_db()
        connection.execute(
            "CREATE TABLE IF NOT EXISTS products ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT NOT NULL, description TEXT NOT NULL, price REAL NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username TEXT NOT NULL UNIQUE, "
            "password_hash TEXT NOT NULL, "
            "role TEXT NOT NULL)"
        )
        if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
                [
                    ("Notebook", "A5 ruled notebook", 4.50),
                    ("Water Bottle", "Reusable 750 ml bottle", 12.00),
                    ("Wireless Mouse", "Compact USB mouse", 18.90),
                    ("Desk Lamp", "LED study lamp", 24.50),
                ],
            )
        connection.commit()
        connection.close()
    except Exception:
        logger.exception("Database setup failed")
        raise


@app.route("/")
def home():
    connection = get_db()
    products = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
    connection.close()
    return render_template("home.html", products=products)

@app.route("/search")
def search():
    term = request.args.get("q", "")
    products = []
    try:
        connection = get_db()
        query = "SELECT * FROM products WHERE name LIKE ?"
        products = connection.execute(query, (f"%{term}%",)).fetchall()
        connection.close()
    except Exception:
        logger.exception("Search failed for term %r", term)
        return render_template("search.html", term=term, products=[], error=True), 500
    return render_template("search.html", term=term, products=products, error=False)


@app.route("/login", methods=["GET", "POST"])
def login():
    failed = False
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        connection = get_db()
        query = "SELECT username, password_hash, role FROM users WHERE username = ?"
        user = connection.execute(query, (username,)).fetchone()
        connection.close()
        if user and check_password_hash(user["password_hash"], password):
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        failed = True
    return render_template("login.html", failed=failed)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    cart_items = session.get("cart", [])
    cart_items.append(product_id)
    session["cart"] = cart_items
    return redirect(request.referrer or url_for("home"))


@app.route("/cart")
def cart():
    ids = session.get("cart", [])
    products = []
    if ids:
        connection = get_db()
        placeholders = ",".join("?" for _ in ids)
        products = connection.execute(
            f"SELECT * FROM products WHERE id IN ({placeholders})", ids
        ).fetchall()
        connection.close()
    total = sum(product["price"] for product in products)
    return render_template("cart.html", products=products, total=total)


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    count = len(session.get("cart", []))
    if request.method == "POST":
        session["cart"] = []
        return render_template("order_placed.html", count=count)
    return render_template("checkout.html", count=count)

@app.route("/admin")
@admin_required
def admin():
    connection = get_db()
    products = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
    connection.close()
    return render_template("admin.html", products=products)


@app.route("/admin/add", methods=["GET", "POST"])
@admin_required
def admin_add():
    errors = []
    form = {"name": "", "description": "", "price": ""}
    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["description"] = request.form.get("description", "").strip()
        form["price"] = request.form.get("price", "").strip()

        if not form["name"]:
            errors.append("Name is required.")
        elif len(form["name"]) > 100:
            errors.append("Name must be 100 characters or fewer.")
        if len(form["description"]) > 500:
            errors.append("Description must be 500 characters or fewer.")

        price = None
        try:
            price = float(form["price"])
        except ValueError:
            errors.append("Price must be a number, for example 4.50.")
        else:
            if not math.isfinite(price) or price <= 0 or price > 100000:
                errors.append("Price must be more than 0 and no more than 100000.")

        if not errors:
            connection = get_db()
            connection.execute(
                "INSERT INTO products (name, description, price) VALUES (?, ?, ?)",
                (form["name"], form["description"], round(price, 2)),
            )
            connection.commit()
            connection.close()
            return redirect(url_for("admin"))
        return render_template("admin_add.html", errors=errors, form=form), 400
    return render_template("admin_add.html", errors=errors, form=form)


if __name__ == "__main__":
    init_db()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
