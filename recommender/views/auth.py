from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from recommender.forms import StyledAuthenticationForm, UserRegistrationForm
from recommender.utils import post_login_url, profile_setup_redirect


def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Complete your profile to get better job matches.")
            setup_redirect = profile_setup_redirect(user)
            if setup_redirect:
                return setup_redirect
            return redirect("home")
    else:
        form = UserRegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return post_login_url(self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Signed in as {self.request.user.username}.")
        return response
