from django import forms
from recommender.models import Job, Company, JobCategory, Application, QualificationDocument
from recommender.forms.profile import (
    MultipleFileField,
    MAX_QUALIFICATION_DOCUMENT_SIZE,
    ALLOWED_QUALIFICATION_DOCUMENT_EXTENSIONS,
    _validate_file_extension,
)
from django.core.exceptions import ValidationError


class JobSearchForm(forms.Form):
    """
    Handles the "Search & Filtering" controls on the public job listings page.

    Every field is optional (required=False) since this form is bound to
    GET parameters and any subset of filters may be supplied. Validation
    here keeps bad/garbage input (e.g. a non-numeric salary) from ever
    reaching the database query in the view.
    """

    SORT_CHOICES = [
        ("-posted_at", "Newest to Oldest"),
        ("posted_at", "Oldest to Newest"),
        ("-salary", "Salary: High to Low"),
        ("salary", "Salary: Low to High"),
        ("deadline", "Deadline: Soonest First"),
    ]

    search = forms.CharField(
        required=False,
        label="Keyword",
        widget=forms.TextInput(attrs={"placeholder": "Search title, skills, description..."}),
    )
    location = forms.CharField(
        required=False,
        label="Location",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Kampala, Remote..."}),
    )
    company = forms.ModelChoiceField(
        required=False,
        label="Company",
        queryset=Company.objects.order_by("name"),
        empty_label="All Companies",
    )
    category = forms.ModelChoiceField(
        required=False,
        label="Category",
        queryset=JobCategory.objects.order_by("name"),
        empty_label="All Categories",
    )
    job_type = forms.ChoiceField(
        required=False,
        label="Job Type",
        choices=[("", "All Job Types")] + list(Job.JOB_TYPES),
    )
    min_salary = forms.DecimalField(
        required=False,
        label="Min Pay",
        min_value=0,
        widget=forms.NumberInput(attrs={"placeholder": "Min Salary"}),
    )
    max_salary = forms.DecimalField(
        required=False,
        label="Max Pay",
        min_value=0,
        widget=forms.NumberInput(attrs={"placeholder": "Max Salary"}),
    )
    sort = forms.ChoiceField(
        required=False,
        label="Sort By",
        choices=SORT_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            base_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = f"{existing} {base_class} border-0 bg-light py-2".strip()

    def clean(self):
        cleaned_data = super().clean()
        min_salary = cleaned_data.get("min_salary")
        max_salary = cleaned_data.get("max_salary")

        if min_salary is not None and max_salary is not None and min_salary > max_salary:
            # Swap silently rather than erroring out, so users get sane
            # results even if they enter the range backwards.
            cleaned_data["min_salary"], cleaned_data["max_salary"] = max_salary, min_salary

        return cleaned_data



class JobForm(forms.ModelForm):
    company_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Company Name (e.g. Acme Inc.)"}),
        label="Company Name",
    )

    class Meta:
        model = Job
        fields = [
            "title",
            "category",
            "job_type",
            "location",
            "salary",
            "experience_required",
            "deadline",
            "description",
            "requirements",
            "required_skills",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Job Title (e.g. Software Engineer)"}),
            "location": forms.TextInput(attrs={"placeholder": "Location (e.g. Remote, New York, NY)"}),
            "salary": forms.NumberInput(attrs={"placeholder": "Salary in UGX (e.g. 1500000)"}),
            "experience_required": forms.NumberInput(attrs={"placeholder": "Required Experience (Years)", "min": 0}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": "Detailed job description..."}),
            "requirements": forms.Textarea(attrs={"rows": 4, "placeholder": "Job requirements and qualifications..."}),
            "required_skills": forms.Textarea(attrs={"rows": 3, "placeholder": "e.g. Python, Django, PostgreSQL (comma separated)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.company:
            self.fields["company_name"].initial = self.instance.company.name

        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} form-control".strip()

    def save(self, commit=True, user=None):
        job = super().save(commit=False)
        company_name_str = self.cleaned_data.get("company_name", "").strip()
        company, _ = Company.objects.get_or_create(
            name=company_name_str,
            defaults={"location": job.location or "Not specified"}
        )
        job.company = company
        if user and not job.posted_by:
            job.posted_by = user

        if commit:
            job.save()
        return job


class QualificationDocumentChoiceField(forms.ModelMultipleChoiceField):
    """
    Shows each archived document's title (or type, if no title was set)
    plus its upload date as the checkbox label, so a seeker can actually
    tell their documents apart - the model's default __str__ includes the
    username and would render identically for every checkbox.
    """

    def label_from_instance(self, obj):
        name = obj.title or obj.get_document_type_display()
        return f"{name} ({obj.get_document_type_display()}, uploaded {obj.uploaded_at:%b %d, %Y})"


class JobApplicationForm(forms.ModelForm):
    resume = forms.FileField(
        required=False,
        label="Upload/Update Resume (Optional)",
        help_text="Supported formats: PDF, DOC, DOCX",
        widget=forms.FileInput(attrs={"class": "form-control"})
    )

    attached_documents = QualificationDocumentChoiceField(
        required=False,
        label="Attach Documents From Your Archive",
        queryset=QualificationDocument.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose which of your uploaded qualification documents to submit with this application.",
    )

    new_document_type = forms.ChoiceField(
        required=False,
        label="New Document Type",
        choices=[("", "Select a type...")] + QualificationDocument.DOCUMENT_TYPE_CHOICES,
    )

    new_documents = MultipleFileField(
        required=False,
        label="Add a New Document (e.g. an award or certificate)",
        help_text="Don't have it saved yet? Attach new PDF(s) here - they'll be added to your archive and to this application.",
    )

    class Meta:
        model = Application
        fields = ["cover_letter"]
        widgets = {
            "cover_letter": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": "form-control",
                    "placeholder": "Write a brief cover letter or note to the recruiter explaining why you are a good fit for this role...",
                }
            ),
        }

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        if profile is not None:
            self.fields["attached_documents"].queryset = profile.qualification_documents.all()

    def clean_new_documents(self):
        files = self.cleaned_data.get("new_documents") or []
        for uploaded_file in files:
            if uploaded_file.size > MAX_QUALIFICATION_DOCUMENT_SIZE:
                raise ValidationError(
                    f"'{uploaded_file.name}' is too large. Each qualification document must be 10 MB or smaller."
                )
            _validate_file_extension(
                uploaded_file, ALLOWED_QUALIFICATION_DOCUMENT_EXTENSIONS, "Qualification documents"
            )
        return files

    def clean(self):
        cleaned_data = super().clean()
        new_files = cleaned_data.get("new_documents") or []
        if new_files and self.profile is not None:
            existing_count = self.profile.qualification_documents.count()
            if existing_count + len(new_files) > QualificationDocument.MAX_PER_PROFILE:
                remaining = max(QualificationDocument.MAX_PER_PROFILE - existing_count, 0)
                self.add_error(
                    "new_documents",
                    f"You can have at most {QualificationDocument.MAX_PER_PROFILE} qualification documents "
                    f"in total. You have {existing_count} already, so you can add up to {remaining} more.",
                )
        return cleaned_data
