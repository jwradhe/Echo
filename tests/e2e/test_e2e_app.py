import os
import time


def test_create_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    echo = f"E2E Echo {int(time.time() * 1000)}"

    page.goto(f"{base_url}/dashboard")

    page.get_by_role("button", name="Let's Echo").click()
    page.get_by_placeholder("What do you want to echo?").fill(echo)
    page.get_by_role("button", name="Post Echo").click()

    page.get_by_text(echo).wait_for(state="visible")
