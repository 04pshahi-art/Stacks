"""Registration, sign-in, lockout and who can reach what without signing in."""
from conftest import PASSWORD

REGISTER = {"username": "newreader", "email": "new@example.com", "password": PASSWORD, "confirm": PASSWORD}


def is_signed_in(browser) -> bool:
    return browser.get("/books/upload").status_code == 200


def test_registering_creates_an_account_and_signs_in(client):
    assert client.post("/register", data=REGISTER).status_code == 302
    assert is_signed_in(client)


def test_a_weak_password_is_refused(client):
    response = client.post("/register", data={**REGISTER, "password": "password", "confirm": "password"})
    assert response.status_code == 200
    assert not is_signed_in(client)


def test_a_taken_username_or_email_is_refused(client, make_user):
    make_user("newreader")
    assert client.post("/register", data=REGISTER).status_code == 200


def test_wrong_password_does_not_sign_in(client, make_user):
    make_user("reader")
    response = client.post("/login", data={"identifier": "reader", "password": "Wrong-Pass-99"})
    assert response.status_code == 200
    assert not is_signed_in(client)


def test_unknown_account_and_wrong_password_look_the_same(client, make_user):
    make_user("reader")
    unknown = client.post("/login", data={"identifier": "nobody", "password": "Wrong-Pass-99"})
    wrong = client.post("/login", data={"identifier": "reader", "password": "Wrong-Pass-99"})
    assert unknown.status_code == wrong.status_code == 200
    assert b"Those details didn" in unknown.data and b"Those details didn" in wrong.data


def test_repeated_failures_lock_the_account_even_for_the_right_password(client, app, make_user):
    make_user("reader")
    for _ in range(app.config["LOGIN_MAX_FAILURES"]):
        client.post("/login", data={"identifier": "reader", "password": "Wrong-Pass-99"})
    client.post("/login", data={"identifier": "reader", "password": PASSWORD})
    assert not is_signed_in(client)


def test_pages_that_need_an_account_send_visitors_to_sign_in(client):
    response = client.get("/books/upload")
    assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_api_calls_without_an_account_get_401_not_a_redirect(client):
    assert client.get("/api/books/1/toc").status_code == 401
    assert client.post("/api/speech/synthesize", json={"text": "hi"}).status_code == 401


def test_login_will_not_redirect_to_another_website(client, make_user):
    make_user("reader")
    response = client.post(
        "/login?next=https://evil.example/steal",
        data={"identifier": "reader", "password": PASSWORD},
    )
    assert response.status_code == 302 and "evil.example" not in response.headers["Location"]


def test_changing_the_password_signs_out_other_sessions(app, make_user, sign_in):
    from app.extensions import db

    user = make_user("reader")
    browser = sign_in("reader")
    assert is_signed_in(browser)
    user.auth_version += 1  # what a password change does
    db.session.commit()
    assert not is_signed_in(browser)


def test_signing_out_needs_a_post(client, make_user, sign_in):
    make_user("reader")
    browser = sign_in("reader")
    assert browser.get("/logout").status_code == 405
    assert browser.post("/logout").status_code == 302
    assert not is_signed_in(browser)
