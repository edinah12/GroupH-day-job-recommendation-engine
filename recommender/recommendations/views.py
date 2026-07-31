"""
Views for the recommendations sub-module.

All business logic is delegated to services.py.
This module is responsible only for HTTP handling and template rendering.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from ..models import Profile
from ..utils import get_user_profile
from .services import recommend_jobs


class RecommendedJobsView(LoginRequiredMixin, TemplateView):
    template_name = "recommendations/recommended_jobs.html"
    login_url = reverse_lazy("login")
    redirect_field_name = "next"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = get_user_profile(request.user)
            if profile.is_recruiter:
                messages.error(request, "Access restricted to job seekers only.")
                return redirect("recruiter_dashboard")
            try:
                _ = request.user.profile
            except Profile.DoesNotExist:
                return redirect(reverse_lazy("create_profile"))

        return super().dispatch(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def get_context_data(self, **kwargs) -> dict:
        """
        Build the template context.

        Calls the recommendation service and passes results to the template.
        The profile is fetched once and reused — no duplicate DB hits.
        """
        context = super().get_context_data(**kwargs)

        profile: Profile = self.request.user.profile

        context["profile"] = profile
        context["recommended_jobs"] = recommend_jobs(profile)

        return context
