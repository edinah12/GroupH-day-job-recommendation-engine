from django import forms
from recommender.models import Job, Company, JobCategory, Application


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

