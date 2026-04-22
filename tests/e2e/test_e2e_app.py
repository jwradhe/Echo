import os
import time
from PIL import Image


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


def _register_user_via_modal(page, base_url, username, email, password, display_name):
    page.goto(base_url)
    page.get_by_role("button", name="Login").click()
    page.get_by_role("link", name="Register").click()

    register_modal = page.locator("#registerModal")
    register_modal.locator("#display_name").fill(display_name)
    register_modal.locator("#reg_username").fill(username)
    register_modal.locator("#reg_email").fill(email)
    register_modal.locator("#reg_password").fill(password)
    register_modal.get_by_role("button", name="Register").click()

    page.get_by_role("button", name="Let's Echo").wait_for(state="visible")


def _login_user_via_modal(page, base_url, username, password):
    page.goto(base_url)
    page.get_by_role("button", name="Login").click()

    login_modal = page.locator("#loginModal")
    login_modal.locator("#username").fill(username)
    login_modal.locator("#password").fill(password)
    login_modal.get_by_role("button", name="Log in").click()

    page.get_by_role("button", name="Let's Echo").wait_for(state="visible")


def _logout_user(page):
    page.get_by_role("button", name="Log out").click()
    page.get_by_role("button", name="Login").wait_for(state="visible")


def test_create_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    _register_and_create_echo(page, base_url)


def test_edit_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    echo = _register_and_create_echo(page, base_url)
    updated_echo = f"Updated {echo}"

    # Find the post and click the three-dots menu
    post = page.locator(".post-card").filter(has_text=echo)
    dropdown_toggle = post.locator("button[data-bs-toggle='dropdown']")
    dropdown_toggle.click()
    
    # Wait a bit for Bootstrap dropdown animation
    page.wait_for_timeout(500)
    
    # Click the Edit button using onclick attribute
    edit_item = post.locator("button.dropdown-item[onclick*='startInlineEdit']")
    edit_item.click()

    page.locator(".inline-edit-textarea").fill(updated_echo)
    page.get_by_role("button", name="Spara").click()

    page.get_by_text(updated_echo).wait_for(state="visible")


def test_delete_echo(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    echo = _register_and_create_echo(page, base_url)

    # Find the post and click the three-dots menu
    post = page.locator(".post-card").filter(has_text=echo)
    dropdown_toggle = post.locator("button[data-bs-toggle='dropdown']")
    dropdown_toggle.click()
    
    # Wait a bit for Bootstrap dropdown animation
    page.wait_for_timeout(500)
    
    # Click the Delete button using onclick attribute
    delete_item = post.locator("button.dropdown-item[onclick*='confirmDelete']")
    delete_item.click()
    
    page.locator("#deleteForm button[type='submit']").click()

    page.get_by_text(echo).wait_for(state="hidden")


def test_update_profile(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    _register_and_create_echo(page, base_url)

    updated_display_name = "E2E Updated User"
    updated_bio = "Updated bio from E2E profile test"

    page.goto(f"{base_url}/profile")
    page.locator("#profile_display_name").fill(updated_display_name)
    page.locator("#profile_bio").fill(updated_bio)
    page.get_by_role("button", name="Save profile").click()

    page.get_by_text(updated_display_name).first.wait_for(state="visible")
    page.get_by_text(updated_bio).first.wait_for(state="visible")


def test_upload_profile_picture(page, tmp_path):
    """E2E test for profile picture upload with file input."""
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    _register_and_create_echo(page, base_url)

    # Create a temporary test image
    test_image_path = tmp_path / "test_avatar.png"
    img = Image.new("RGB", (800, 800), color=(255, 100, 50))
    img.save(test_image_path, format="PNG")

    # Navigate to profile page
    page.goto(f"{base_url}/profile")

    # Upload the profile picture
    page.locator("input[name='profile_picture']").set_input_files(str(test_image_path))
    page.get_by_role("button", name="Upload").click()

    # Wait for page reload after upload
    page.wait_for_load_state("networkidle")

    # Verify the profile image is updated (check src attribute contains .webp)
    profile_img = page.locator(".profile-avatar-lg")
    src = profile_img.get_attribute("src")
    assert src is not None
    assert ".webp" in src
    assert "/static/uploads/profile/" in src


def test_follow_user_from_profile(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    stamp = int(time.time() * 1000)

    viewer_username = f"e2e_follow_viewer_{stamp}"
    viewer_email = f"{viewer_username}@example.com"
    target_username = f"e2e_follow_target_{stamp}"
    target_email = f"{target_username}@example.com"
    password = "TestPassword123"

    _register_user_via_modal(
        page,
        base_url,
        viewer_username,
        viewer_email,
        password,
        "Follower User",
    )
    _logout_user(page)

    _register_user_via_modal(
        page,
        base_url,
        target_username,
        target_email,
        password,
        "Target User",
    )

    page.get_by_role("button", name="Let's Echo").click()
    page.get_by_placeholder("What do you want to echo?").fill(f"Follow target post {stamp}")
    page.get_by_role("button", name="Post Echo").click()
    _logout_user(page)

    _login_user_via_modal(page, base_url, viewer_username, password)
    page.goto(f"{base_url}/profile/{target_username}")

    page.get_by_role("button", name="Follow").click()
    page.get_by_role("button", name="Unfollow").wait_for(state="visible")
    page.locator(".followers-list").get_by_text(f"@{viewer_username}").wait_for(state="visible")


def test_search_posts_with_partial_keyword(page):
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
    echo = _register_and_create_echo(page, base_url)
    partial_term = echo.split()[-1][:4]

    page.locator("#feedSearchInput").fill(partial_term)
    page.locator(".search-form button[type='submit']").click()

    page.get_by_text(f'Search results for "{partial_term}"').wait_for(state="visible")
    page.locator(".search-post-item").get_by_text(echo).wait_for(state="visible")
