from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_SEEKER = "seeker"
    ROLE_RECRUITER = "recruiter"
    ROLE_CHOICES = [
        (ROLE_SEEKER, "Job Seeker"),
        (ROLE_RECRUITER, "Recruiter"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_SEEKER,
        db_index=True,
    )

    company_name = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=100, blank=True, help_text="e.g. Hiring Manager, Technical Recruiter")
    company_website = models.URLField(blank=True)

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
        db_index=True,
    )

    preferred_category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
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

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["preferred_location", "preferred_category"]),
        ]

    @property
    def is_recruiter(self):
        return self.role == self.ROLE_RECRUITER

    @property
    def is_seeker(self):
        return self.role == self.ROLE_SEEKER

    @property
    def is_complete(self):
        if self.is_recruiter:
            return bool(self.company_name.strip())
        return bool(
            self.skills.strip()
            and (self.education.strip() or self.bio.strip())
        )

    def skills_list(self):
        if not self.skills.strip():
            return []
        return [skill.strip() for skill in self.skills.split(",") if skill.strip()]

    def qualification_documents_summary(self):
        """
        Small counts dict used by the applicants list to show, at a glance,
        how many of a seeker's attached qualification documents are
        pending / verified / rejected, without a recruiter having to open
        the full review page first.
        """
        docs = self.qualification_documents.all()
        return {
            "total": len(docs),
            "pending": sum(1 for d in docs if d.verification_status == QualificationDocument.VERIFICATION_PENDING),
            "verified": sum(1 for d in docs if d.verification_status == QualificationDocument.VERIFICATION_VERIFIED),
            "rejected": sum(1 for d in docs if d.verification_status == QualificationDocument.VERIFICATION_REJECTED),
        }

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
class JobCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name 
    
class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, db_index=True)
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

    posted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posted_jobs",
        null=True,
        blank=True,
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

    location = models.CharField(max_length=100, db_index=True)

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_index=True,
    )

    experience_required = models.PositiveIntegerField(db_index=True)

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPES,
        db_index=True,
    )

    deadline = models.DateField()

    posted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["location", "category"]),
            models.Index(fields=["job_type", "salary"]),
            models.Index(fields=["-posted_at"]),
        ]

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
        default="Pending",
        db_index=True,
    )

    cover_letter = models.TextField(blank=True)

    attached_documents = models.ManyToManyField(
        "QualificationDocument",
        blank=True,
        related_name="applications",
        help_text="Qualification documents the applicant chose to submit with this specific application.",
    )

    applied_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("user", "job")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-applied_at"]),
        ]

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

    saved_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("user", "job")
        indexes = [
            models.Index(fields=["-saved_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} saved {self.job.title}"


class JobView(models.Model):
    """
    Records the first time a logged-in user views a job detail page.

    Only the *first* view is stored (unique_together enforces this),
    so the table stays small and queries remain fast.  Anonymous views
    are never recorded.

    Used by the recommendation engine to provide a small preference
    boost toward jobs in the same category / with similar skills as
    previously viewed jobs.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="job_views",
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="views",
    )

    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "job")
        ordering = ["-viewed_at"]

    def __str__(self) -> str:
        return f"{self.user.username} viewed {self.job.title}"


class QualificationDocument(models.Model):
    """
    A PDF document (degree certificate, transcript, professional
    certification, ID, etc.) a job seeker attaches to their profile so
    recruiters can review it for authenticity when assessing an applicant.

    Stored once on the seeker's profile - not per job application - so a
    seeker only has to upload each document a single time. For any given
    application, the seeker then chooses which of these archived
    documents (plus optionally any newly added ones) to submit for that
    specific job - see Application.attached_documents.
    """

    MAX_PER_PROFILE = 10

    DOCUMENT_TYPE_DEGREE = "degree"
    DOCUMENT_TYPE_TRANSCRIPT = "transcript"
    DOCUMENT_TYPE_CERTIFICATION = "certification"
    DOCUMENT_TYPE_ID = "id"
    DOCUMENT_TYPE_OTHER = "other"
    DOCUMENT_TYPE_CHOICES = [
        (DOCUMENT_TYPE_DEGREE, "Degree Certificate"),
        (DOCUMENT_TYPE_TRANSCRIPT, "Academic Transcript"),
        (DOCUMENT_TYPE_CERTIFICATION, "Professional Certification"),
        (DOCUMENT_TYPE_ID, "National ID / Passport"),
        (DOCUMENT_TYPE_OTHER, "Other"),
    ]

    VERIFICATION_PENDING = "pending"
    VERIFICATION_VERIFIED = "verified"
    VERIFICATION_REJECTED = "rejected"
    VERIFICATION_CHOICES = [
        (VERIFICATION_PENDING, "Pending Review"),
        (VERIFICATION_VERIFIED, "Verified"),
        (VERIFICATION_REJECTED, "Rejected"),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="qualification_documents",
    )

    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default=DOCUMENT_TYPE_OTHER,
    )

    title = models.CharField(
        max_length=150,
        blank=True,
        help_text="Optional label, e.g. 'BSc Computer Science Degree'",
    )

    file = models.FileField(upload_to="qualification_documents/%Y/%m/")

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_CHOICES,
        default=VERIFICATION_PENDING,
        db_index=True,
    )

    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_qualification_documents",
        help_text="Recruiter who last reviewed this document.",
    )

    verification_note = models.TextField(blank=True)

    verified_at = models.DateTimeField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["profile", "verification_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.profile.user.username} - {self.get_document_type_display()}"
