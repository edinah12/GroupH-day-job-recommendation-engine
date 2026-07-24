from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from recommender.decorators import recruiter_required, seeker_required
from recommender.models import Job, Application, SavedJob
from recommender.utils import get_user_profile


@login_required
def dashboard(request):
    profile = get_user_profile(request.user)
    if profile.is_recruiter:
        return recruiter_dashboard(request)
    return seeker_dashboard(request)


@recruiter_required
def recruiter_dashboard(request):
    posted_jobs = Job.objects.filter(posted_by=request.user).order_by("-posted_at")
    total_applications = Application.objects.filter(job__posted_by=request.user).count()

    return render(
        request,
        "dashboard/recruiter.html",
        {
            "jobs": posted_jobs,
            "total_jobs": posted_jobs.count(),
            "total_applications": total_applications,
        },
    )


@seeker_required
def seeker_dashboard(request):
    applications = Application.objects.filter(user=request.user).order_by("-applied_at")
    saved_jobs = SavedJob.objects.filter(user=request.user).order_by("-saved_at")

    return render(
        request,
        "dashboard/seeker.html",
        {
            "applications": applications,
            "saved_jobs": saved_jobs,
        },
    )
