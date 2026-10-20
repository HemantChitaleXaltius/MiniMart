"""Tests for the checkout flow, and for carts in situations the other test files skip."""

import sqlite3

import pytest

# Test-only login details. They match the shopper user that tests/conftest.py creates.
SHOPPER_LOGIN = {"username": "shopper", "password": "shopper-test-password"}

# Starter products (ids 1 to 4): 1 Notebook $4.50, 2 Water Bottle $12.00,
# 3 Wireless Mouse $18.90, 4 Desk Lamp $24.50.


def remove_product(app, product_id):
    """Delete a product from the shop's database, as if the owner had retired it."""
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
    connection.commit()
    connection.close()


# ------------------------------------------------------------- checkout page


# If this fails: the checkout page tells the shopper the wrong number of items they are about to buy.
def test_checkout_page_counts_the_items_in_the_cart(shopper_client):
    shopper_client.post("/cart/add/1")
    shopper_client.post("/cart/add/3")

    response = shopper_client.get("/checkout")

    assert b"You are about to order 2 item(s)." in response.data


# If this fails: someone who adds two of the same product is told they are ordering only one.
def test_checkout_page_counts_a_product_added_twice_as_two_items(shopper_client):
    shopper_client.post("/cart/add/1")
    shopper_client.post("/cart/add/1")

    response = shopper_client.get("/checkout")

    assert b"You are about to order 2 item(s)." in response.data


# If this fails: there is no working "Place order" button, so nobody can finish buying.
def test_checkout_page_has_a_place_order_button_that_submits_a_form(shopper_client):
    response = shopper_client.get("/checkout")

    assert b"Place order" in response.data
    assert b'method="post"' in response.data


# If this fails: merely looking at the checkout page wipes the cart, so shoppers lose their items.
def test_viewing_the_checkout_page_does_not_empty_the_cart(shopper_client):
    shopper_client.post("/cart/add/1")

    shopper_client.get("/checkout")

    assert b"Notebook - $4.50" in shopper_client.get("/cart").data


# If this fails: the cart page has no way to reach checkout.
def test_cart_page_has_a_checkout_button_that_leads_to_checkout(client):
    client.post("/cart/add/1")

    response = client.get("/cart")

    assert b'href="/checkout"' in response.data
    assert b"Checkout" in response.data


# If this fails: a visitor who fills a cart and then logs in finds the cart wiped.
def test_logging_in_keeps_the_items_already_in_the_cart(client):
    client.post("/cart/add/1")

    login = client.post("/login", data=SHOPPER_LOGIN)

    assert login.status_code == 302
    assert b"Notebook - $4.50" in client.get("/cart").data


# ------------------------------------------------------------ placing orders


# If this fails: after buying, the shopper gets no confirmation, or is told the wrong number of items.
def test_placing_an_order_shows_the_thank_you_message_with_the_item_count(shopper_client):
    shopper_client.post("/cart/add/1")
    shopper_client.post("/cart/add/2")

    response = shopper_client.post("/checkout")

    assert b"Thank you. Your order contained 2 item(s)." in response.data


# If this fails: the cart still holds the items after ordering, so they could be ordered again.
def test_placing_an_order_empties_the_cart(shopper_client):
    shopper_client.post("/cart/add/1")
    shopper_client.post("/checkout")

    response = shopper_client.get("/cart")

    assert b"Your cart is empty." in response.data
    assert b"Total: $0.00" in response.data


# If this fails: admins are locked out of checkout, because the rule meant for shoppers blocks them too.
def test_an_admin_can_also_place_an_order(admin_client):
    admin_client.post("/cart/add/1")

    response = admin_client.post("/checkout")

    assert b"Thank you. Your order contained 1 item(s)." in response.data


# If this fails: one person's order empties other visitors' carts.
def test_placing_an_order_does_not_empty_another_visitors_cart(client, shopper_client):
    client.post("/cart/add/1")
    shopper_client.post("/cart/add/2")

    shopper_client.post("/checkout")

    assert b"Notebook - $4.50" in client.get("/cart").data


# If this fails: someone who is not logged in can place an order.
def test_logged_out_visitor_cannot_place_an_order(client):
    client.post("/cart/add/1")

    response = client.post("/checkout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert b"Thank you" not in response.data


# If this fails: customers can "order" an empty cart and get a thank-you message (known gap, so this is marked as expected to fail).
@pytest.mark.xfail(
    strict=True,
    reason="Known gap: checkout accepts an empty cart and says thank you.",
)
def test_placing_an_order_with_an_empty_cart_is_refused(shopper_client):
    response = shopper_client.post("/checkout")

    assert b"Thank you" not in response.data


# --------------------------------------------------------------- cart edges


# If this fails: retiring a product that is in someone's cart crashes their cart page, or still charges for it.
def test_cart_ignores_a_product_that_was_removed_from_the_shop(app, client):
    client.post("/cart/add/1")
    client.post("/cart/add/2")
    remove_product(app, 2)

    response = client.get("/cart")

    assert b"Notebook - $4.50" in response.data
    assert b"Water Bottle" not in response.data
    assert b"Total: $4.50" in response.data
