from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from recommender.forms import ProfileForm, RecruiterProfileForm
from recommender.models import QualificationDocument
from recommender.utils import get_user_profile


@login_required
def view_profile(request):
    profile = get_user_profile(request.user)
    return render(
        request,
        "profile/detail.html",
        {"profile": profile, "document_max": QualificationDocument.MAX_PER_PROFILE},
    )


@login_required
def edit_profile(request):
    profile = get_user_profile(request.user)
    is_setup = not profile.is_complete
    FormClass = RecruiterProfileForm if profile.is_recruiter else ProfileForm

    if request.method == "POST":
        form = FormClass(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()

            # Seekers only: any PDFs attached via the "Qualification
            # Documents" field are stored as separate QualificationDocument
            # records on the profile, so they only need to be uploaded
            # once and are then available to every recruiter reviewing
            # this seeker's applications.
            uploaded_documents = form.cleaned_data.get("qualification_documents")
            if uploaded_documents:
                for uploaded_file in uploaded_documents:
                    QualificationDocument.objects.create(
                        profile=profile,
                        file=uploaded_file,
                        title=uploaded_file.name,
                    )

            if uploaded_documents:
                messages.success(
                    request,
                    "Your qualification documents have been added to your profile. "
                    "You can choose which ones to attach whenever you apply for a job.",
                )
            elif is_setup:
                if profile.is_recruiter:
                    messages.success(request, "Profile saved. You can now post jobs and manage applicants.")
                else:
                    messages.success(request, "Profile saved. You can now explore job recommendations.")
            else:
                messages.success(request, "Your profile has been updated.")
            return redirect("view_profile")
    else:
        form = FormClass(instance=profile)

    template = "profile/setup.html" if is_setup else "profile/edit.html"
    return render(
        request,
        template,
        {
            "form": form,
            "profile": profile,
            "is_setup": is_setup,
            "document_slots_remaining": max(
                QualificationDocument.MAX_PER_PROFILE - profile.qualification_documents.count(), 0
            ) if profile.is_seeker else 0,
        },
    )


@login_required
def create_profile(request):
    return redirect("edit_profile")

