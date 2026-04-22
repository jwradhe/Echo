from __future__ import annotations
from io import BytesIO
from pathlib import Path
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user
from PIL import Image, UnidentifiedImageError
from .profile import (
    create_profile,
    delete_profile,
    follow_user,
    get_profile_by_username,
    is_following,
    list_followers,
    list_following,
    list_recent_posts_for_user,
    unfollow_user,
    upsert_profile_image,
    update_profile,
)

profile_bp = Blueprint("profile", __name__)

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def _normalize_profile_input(display_name: str | None, bio: str | None) -> tuple[str | None, str | None]:
    clean_display_name = (display_name or "").strip() or None
    clean_bio = (bio or "").strip() or None

    if clean_display_name and len(clean_display_name) > 255:
        raise ValueError("Display name can be at most 255 characters.")
    if clean_bio and len(clean_bio) > 500:
        raise ValueError("Bio can be at most 500 characters.")

    return clean_display_name, clean_bio


def _transform_profile_image(raw_bytes: bytes) -> bytes:
    max_dimension = int(current_app.config.get("PROFILE_IMAGE_MAX_DIMENSION", 512))

    with Image.open(BytesIO(raw_bytes)) as image:
        source_format = (image.format or "").upper()
        if source_format not in ALLOWED_IMAGE_FORMATS:
            raise ValueError("Only JPG, PNG, and WEBP images are allowed.")

        normalized = image.convert("RGBA")
        normalized.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        out_buffer = BytesIO()
        normalized.save(out_buffer, format="WEBP", quality=85, method=6)
        return out_buffer.getvalue()


@profile_bp.route("/profile")
@login_required
def my_profile():
    return redirect(url_for("profile.user_profile", username=current_user.username))


@profile_bp.route("/profile/<username>")
def user_profile(username: str):
    default_avatar_url = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop"
    profile = get_profile_by_username(username)
    if not profile:
        flash("Profile not found.", "danger")
        return redirect(url_for("dashboard"))

    recent_posts = list_recent_posts_for_user(profile["user_id"], limit=20)
    is_owner = current_user.is_authenticated and current_user.get_id() == profile["user_id"]
    viewer_is_following = (
        current_user.is_authenticated
        and not is_owner
        and is_following(current_user.get_id(), profile["user_id"])
    )
    followers = list_followers(profile["user_id"], limit=20)
    following = list_following(profile["user_id"], limit=20)

    return render_template(
        "profile.html",
        profile=profile,
        recent_posts=recent_posts,
        is_owner=is_owner,
        viewer_is_following=viewer_is_following,
        followers=followers,
        following=following,
        default_avatar_url=default_avatar_url,
    )


@profile_bp.route("/profile", methods=["POST"])
@login_required
def update_my_profile():
    try:
        display_name, bio = _normalize_profile_input(
            request.form.get("display_name"),
            request.form.get("bio"),
        )
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("profile.my_profile"))

    updated = update_profile(current_user.get_id(), display_name, bio)
    if not updated:
        flash("Could not update profile.", "danger")
        return redirect(url_for("profile.my_profile"))

    flash("Profile updated.", "success")
    return redirect(url_for("profile.my_profile"))


@profile_bp.route("/profile/picture", methods=["POST"])
@login_required
def update_profile_picture():
    file = request.files.get("profile_picture")
    if not file or not file.filename:
        flash("Choose an image to upload.", "danger")
        return redirect(url_for("profile.my_profile"))

    raw_bytes = file.read()
    max_bytes = int(current_app.config.get("PROFILE_IMAGE_MAX_BYTES", 5 * 1024 * 1024))
    if not raw_bytes:
        flash("Uploaded file is empty.", "danger")
        return redirect(url_for("profile.my_profile"))
    if len(raw_bytes) > max_bytes:
        flash("Image is too large. Maximum size is 5 MB.", "danger")
        return redirect(url_for("profile.my_profile"))

    try:
        transformed = _transform_profile_image(raw_bytes)
    except UnidentifiedImageError:
        flash("Invalid image file.", "danger")
        return redirect(url_for("profile.my_profile"))
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("profile.my_profile"))

    upload_subdir = current_app.config.get("PROFILE_IMAGE_UPLOAD_SUBDIR", "uploads/profile")
    upload_dir = Path(current_app.static_folder) / upload_subdir
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{current_user.get_id()}.webp"
    absolute_file_path = upload_dir / file_name
    absolute_file_path.write_bytes(transformed)

    media_url = url_for("static", filename=f"{upload_subdir}/{file_name}")
    updated = upsert_profile_image(current_user.get_id(), media_url, media_type="image/webp")
    if not updated:
        flash("Could not update profile picture.", "danger")
        return redirect(url_for("profile.my_profile"))

    flash("Profile picture updated.", "success")
    return redirect(url_for("profile.my_profile"))


@profile_bp.route("/profile/delete", methods=["POST"])
@login_required
def delete_my_profile():
    deleted = delete_profile(current_user.get_id())
    if not deleted:
        flash("Could not delete profile.", "danger")
        return redirect(url_for("profile.my_profile"))

    logout_user()
    flash("Your account has been deactivated.", "info")
    return redirect(url_for("dashboard"))


@profile_bp.route("/profile/<username>/follow", methods=["POST"])
@login_required
def toggle_follow_user(username: str):
    profile = get_profile_by_username(username)
    if not profile:
        flash("Profile not found.", "danger")
        return redirect(url_for("dashboard"))

    follower_id = current_user.get_id()
    followed_id = profile["user_id"]
    if follower_id == followed_id:
        flash("You cannot follow yourself.", "warning")
        return redirect(url_for("profile.user_profile", username=username))

    if is_following(follower_id, followed_id):
        unfollow_user(follower_id, followed_id)
        flash(f"You unfollowed @{profile['username']}.", "info")
    else:
        did_follow = follow_user(follower_id, followed_id)
        if did_follow or is_following(follower_id, followed_id):
            flash(f"You are now following @{profile['username']}.", "success")
        else:
            flash("Could not follow this user.", "danger")

    return redirect(url_for("profile.user_profile", username=username))


@profile_bp.route("/api/profile/<username>", methods=["GET"])
def get_profile_api(username: str):
    profile = get_profile_by_username(username)
    if not profile:
        return {"error": "Profile not found"}, 404

    return {
        "user_id": profile["user_id"],
        "username": profile["username"],
        "display_name": profile.get("display_name"),
        "bio": profile.get("bio"),
        "profile_image_url": profile.get("profile_image_url"),
        "created_at": profile.get("created_at").isoformat() if profile.get("created_at") else None,
        "posts_count": int(profile.get("posts_count") or 0),
        "followers_count": int(profile.get("followers_count") or 0),
        "following_count": int(profile.get("following_count") or 0),
    }, 200


@profile_bp.route("/api/profile/<username>/follow", methods=["GET", "POST", "DELETE"])
@login_required
def follow_profile_api(username: str):
    profile = get_profile_by_username(username)
    if not profile:
        return {"error": "Profile not found"}, 404

    follower_id = current_user.get_id()
    followed_id = profile["user_id"]
    if follower_id == followed_id:
        return {"error": "You cannot follow yourself"}, 400

    if request.method == "GET":
        return {
            "username": profile["username"],
            "is_following": is_following(follower_id, followed_id),
        }, 200

    if request.method == "POST":
        created = follow_user(follower_id, followed_id)
        currently_following = created or is_following(follower_id, followed_id)
        if not currently_following:
            return {"error": "Failed to follow user"}, 500
        return {
            "success": True,
            "username": profile["username"],
            "is_following": True,
            "created": bool(created),
        }, 200

    deleted = unfollow_user(follower_id, followed_id)
    return {
        "success": True,
        "username": profile["username"],
        "is_following": False,
        "deleted": bool(deleted),
    }, 200


@profile_bp.route("/api/profile", methods=["POST"])
@login_required
def create_profile_api():
    payload = request.get_json(silent=True) or {}
    try:
        display_name, bio = _normalize_profile_input(payload.get("display_name"), payload.get("bio"))
    except ValueError as exc:
        return {"error": str(exc)}, 400

    created = create_profile(current_user.get_id(), display_name, bio)
    if not created:
        return {"error": "Failed to create profile"}, 500

    return {"success": True}, 201


@profile_bp.route("/api/profile", methods=["PUT"])
@login_required
def update_profile_api():
    payload = request.get_json(silent=True) or {}
    try:
        display_name, bio = _normalize_profile_input(payload.get("display_name"), payload.get("bio"))
    except ValueError as exc:
        return {"error": str(exc)}, 400

    updated = update_profile(current_user.get_id(), display_name, bio)
    if not updated:
        return {"error": "Failed to update profile"}, 500

    return {"success": True}, 200


@profile_bp.route("/api/profile", methods=["DELETE"])
@login_required
def delete_profile_api():
    deleted = delete_profile(current_user.get_id())
    if not deleted:
        return jsonify({"error": "Failed to delete profile"}), 500

    logout_user()
    return jsonify({"success": True}), 200