from django.shortcuts import redirect
from django.urls import reverse

from recommender.models import Profile


def get_user_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def profile_setup_redirect(user):
    profile = get_user_profile(user)
    if not profile.is_complete:
        return redirect("edit_profile")
    return None


def post_login_url(user):
    profile = get_user_profile(user)
    if not profile.is_complete:
        return reverse("edit_profile")
    if profile.is_recruiter:
        return reverse("recruiter_dashboard")
    return reverse("home")
