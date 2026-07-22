from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..models import Job


@login_required
def home(request):
    jobs = Job.objects.all()

    return render(
        request,
        "home.html",
        {
            "jobs": jobs
        }
    )