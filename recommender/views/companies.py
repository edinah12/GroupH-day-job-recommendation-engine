from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from ..models import Company


def company_list(request):
    search_query = request.GET.get("search", "").strip()
    companies = Company.objects.annotate(active_jobs_count=Count("jobs")).order_by("name")

    if search_query:
        companies = companies.filter(
            Q(name__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    return render(
        request,
        "companies/list.html",
        {
            "companies": companies,
            "search_query": search_query,
        },
    )


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
