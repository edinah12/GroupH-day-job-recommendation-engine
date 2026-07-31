from django import forms
from django.core.exceptions import ValidationError

from recommender.models import Profile, QualificationDocument

MAX_RESUME_SIZE = 5 * 1024 * 1024
ALLOWED_RESUME_EXTENSIONS = (".pdf", ".doc", ".docx")
ALLOWED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

MAX_QUALIFICATION_DOCUMENT_SIZE = 10 * 1024 * 1024
ALLOWED_QUALIFICATION_DOCUMENT_EXTENSIONS = (".pdf",)


def _validate_file_extension(value, allowed, label):
    if not value:
        return
    name = value.name.lower()
    if not any(name.endswith(ext) for ext in allowed):
        allowed_display = ", ".join(allowed)
        raise ValidationError(f"{label} must be one of: {allowed_display}.")


class MultipleFileInput(forms.ClearableFileInput):
    """A file input widget that accepts more than one file at once."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """
    A FileField that accepts and validates a list of uploaded files
    instead of a single one. Django's built-in FileField only supports
    one file per field, so this overrides clean() to run the normal
    per-file validation across every file the user selected.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if data in (None, "", []):
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [single_file_clean(item, initial) for item in data]


class ProfileForm(forms.ModelForm):

    qualification_documents = MultipleFileField(
        required=False,
        label="Qualification Documents",
        help_text=(
            "Attach your degree certificate, transcripts, professional certifications, "
            "or ID as PDF files. Recruiters will review these to verify your qualifications "
            "before assessing your applications. You can select multiple PDF files at once."
        ),
    )

    class Meta:
        model = Profile

        fields = [
            "phone",
            "bio",
            "education",
            "experience",
            "skills",
            "preferred_location",
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

    def clean_qualification_documents(self):
        files = self.cleaned_data.get("qualification_documents") or []
        for uploaded_file in files:
            if uploaded_file.size > MAX_QUALIFICATION_DOCUMENT_SIZE:
                raise ValidationError(
                    f"'{uploaded_file.name}' is too large. Each qualification document must be 10 MB or smaller."
                )
            _validate_file_extension(
                uploaded_file, ALLOWED_QUALIFICATION_DOCUMENT_EXTENSIONS, "Qualification documents"
            )
        if files and self.instance.pk:
            existing_count = self.instance.qualification_documents.count()
            if existing_count + len(files) > QualificationDocument.MAX_PER_PROFILE:
                remaining = max(QualificationDocument.MAX_PER_PROFILE - existing_count, 0)
                raise ValidationError(
                    f"You can have at most {QualificationDocument.MAX_PER_PROFILE} qualification documents "
                    f"in total. You have {existing_count} already, so you can add up to {remaining} more."
                )
        return files


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


class QualificationDocumentVerifyForm(forms.ModelForm):
    """Used by recruiters on the applicant document-review page to record
    their assessment of a single qualification document."""

    class Meta:
        model = QualificationDocument
        fields = ["verification_status", "verification_note"]
        widgets = {
            "verification_note": forms.TextInput(
                attrs={"placeholder": "Optional note (e.g. reason for rejection)"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            base_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = f"{existing} {base_class} form-control-sm".strip()

