from django.urls import include, path

from .views.home import home
from .views.jobs import job_detail
from .views.auth import register
from .views.profile import create_profile
from .views.dashboard import dashboard

from django.contrib.auth import views as auth_views


urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("recommendations/", include("recommender.recommendations.urls")),

    path(
        "register/",
        register,
        name="register"
    ),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html"
        ),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    path(
        "jobs/<int:job_id>/",
        job_detail,
        name="job_detail",
    ),

    path(
        "profile/create/",
        create_profile,
        name="create_profile"
    ),
]
