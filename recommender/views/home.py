"""
Home view — displays latest jobs and a preview of the top 3 recommendations
for authenticated users who have completed their profile.
"""

from __future__ import annotations

from django.shortcuts import render

from ..models import Job, Profile
from ..recommendations.services import recommend_jobs


def home(request):
    """
    Render the home page.

    Context:
        jobs (QuerySet):         All available jobs with company prefetched.
        recommended_jobs (list): Top-3 scored recommendations (authenticated
                                 users with a profile only).
        needs_profile (bool):    True when the user is authenticated but has
                                 not yet created a profile.
    """
    jobs = Job.objects.select_related("company", "category").all()

    recommended_jobs: list = []
    needs_profile: bool = False

    if request.user.is_authenticated:
        try:
            profile: Profile = request.user.profile
            recommended_jobs = recommend_jobs(profile)[:3]
        except Profile.DoesNotExist:
            needs_profile = True

    return render(
        request,
        "home.html",
        {
            "jobs": jobs,
            "recommended_jobs": recommended_jobs,
            "needs_profile": needs_profile,
        },
    )