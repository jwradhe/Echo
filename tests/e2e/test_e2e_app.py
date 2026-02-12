import os
import time


def test_create_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    stamp = int(time.time() * 1000)
    username = f"e2e_user_{stamp}"
    email = f"e2e_user_{stamp}@example.com"
    password = "TestPassword123"
    echo = f"E2E Echo {stamp}"

    page.goto(f"{base_url}/register")
    page.get_by_label("Display name").fill("E2E User")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Register").click()

    page.get_by_role("button", name="Let's Echo").wait_for(state="visible")

    page.get_by_role("button", name="Let's Echo").click()
    page.get_by_placeholder("What do you want to echo?").fill(echo)
    page.get_by_role("button", name="Post Echo").click()

    page.get_by_text(echo).wait_for(state="visible")
