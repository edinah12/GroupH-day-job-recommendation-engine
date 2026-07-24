from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from recommender.utils import get_user_profile


def recruiter_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        profile = get_user_profile(request.user)
        if not profile.is_recruiter:
            messages.error(request, "Access restricted to recruiters only.")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def seeker_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        profile = get_user_profile(request.user)
        if not profile.is_seeker:
            messages.error(request, "Access restricted to job seekers only.")
            return redirect("recruiter_dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped_view
