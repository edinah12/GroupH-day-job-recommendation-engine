from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from ..models import Company
from ..search import fuzzy_filter


def _company_search_text(company):
    # See recommender/views/jobs.py::_job_search_text for why description
    # is excluded from the fuzzy pass (it's covered by the exact pass).
    return " ".join(filter(None, [company.name, company.location]))


@login_required
def company_list(request):
    search_query = request.GET.get("search", "").strip()
    companies = Company.objects.annotate(active_jobs_count=Count("jobs")).order_by("name")

    if search_query:
        # Typo-tolerant: also catches close misspellings, not just exact
        # substrings. See recommender/search.py.
        companies = fuzzy_filter(
            companies,
            search_query,
            exact_fields=["name", "location", "description"],
            text_fn=_company_search_text,
        )

    return render(
        request,
        "companies/list.html",
        {
            "companies": companies,
            "search_query": search_query,
        },
    )


@login_required
def company_detail(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    jobs = company.jobs.select_related("category").order_by("-posted_at")
    return render(
        request,
        "companies/detail.html",
        {
            "company": company,
            "jobs": jobs,
        },
    )
