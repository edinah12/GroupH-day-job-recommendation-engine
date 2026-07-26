from django import forms
from recommender.models import Job, Company, JobCategory, Application


class JobSearchForm(forms.Form):
    """
    Handles the "Search & Filtering" controls on the public job listings page.

    Every field is optional (required=False) since this form is bound to
    GET parameters and any subset of filters may be supplied. Validation
    here keeps bad/garbage input (e.g. a non-numeric salary) from ever
    reaching the database query in the view.
    """

    SORT_CHOICES = [
        ("-posted_at", "Newest First"),
        ("posted_at", "Oldest First"),
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
            "salary": forms.NumberInput(attrs={"placeholder": "Salary in USD (e.g. 85000)"}),
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


class JobApplicationForm(forms.ModelForm):
    resume = forms.FileField(
        required=False,
        label="Upload/Update Resume (Optional)",
        help_text="Supported formats: PDF, DOC, DOCX",
        widget=forms.FileInput(attrs={"class": "form-control"})
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

