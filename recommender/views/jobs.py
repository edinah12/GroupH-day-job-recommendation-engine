from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from recommender.decorators import recruiter_required, seeker_required
from recommender.forms import JobForm, JobApplicationForm, JobSearchForm, QualificationDocumentVerifyForm
from recommender.models import Job, Application, JobCategory, SavedJob, JobView, QualificationDocument
from recommender.search import fuzzy_filter
from recommender.utils import get_user_profile

# Every sort option maps to a full order_by() tuple that always ends with a
# stable secondary key (-id/id). Without that tie-breaker, rows that share
# the exact same posted_at/salary/deadline value can come back in a
# different order on every request, which makes "Oldest to Newest" /
# "Newest to Oldest" look broken even though the primary field is correct.
JOB_SORT_OPTIONS = {
    "-posted_at": ("-posted_at", "-id"),   # Newest to Oldest
    "posted_at": ("posted_at", "id"),      # Oldest to Newest
    "-salary": ("-salary", "-posted_at", "-id"),
    "salary": ("salary", "-posted_at", "-id"),
    "deadline": ("deadline", "-posted_at", "-id"),
}
DEFAULT_JOB_SORT = "-posted_at"


def _job_search_text(job):
    # Deliberately excludes description/requirements: those are long,
    # generic free-text fields, and comparing typo'd words against every
    # word in them causes incidental collisions with unrelated boilerplate
    # (e.g. a typo'd "developr" fuzzy-matching the word "develop" inside
    # an unrelated "policy development" phrase). Exact substring search
    # still covers description/requirements via `exact_fields` below -
    # only the fuzzy/typo-tolerant pass is scoped to these more specific,
    # job-identifying fields.
    return " ".join(
        filter(
            None,
            [
                job.title,
                job.company.name if job.company_id else "",
                job.location,
                job.required_skills,
                job.category.name if job.category_id else "",
            ],
        )
    )


@login_required
def job_list(request):
    """
    Public job listings page with Search & Filtering.

    Supports refining results by keyword, location, pay (salary range),
    job type, category and company - all combinable at once - plus
    sorting. This view is independent of the recommendation engine
    (recommender.recommendations.services); it never touches match
    scores and only narrows down the plain Job queryset.
    """
    search_form = JobSearchForm(request.GET or None)

    jobs = Job.objects.select_related("company", "category")

    # search_form.is_valid() also runs even with an empty query dict
    # (all fields are optional), so this safely handles a fresh page load.
    if search_form.is_valid():
        data = search_form.cleaned_data

        search_query = (data.get("search") or "").strip()
        if search_query:
            # Typo-tolerant: matches exact/substring hits AND close
            # misspellings or related word forms (e.g. "developr" still
            # finds "Developer" roles). See recommender/search.py.
            jobs = fuzzy_filter(
                jobs,
                search_query,
                exact_fields=[
                    "title",
                    "company__name",
                    "description",
                    "requirements",
                    "required_skills",
                ],
                text_fn=_job_search_text,
            )

        location_query = (data.get("location") or "").strip()
        if location_query:
            jobs = jobs.filter(location__icontains=location_query)

        company = data.get("company")
        if company:
            jobs = jobs.filter(company=company)

        category = data.get("category")
        if category:
            jobs = jobs.filter(category=category)

        job_type = data.get("job_type")
        if job_type:
            jobs = jobs.filter(job_type=job_type)

        min_salary = data.get("min_salary")
        if min_salary is not None:
            jobs = jobs.filter(salary__gte=min_salary)

        max_salary = data.get("max_salary")
        if max_salary is not None:
            jobs = jobs.filter(salary__lte=max_salary)

    # Sorting is resolved independently of search_form.is_valid() above, so
    # an unrelated invalid field (e.g. a bad salary value) can never cause
    # the chosen sort order to be silently dropped. The raw GET value is
    # checked against a fixed whitelist of real order_by() tuples, so this
    # is also safe from arbitrary field injection.
    sort_key = request.GET.get("sort")
    if sort_key not in JOB_SORT_OPTIONS:
        sort_key = DEFAULT_JOB_SORT
    jobs = jobs.order_by(*JOB_SORT_OPTIONS[sort_key])

    return render(
        request,
        "jobs/list.html",
        {
            "jobs": jobs,
            "search_form": search_form,
            "active_filters": _has_active_filters(search_form),
        },
    )


def _has_active_filters(search_form: JobSearchForm) -> bool:
    """True if the user has applied any search/filter criteria at all."""
    if not search_form.is_bound:
        return False
    return any(
        (search_form.data.get(name) or "").strip()
        for name in search_form.fields
    )


@login_required
def job_detail(request, job_id: int):
    """
    Render the job detail page.

    For authenticated seekers:
      - Checks whether the user has already applied (has_applied).
      - Checks whether the user has saved this job (is_saved).
      - Records a JobView (silently ignored on repeat visits via get_or_create).

    For authenticated recruiters who own the job:
      - Sets is_owner = True to show management controls.
    """
    job = get_object_or_404(
        Job.objects.select_related("company", "category"),
        id=job_id,
    )
    has_applied = False
    is_saved = False
    is_owner = False

    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
        if profile.is_seeker:
            has_applied = Application.objects.filter(
                user=request.user, job=job
            ).exists()
            is_saved = SavedJob.objects.filter(
                user=request.user, job=job
            ).exists()
            # Record first view; subsequent visits are silently ignored.
            JobView.objects.get_or_create(user=request.user, job=job)
        elif profile.is_recruiter and job.posted_by == request.user:
            is_owner = True

    return render(
        request,
        "jobs/detail.html",
        {
            "job": job,
            "has_applied": has_applied,
            "is_saved": is_saved,
            "is_owner": is_owner,
        },
    )


@seeker_required
def toggle_save_job(request, job_id: int):
    """
    Toggle the saved state of a job for the current seeker.

    POST-only endpoint.  Uses get_or_create so a double-submit never
    creates duplicate rows.  If the job was already saved the existing
    SavedJob row is deleted (unsave).  Redirects back to the job detail
    page with a flash message in both cases.
    """
    if request.method != "POST":
        return redirect("job_detail", job_id=job_id)

    job = get_object_or_404(Job, id=job_id)
    saved_obj, created = SavedJob.objects.get_or_create(
        user=request.user, job=job
    )

    if created:
        messages.success(request, f"\"{job.title}\" added to your saved jobs.")
    else:
        saved_obj.delete()
        messages.info(request, f"\"{job.title}\" removed from saved jobs.")

    return redirect("job_detail", job_id=job_id)


@login_required
def saved_jobs(request):
    """
    Display a paginated list of jobs the current user has saved.

    Results are ordered newest-saved-first.  Only available to
    authenticated users; seekers see their own saved jobs.
    """
    saved = (
        SavedJob.objects
        .filter(user=request.user)
        .select_related("job", "job__company", "job__category")
        .order_by("-saved_at")
    )

    paginator = Paginator(saved, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "jobs/saved.html", {"page_obj": page_obj})


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
    profile = get_user_profile(request.user)

    existing_application = Application.objects.filter(user=request.user, job=job).first()
    if existing_application:
        messages.info(request, f"You have already submitted an application for '{job.title}'.")
        return render(
            request,
            "jobs/apply.html",
            {
                "job": job,
                "profile": profile,
                "already_applied": True,
                "application": existing_application,
            },
        )

    if request.method == "POST":
        form = JobApplicationForm(request.POST, request.FILES, profile=profile)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.job = job
            application.save()

            if request.FILES.get("resume"):
                profile.resume = request.FILES["resume"]
                profile.save()

            # Documents chosen from the seeker's existing archive.
            selected_documents = list(form.cleaned_data.get("attached_documents") or [])

            # Any brand-new documents (e.g. an award or certificate they
            # didn't already have saved) are added to the archive first,
            # then attached to this application alongside the selected ones.
            new_files = form.cleaned_data.get("new_documents") or []
            new_document_type = form.cleaned_data.get("new_document_type") or QualificationDocument.DOCUMENT_TYPE_OTHER
            for uploaded_file in new_files:
                new_document = QualificationDocument.objects.create(
                    profile=profile,
                    file=uploaded_file,
                    title=uploaded_file.name,
                    document_type=new_document_type,
                )
                selected_documents.append(new_document)

            if selected_documents:
                application.attached_documents.set(selected_documents)
                messages.success(
                    request,
                    f"Your application for '{job.title}' has been submitted for verification by the recruiter, "
                    f"along with {len(selected_documents)} attached document{'s' if len(selected_documents) != 1 else ''}.",
                )
            else:
                messages.success(request, f"Your application for '{job.title}' has been submitted successfully!")

            return redirect("job_detail", job_id=job.id)
    else:
        form = JobApplicationForm(profile=profile)

    return render(
        request,
        "jobs/apply.html",
        {
            "job": job,
            "profile": profile,
            "form": form,
            "already_applied": False,
            "document_slots_remaining": max(
                QualificationDocument.MAX_PER_PROFILE - profile.qualification_documents.count(), 0
            ),
            "document_max": QualificationDocument.MAX_PER_PROFILE,
        },
    )


@recruiter_required
def job_applicants(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    if job.posted_by != request.user:
        messages.error(request, "You do not have permission to view applicants for this job.")
        return redirect("recruiter_dashboard")

    applications = (
        job.applications.select_related("user", "user__profile")
        .prefetch_related("attached_documents")
        .order_by("-applied_at")
    )

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


@recruiter_required
def review_qualification_documents(request, application_id):
    """
    Lets a recruiter open the qualification documents an applicant chose
    to attach to this specific application (degree certificates,
    transcripts, certifications, ID, etc.) and review each one for
    authenticity as part of assessing that applicant.
    """
    application = get_object_or_404(
        Application.objects.select_related("user", "user__profile", "job"),
        id=application_id,
    )

    if application.job.posted_by != request.user:
        messages.error(request, "Permission denied.")
        return redirect("recruiter_dashboard")

    documents = application.attached_documents.all()
    verify_forms = {
        document.id: QualificationDocumentVerifyForm(instance=document)
        for document in documents
    }

    return render(
        request,
        "jobs/applicant_documents.html",
        {
            "application": application,
            "documents": documents,
            "verify_forms": verify_forms,
        },
    )


@recruiter_required
def update_document_verification(request, application_id, document_id):
    """
    Records a recruiter's verification decision (Pending / Verified /
    Rejected) for one qualification document attached to a specific
    application, after they have opened and reviewed the PDF for
    authenticity.
    """
    application = get_object_or_404(Application, id=application_id)

    if application.job.posted_by != request.user:
        messages.error(request, "Permission denied.")
        return redirect("recruiter_dashboard")

    document = get_object_or_404(application.attached_documents, id=document_id)

    if request.method == "POST":
        form = QualificationDocumentVerifyForm(request.POST, instance=document)
        if form.is_valid():
            document = form.save(commit=False)
            document.verified_by = request.user
            document.verified_at = timezone.now()
            document.save()
            messages.success(
                request,
                f"'{document.title or document.get_document_type_display()}' marked as {document.get_verification_status_display()}.",
            )

    return redirect("review_qualification_documents", application_id=application.id)


@seeker_required
def seeker_applications(request):
    """
    Display a list of all job applications submitted by the current job seeker.
    """
    applications = (
        Application.objects.filter(user=request.user)
        .select_related("job", "job__company", "job__category")
        .order_by("-applied_at")
    )
    return render(
        request,
        "jobs/my_applications.html",
        {"applications": applications},
    )
