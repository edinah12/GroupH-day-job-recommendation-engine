from django import forms
from django.core.exceptions import ValidationError

from recommender.models import Profile

MAX_RESUME_SIZE = 5 * 1024 * 1024
ALLOWED_RESUME_EXTENSIONS = (".pdf", ".doc", ".docx")
ALLOWED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def _validate_file_extension(value, allowed, label):
    if not value:
        return
    name = value.name.lower()
    if not any(name.endswith(ext) for ext in allowed):
        allowed_display = ", ".join(allowed)
        raise ValidationError(f"{label} must be one of: {allowed_display}.")


class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile

        fields = [
            "phone",
            "bio",
            "education",
            "experience",
            "skills",
            "preferred_location",
            "preferred_category",
            "expected_salary",
            "resume",
            "profile_picture",
        ]

        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Tell employers about yourself",
                }
            ),
            "skills": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Example: Python, Django, SQL",
                }
            ),
            "education": forms.TextInput(
                attrs={"placeholder": "e.g. BSc Computer Science"}
            ),
            "preferred_location": forms.TextInput(
                attrs={"placeholder": "City or Remote"}
            ),
            "phone": forms.TextInput(attrs={"placeholder": "+1 555 0100"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()
        self.fields["experience"].widget.attrs["min"] = 0

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and resume.size > MAX_RESUME_SIZE:
            raise ValidationError("Resume must be 5 MB or smaller.")
        _validate_file_extension(resume, ALLOWED_RESUME_EXTENSIONS, "Resume")
        return resume

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")
        _validate_file_extension(picture, ALLOWED_IMAGE_EXTENSIONS, "Profile picture")
        return picture


class RecruiterProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "company_name",
            "designation",
            "company_website",
            "phone",
            "bio",
            "profile_picture",
        ]
        widgets = {
            "company_name": forms.TextInput(attrs={"placeholder": "e.g. Acme Corp"}),
            "designation": forms.TextInput(attrs={"placeholder": "e.g. Senior Tech Recruiter"}),
            "company_website": forms.URLInput(attrs={"placeholder": "https://company.com"}),
            "phone": forms.TextInput(attrs={"placeholder": "+1 555 0100"}),
            "bio": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe your company or hiring scope",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")
        _validate_file_extension(picture, ALLOWED_IMAGE_EXTENSIONS, "Profile picture")
        return picture

