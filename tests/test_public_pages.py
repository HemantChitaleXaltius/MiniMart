"""Tests for the pages anyone can visit: the home page, search and the cart."""

import logging
import sqlite3

import pytest

# The four starter products, in the order init_db() creates them (ids 1 to 4).
STARTER_PRODUCTS = [
    ("Notebook", "$4.50"),
    ("Water Bottle", "$12.00"),
    ("Wireless Mouse", "$18.90"),
    ("Desk Lamp", "$24.50"),
]

SCRIPT_TEXT = "<script>alert(1)</script>"
SCRIPT_TEXT_ESCAPED = "&lt;script&gt;alert(1)&lt;/script&gt;"


def add_product(admin_client, name, description="A test product", price="7.50"):
    """Add a product the way an admin would, and fail loudly if it did not work."""
    response = admin_client.post(
        "/admin/add", data={"name": name, "description": description, "price": price}
    )
    assert response.status_code == 302, "test setup failed: the product was not added"


def break_the_products_table(app):
    """Delete the products table so that any query on it fails."""
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.execute("DROP TABLE products")
    connection.commit()
    connection.close()


# ------------------------------------------------------------------ home page


# If this fails: shoppers see a missing product, or a product with the wrong price.
def test_home_page_shows_every_starter_product_with_its_price(client):
    response = client.get("/")

    for name, price in STARTER_PRODUCTS:
        assert name.encode() in response.data
        assert price.encode() in response.data


# If this fails: an "Add to cart" button puts the wrong product in the cart, or does nothing.
def test_home_page_add_to_cart_buttons_point_at_each_product(client):
    response = client.get("/")

    for product_id in (1, 2, 3, 4):
        assert f'action="/cart/add/{product_id}"'.encode() in response.data


# If this fails: the search box on the home page does not lead to the search page.
def test_home_page_search_box_sends_the_word_to_the_search_page(client):
    response = client.get("/")

    assert b'action="/search"' in response.data
    assert b'name="q"' in response.data


# If this fails: logged-out visitors are shown a Logout link, or no way to log in.
def test_logged_out_visitor_sees_login_link_and_no_logout_link(client):
    response = client.get("/")

    assert b'href="/login"' in response.data
    assert b'href="/logout"' not in response.data


# If this fails: logged-in people cannot see who they are signed in as, or cannot log out.
def test_logged_in_shopper_sees_their_name_role_and_logout_link(shopper_client):
    response = shopper_client.get("/")

    assert b"shopper (shopper)" in response.data
    assert b'href="/logout"' in response.data


# If this fails: products an admin adds never show up in the shop, or show the wrong price.
def test_product_added_by_an_admin_appears_on_the_home_page(client, admin_client):
    add_product(admin_client, "Teapot", price="7.5")

    response = client.get("/")

    assert b"Teapot" in response.data
    assert b"$7.50" in response.data


# If this fails: a product name containing a script runs in every visitor's browser.
def test_product_name_with_a_script_is_shown_as_plain_text_on_the_home_page(
    client, admin_client
):
    add_product(admin_client, SCRIPT_TEXT)

    response = client.get("/")

    assert SCRIPT_TEXT.encode() not in response.data
    assert SCRIPT_TEXT_ESCAPED.encode() in response.data


# If this fails: a product description containing HTML is treated as page code, not text.
def test_product_description_with_html_is_shown_as_plain_text_on_the_home_page(
    client, admin_client
):
    add_product(admin_client, "Safe Name", description="<img src=x onerror=alert(1)>")

    response = client.get("/")

    assert b"<img src=x" not in response.data
    assert b"&lt;img src=x onerror=alert(1)&gt;" in response.data


# --------------------------------------------------------------------- search


# If this fails: searching for part of a name does not find the product, or finds everything.
def test_search_finds_a_product_by_part_of_its_name(client):
    response = client.get("/search", query_string={"q": "note"})

    assert b"Notebook" in response.data
    assert b"Desk Lamp" not in response.data


# If this fails: searching "NOTE" finds nothing, so shoppers must guess the exact capital letters.
def test_search_ignores_upper_and_lower_case(client):
    response = client.get("/search", query_string={"q": "NOTE"})

    assert b"Notebook" in response.data


# If this fails: a search with no results shows an empty page, or shows products that do not match.
def test_search_with_no_match_says_so_and_lists_no_products(client):
    response = client.get("/search", query_string={"q": "zzz"})

    assert b"No products found." in response.data
    assert b"Add to cart" not in response.data


# If this fails: the results page does not tell the shopper what word it searched for.
def test_search_page_repeats_the_word_that_was_searched(client):
    response = client.get("/search", query_string={"q": "lamp"})

    assert b"Search results for <strong>lamp</strong>" in response.data


# If this fails: opening /search with no word crashes instead of listing the shop.
def test_search_with_no_word_at_all_lists_every_product(client):
    response = client.get("/search")

    assert response.data.count(b"Add to cart") == 4


# If this fails: a name with an apostrophe (like O'Brien) breaks the search or the page.
def test_search_word_with_an_apostrophe_does_not_break_the_page(client):
    response = client.get("/search", query_string={"q": "O'Brien"})

    assert response.status_code == 200
    assert b"O&#39;Brien" in response.data
    assert b"No products found." in response.data


# If this fails: when the database breaks, shoppers get a blank or misleading page, not a clear message.
def test_search_failure_returns_500_with_a_friendly_message(app, client):
    break_the_products_table(app)

    response = client.get("/search", query_string={"q": "note"})

    assert response.status_code == 500
    assert b"Sorry, search is not working right now." in response.data


# If this fails: a database error leaks internal details (like table names) to the public.
def test_search_failure_does_not_show_database_error_details(app, client):
    break_the_products_table(app)

    response = client.get("/search", query_string={"q": "note"})

    assert b"Traceback" not in response.data
    assert b"no such table" not in response.data


# If this fails: search breaks silently and nobody can find out why from the log.
def test_search_failure_is_written_to_the_error_log(app, client, caplog):
    break_the_products_table(app)

    with caplog.at_level(logging.ERROR, logger="minimart"):
        client.get("/search", query_string={"q": "note"})

    assert "Search failed for term 'note'" in caplog.text
    assert "no such table" in caplog.text  # the real cause is recorded for developers


# ------------------------------------------------------------------------ cart


# If this fails: an empty cart shows a blank page or a wrong total.
def test_empty_cart_shows_a_message_and_a_zero_total(client):
    response = client.get("/cart")

    assert b"Your cart is empty." in response.data
    assert b"Total: $0.00" in response.data


# If this fails: a product added to the cart is missing, or its price or the total is wrong.
def test_cart_lists_an_added_product_with_its_price_and_total(client):
    client.post("/cart/add/1")

    response = client.get("/cart")

    assert b"Notebook - $4.50" in response.data
    assert b"Total: $4.50" in response.data


# If this fails: the cart total is wrong as soon as there is more than one product.
def test_cart_total_adds_up_two_different_products(client):
    client.post("/cart/add/1")  # Notebook, 4.50
    client.post("/cart/add/3")  # Wireless Mouse, 18.90

    response = client.get("/cart")

    assert b"Wireless Mouse - $18.90" in response.data
    assert b"Total: $23.40" in response.data


# If this fails: after clicking "Add to cart" shoppers lose their place instead of returning to it.
def test_adding_to_cart_returns_to_the_page_the_shopper_came_from(client):
    response = client.post("/cart/add/1", headers={"Referer": "/search?q=note"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/search?q=note"


# If this fails: adding to the cart from a page with no "came from" sends the shopper somewhere broken.
def test_adding_to_cart_with_no_previous_page_goes_to_the_home_page(client):
    response = client.post("/cart/add/1")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


# If this fails: simply visiting a link can fill someone's cart, because adding is not limited to a button press.
def test_adding_to_cart_by_visiting_the_address_is_not_allowed(client):
    response = client.get("/cart/add/1")

    assert response.status_code == 405


# If this fails: a made-up product address like /cart/add/abc is accepted instead of rejected.
def test_adding_to_cart_with_a_non_number_product_id_is_not_found(client):
    response = client.post("/cart/add/abc")

    assert response.status_code == 404


# If this fails: one visitor's cart shows up for another visitor.
def test_each_visitor_has_their_own_cart(client, shopper_client):
    client.post("/cart/add/1")

    assert b"Notebook" in client.get("/cart").data
    assert b"Your cart is empty." in shopper_client.get("/cart").data


# If this fails: a product name containing a script runs in the browser of anyone who opens the cart.
def test_product_name_with_html_is_shown_as_plain_text_in_the_cart(client, admin_client):
    add_product(admin_client, "<b>Bold</b>")  # the first new product gets id 5
    client.post("/cart/add/5")

    response = client.get("/cart")

    assert b"<b>Bold</b>" not in response.data
    assert b"&lt;b&gt;Bold&lt;/b&gt;" in response.data


# If this fails: a customer who adds the same item twice is only charged for one (known bug, so this is marked as expected to fail).
@pytest.mark.xfail(
    strict=True,
    reason="Known bug: the cart lists a product once however many times it was added.",
)
def test_cart_total_counts_a_product_added_twice_two_times(client):
    client.post("/cart/add/1")
    client.post("/cart/add/1")

    response = client.get("/cart")

    assert b"Total: $9.00" in response.data


# If this fails: made-up product numbers pile up in the cart and are counted at checkout (known bug, so this is marked as expected to fail).
@pytest.mark.xfail(
    strict=True,
    reason="Known bug: cart-add accepts product numbers that do not exist.",
)
def test_adding_a_product_that_does_not_exist_leaves_the_cart_empty(client):
    client.post("/cart/add/9999")

    with client.session_transaction() as sess:
        assert sess.get("cart", []) == []
