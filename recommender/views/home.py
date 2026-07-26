from django.shortcuts import render, redirect
from django.db.models import Q
from ..models import Job, Company, JobCategory
from ..utils import get_user_profile


def home(request):
    search_query = request.GET.get("search", "").strip()

    if not request.user.is_authenticated:
        featured_jobs = Job.objects.select_related("company", "category").order_by("-posted_at")
        if search_query:
            featured_jobs = featured_jobs.filter(
                Q(title__icontains=search_query) |
                Q(company__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        featured_jobs = featured_jobs[:6]
        
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
    if profile.is_recruiter:
        return redirect("recruiter_dashboard")

    jobs = Job.objects.select_related("company", "category").order_by("-posted_at")
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(company__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
        
    recommended_jobs = []
    try:
        from recommender.recommendations.services import recommend_jobs
        recommended_jobs = recommend_jobs(profile)[:4]
    except Exception:
        pass

    return render(
        request,
        "home.html",
        {
            "jobs": jobs,
            "recommended_jobs": recommended_jobs,
            "search_query": search_query,
        },
    )