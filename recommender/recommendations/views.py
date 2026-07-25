"""
Views for the recommendations sub-module.

All business logic is delegated to services.py.
This module is responsible only for HTTP handling and template rendering.
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from ..models import Profile
from .services import recommend_jobs


class RecommendedJobsView(LoginRequiredMixin, TemplateView):
    """
    Display personalised job recommendations for the authenticated user.

    Access control:
        - Unauthenticated users are redirected to the login page.
        - Authenticated users without a profile are redirected to the
          profile creation page so they can supply the data required
          by the scoring engine.

    Template context:
        recommended_jobs (list[dict]):
            Each entry has the shape {"job": Job, "score": float},
            sorted by score descending, filtered to scores >= 40.
        profile (Profile):
            The current user's profile, exposed so the template can
            display personalisation hints if needed.
    """

    template_name = "recommendations/recommended_jobs.html"
    login_url = reverse_lazy("login")
    redirect_field_name = "next"

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, request, *args, **kwargs):
        """
        Redirect to profile creation if the user has no profile yet.

        Using a try/except on Profile.DoesNotExist is safer than hasattr()
        because it correctly handles edge-cases where the related object
        descriptor exists but the underlying row has been deleted.
        """
        if request.user.is_authenticated:
            try:
                # Access the reverse OneToOne relation to verify existence.
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
