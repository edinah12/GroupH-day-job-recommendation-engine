"""
Home view — displays latest jobs and a preview of the top 3 recommendations
for authenticated users who have completed their profile.
"""

from __future__ import annotations

from django.shortcuts import render, redirect
from django.db.models import Q

from recommender.models import Job, Company, JobCategory, Profile
from recommender.utils import get_user_profile
from recommender.recommendations.services import recommend_jobs


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
    search_query = request.GET.get("search", "").strip()

    jobs = Job.objects.select_related("company", "category").all()
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(company__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    recommended_jobs: list = []
    needs_profile: bool = False

    if not request.user.is_authenticated:
        featured_jobs = jobs.order_by("-posted_at")[:6]
        
        total_jobs = Job.objects.count()
        total_companies = Company.objects.count()
        categories = JobCategory.objects.all()[:6]
        return render(
            request,
            "welcome.html",
            {
                "featured_jobs": featured_jobs,
                "total_jobs": total_jobs,
                "total_companies": total_companies,
                "categories": categories,
                "search_query": search_query,
            },
        )

    profile = get_user_profile(request.user)
    if getattr(profile, 'is_recruiter', False):
        return redirect("recruiter_dashboard")

    try:
        recommended_jobs = recommend_jobs(profile)[:3]
    except Exception:
        needs_profile = True

    jobs = jobs.order_by("-posted_at")
        
    return render(
        request,
        "home.html",
        {
            "jobs": jobs,
            "search_query": search_query,
            "recommended_jobs": recommended_jobs,
            "needs_profile": needs_profile,
        },
    )