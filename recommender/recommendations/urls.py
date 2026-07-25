from django.urls import path

from .views import RecommendedJobsView

urlpatterns = [
    path("", RecommendedJobsView.as_view(), name="recommended_jobs"),
]
