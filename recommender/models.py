from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=20, blank=True)

    bio = models.TextField(blank=True)

    education = models.CharField(
        max_length=200,
        blank=True,
    )

    experience = models.PositiveIntegerField(
        default=0,
        help_text="Years of experience",
    )

    skills = models.TextField(
        blank=True,
        help_text="Separate skills with commas",
    )

    preferred_location = models.CharField(
        max_length=100,
        blank=True,
    )

    expected_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    resume = models.FileField(
        upload_to="resumes/",
        blank=True,
        null=True,
    )

    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_complete(self):
        return bool(
            self.skills.strip()
            and (self.education.strip() or self.bio.strip())
        )

    def skills_list(self):
        if not self.skills.strip():
            return []
        return [skill.strip() for skill in self.skills.split(",") if skill.strip()]

    def __str__(self):
        return self.user.username
    
class JobCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name 
    
class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)

    def __str__(self):
        return self.name       
    
class Job(models.Model):

    JOB_TYPES = [
        ("Full-Time", "Full-Time"),
        ("Part-Time", "Part-Time"),
        ("Internship", "Internship"),
        ("Contract", "Contract"),
        ("Remote", "Remote"),
    ]

    title = models.CharField(max_length=200)

    company = models.ForeignKey(
    Company,
    on_delete=models.CASCADE,
    related_name="jobs"
   )

    category = models.ForeignKey(
        JobCategory,
        on_delete=models.CASCADE,
        related_name="jobs"
    )

    description = models.TextField()

    requirements = models.TextField()

    required_skills = models.TextField(
        help_text="Separate skills using commas"
    )

    location = models.CharField(max_length=100)

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    experience_required = models.PositiveIntegerField()

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPES
    )

    deadline = models.DateField()

    posted_at = models.DateTimeField(auto_now_add=True)

    def skills_list(self):
        if not self.required_skills or not self.required_skills.strip():
            return []
        return [s.strip() for s in self.required_skills.split(",") if s.strip()]

    def __str__(self):
        return self.title 
    
class Application(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Reviewed", "Reviewed"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "job")

    def __str__(self):
        return f"{self.user.username} - {self.job.title}"
    
class SavedJob(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_jobs"
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="saved_by"
    )

    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "job")

    def __str__(self):
        return f"{self.user.username} saved {self.job.title}"           