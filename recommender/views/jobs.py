from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from recommender.decorators import recruiter_required, seeker_required
from recommender.forms import JobForm
from recommender.models import Job, Application, JobCategory
from recommender.utils import get_user_profile


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    has_applied = False
    is_owner = False

    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
        if profile.is_seeker:
            has_applied = Application.objects.filter(user=request.user, job=job).exists()
        elif profile.is_recruiter and job.posted_by == request.user:
            is_owner = True

    return render(
        request,
        "jobs/detail.html",
        {
            "job": job,
            "has_applied": has_applied,
            "is_owner": is_owner,
        },
    )


@recruiter_required
def create_job(request):
    profile = get_user_profile(request.user)

    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(user=request.user)
            messages.success(request, f"Job listing '{job.title}' has been successfully posted!")
            return redirect("recruiter_dashboard")
    else:
        initial = {}
        if profile.company_name:
            initial["company_name"] = profile.company_name
        form = JobForm(initial=initial)

    return render(
        request,
        "jobs/create.html",
        {"form": form},
    )


@recruiter_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if job.posted_by != request.user:
        messages.error(request, "You do not have permission to edit this job.")
        return redirect("recruiter_dashboard")

    if request.method == "POST":
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, f"Job listing '{job.title}' has been updated.")
            return redirect("recruiter_dashboard")
    else:
        form = JobForm(instance=job)

    return render(
        request,
        "jobs/edit.html",
        {"form": form, "job": job},
    )


@recruiter_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if job.posted_by != request.user:
        messages.error(request, "You do not have permission to delete this job.")
        return redirect("recruiter_dashboard")

    if request.method == "POST":
        title = job.title
        job.delete()
        messages.success(request, f"Job listing '{title}' was deleted.")
        return redirect("recruiter_dashboard")

    return render(request, "jobs/delete_confirm.html", {"job": job})


@seeker_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if Application.objects.filter(user=request.user, job=job).exists():
        messages.info(request, "You have already applied for this job.")
    else:
        Application.objects.create(user=request.user, job=job)
        messages.success(request, f"Your application for '{job.title}' has been submitted successfully!")

    return redirect("job_detail", job_id=job.id)


@recruiter_required
def job_applicants(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if job.posted_by != request.user:
        messages.error(request, "You do not have permission to view applicants for this job.")
        return redirect("recruiter_dashboard")

    applications = job.applications.select_related("user", "user__profile").order_by("-applied_at")

    return render(
        request,
        "jobs/applicants.html",
        {"job": job, "applications": applications},
    )


@recruiter_required
def update_application_status(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    if application.job.posted_by != request.user:
        messages.error(request, "Permission denied.")
        return redirect("recruiter_dashboard")

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()
            messages.success(request, f"Application status updated to '{new_status}'.")

    return redirect("job_applicants", job_id=application.job.id)