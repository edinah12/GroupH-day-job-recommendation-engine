from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from recommender.forms import ProfileForm
from recommender.utils import get_user_profile


@login_required
def view_profile(request):
    profile = get_user_profile(request.user)
    return render(
        request,
        "profile/detail.html",
        {"profile": profile},
    )


@login_required
def edit_profile(request):
    profile = get_user_profile(request.user)
    is_setup = not profile.is_complete

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            if is_setup:
                messages.success(request, "Profile saved. You can now explore job recommendations.")
            else:
                messages.success(request, "Your profile has been updated.")
            return redirect("view_profile")
    else:
        form = ProfileForm(instance=profile)

    template = "profile/setup.html" if is_setup else "profile/edit.html"
    return render(
        request,
        template,
        {"form": form, "profile": profile, "is_setup": is_setup},
    )


@login_required
def create_profile(request):
    return redirect("edit_profile")
