"""
Dashboard view — summary page for authenticated users.

Shows: welcome message, quick stats, top recommendations,
recent applications, saved jobs, and profile completion %.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from recommender.decorators import recruiter_required, seeker_required
from recommender.models import Application, Job, Profile, SavedJob
from recommender.utils import get_user_profile
from recommender.recommendations.services import recommend_jobs


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
    profile = get_user_profile(request.user)
    if getattr(profile, 'is_recruiter', False):
        return recruiter_dashboard(request)
    return seeker_dashboard(request)


@recruiter_required
def recruiter_dashboard(request):
    posted_jobs = Job.objects.filter(company__in=request.user.companies.all() if hasattr(request.user, 'companies') else []).order_by("-posted_at")
    
    # We will just render the redesigned dashboard for recruiters for now, or fallback to the teammate's template
    # Since teammates created "dashboard/recruiter.html", let's use it.
    total_applications = Application.objects.filter(job__in=posted_jobs).count()
    recent_applications = (
        Application.objects.filter(job__in=posted_jobs)
        .select_related("user", "job")
        .order_by("-applied_at")[:5]
    )

    return render(
        request,
        "dashboard/recruiter.html",
        {
            "total_jobs": posted_jobs.count(),
            "total_applications": total_applications,
            "recent_applications": recent_applications,
        },
    )


@recruiter_required
def recruiter_jobs(request):
    posted_jobs = Job.objects.filter(company__in=request.user.companies.all() if hasattr(request.user, 'companies') else []).order_by("-posted_at")

    return render(
        request,
        "dashboard/recruiter_jobs.html",
        {
            "jobs": posted_jobs,
        },
    )


@seeker_required
def seeker_dashboard(request):
    profile = get_user_profile(request.user)
    
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
