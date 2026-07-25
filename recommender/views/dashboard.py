"""
Dashboard view — summary page for authenticated users.

Shows: welcome message, quick stats, top recommendations,
recent applications, saved jobs, and profile completion %.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..models import Application, Job, Profile, SavedJob
from ..recommendations.services import recommend_jobs


def _profile_completion(profile: Profile) -> int:
    """Return a 0-100 integer representing how complete the profile is."""
    fields = [
        profile.phone,
        profile.bio,
        profile.education,
        profile.skills,
        profile.preferred_location,
        profile.preferred_category,
        profile.resume,
        profile.profile_picture,
    ]
    filled = sum(1 for f in fields if f)
    return round((filled / len(fields)) * 100)


@login_required
def dashboard(request):
    """Render the user dashboard."""
    try:
        profile: Profile = request.user.profile
    except Profile.DoesNotExist:
        return redirect("create_profile")

    # --- Stats ---
    total_jobs       = Job.objects.count()
    applied_count    = Application.objects.filter(user=request.user).count()
    saved_count      = SavedJob.objects.filter(user=request.user).count()
    completion_pct   = _profile_completion(profile)

    # --- Top 5 recommendations ---
    top_recommendations = recommend_jobs(profile)[:5]

    # --- Recent applications (last 5) ---
    recent_applications = (
        Application.objects
        .filter(user=request.user)
        .select_related("job", "job__company")
        .order_by("-applied_at")[:5]
    )

    # --- Saved jobs (last 4) ---
    saved_jobs = (
        SavedJob.objects
        .filter(user=request.user)
        .select_related("job", "job__company", "job__category")
        .order_by("-saved_at")[:4]
    )

    return render(request, "dashboard.html", {
        "profile":             profile,
        "total_jobs":          total_jobs,
        "applied_count":       applied_count,
        "saved_count":         saved_count,
        "completion_pct":      completion_pct,
        "top_recommendations": top_recommendations,
        "recent_applications": recent_applications,
        "saved_jobs":          saved_jobs,
    })
