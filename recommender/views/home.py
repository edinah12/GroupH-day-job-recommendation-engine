from django.shortcuts import render, redirect
from django.db.models import Q
from ..models import Job, Company, JobCategory
from ..search import fuzzy_filter
from ..utils import get_user_profile


def _job_search_text(job):
    # See recommender/views/jobs.py::_job_search_text for why description
    # is excluded from the fuzzy pass (it's covered by the exact pass).
    return " ".join(
        filter(
            None,
            [
                job.title,
                job.company.name if job.company_id else "",
                job.location,
            ],
        )
    )


def home(request):
    search_query = request.GET.get("search", "").strip()

    if not request.user.is_authenticated:
        featured_jobs = Job.objects.select_related("company", "category").order_by("-posted_at")
        if search_query:
            # Typo-tolerant: also catches close misspellings, not just
            # exact substrings. See recommender/search.py.
            featured_jobs = fuzzy_filter(
                featured_jobs,
                search_query,
                exact_fields=["title", "company__name", "description"],
                text_fn=_job_search_text,
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
        jobs = fuzzy_filter(
            jobs,
            search_query,
            exact_fields=["title", "company__name", "description"],
            text_fn=_job_search_text,
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