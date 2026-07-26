from django.urls import include, path
from django.contrib.auth import views as auth_views

from .views.home import home
from .views.companies import company_list, company_detail
from .views.auth import register, CustomLoginView
from .views.profile import create_profile, edit_profile, view_profile
from .views.dashboard import dashboard, recruiter_dashboard, recruiter_jobs, seeker_dashboard
from .views.jobs import (
    job_list,
    job_detail,
    create_job,
    edit_job,
    delete_job,
    apply_job,
    job_applicants,
    update_application_status,
)

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("recruiter/dashboard/", recruiter_dashboard, name="recruiter_dashboard"),
    path("recruiter/jobs/", recruiter_jobs, name="recruiter_jobs"),
    path("my-applications/", seeker_dashboard, name="seeker_dashboard"),
    
    path("recommendations/", include("recommender.recommendations.urls")),

    path("register/", register, name="register"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/password-reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),

    path("jobs/", job_list, name="job_list"),
    path("jobs/create/", create_job, name="create_job"),
    path("jobs/<int:job_id>/", job_detail, name="job_detail"),
    path("jobs/<int:job_id>/edit/", edit_job, name="edit_job"),
    path("jobs/<int:job_id>/delete/", delete_job, name="delete_job"),
    path("jobs/<int:job_id>/apply/", apply_job, name="apply_job"),
    path("jobs/<int:job_id>/applicants/", job_applicants, name="job_applicants"),
    path("applications/<int:application_id>/status/", update_application_status, name="update_application_status"),

    path("profile/", view_profile, name="view_profile"),
    path("profile/edit/", edit_profile, name="edit_profile"),
    path("profile/create/", create_profile, name="create_profile"),

    path("companies/", company_list, name="company_list"),
    path("companies/<int:company_id>/", company_detail, name="company_detail"),
]
