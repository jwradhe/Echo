import os
import time


def _register_and_create_echo(page, base_url):
    stamp = int(time.time() * 1000)
    username = f"e2e_user_{stamp}"
    email = f"e2e_user_{stamp}@example.com"
    password = "TestPassword123"
    echo = f"E2E Echo {stamp}"

    page.goto(base_url)

    page.get_by_role("button", name="Login").click()
    page.get_by_role("link", name="Register").click()

    page.locator("#display_name").fill("E2E User")
    page.locator("#reg_username").fill(username)
    page.locator("#reg_email").fill(email)
    page.locator("#reg_password").fill(password)
    page.get_by_role("button", name="Register").click()

    page.get_by_role("button", name="Let's Echo").wait_for(state="visible")
    page.get_by_role("button", name="Let's Echo").click()
    page.get_by_placeholder("What do you want to echo?").fill(echo)
    page.get_by_role("button", name="Post Echo").click()

    page.get_by_text(echo).wait_for(state="visible")

    return echo


def test_create_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    _register_and_create_echo(page, base_url)


def test_edit_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    echo = _register_and_create_echo(page, base_url)
    updated_echo = f"Updated {echo}"

    post = page.locator(".post-card").filter(has_text=echo)
    post.locator("button[data-bs-toggle='dropdown']").click()

    page.get_by_role("button", name="Edit").click()

    page.locator(".inline-edit-textarea").fill(updated_echo)
    page.get_by_role("button", name="Spara").click()

    page.get_by_text(updated_echo).wait_for(state="visible")


def test_delete_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    echo = _register_and_create_echo(page, base_url)

    post = page.locator(".post-card").filter(has_text=echo)
    post.locator("button[data-bs-toggle='dropdown']").click()
    page.get_by_role("button", name="Delete").click()
    page.locator("#deleteForm button[type='submit']").click()

    page.get_by_text(echo).wait_for(state="hidden")