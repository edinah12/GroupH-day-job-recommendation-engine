from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from recommender.forms import ProfileForm


@login_required
def create_profile(request):

    if hasattr(request.user, "profile"):
        return redirect("home")


    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            profile = form.save(commit=False)

            profile.user = request.user

            profile.save()

            return redirect("home")

    else:

        form = ProfileForm()


    return render(
        request,
        "profile/create.html",
        {
            "form": form
        }
    )