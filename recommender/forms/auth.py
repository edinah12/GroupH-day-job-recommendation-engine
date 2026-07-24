from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"


from recommender.models import Profile


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"placeholder": "you@example.com", "autocomplete": "email"}
        ),
    )
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        initial=Profile.ROLE_SEEKER,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="I am joining as a:",
    )

    class Meta:
        model = User
        fields = ("username", "email", "role", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"placeholder": "Choose a username", "autocomplete": "username"}
        )
        self.fields["password1"].widget.attrs.update({"autocomplete": "new-password"})
        self.fields["password2"].widget.attrs.update({"autocomplete": "new-password"})
        for name, field in self.fields.items():
            if name != "role":
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} form-control".strip()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            role = self.cleaned_data.get("role", Profile.ROLE_SEEKER)
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
        return user
