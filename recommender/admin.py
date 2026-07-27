from django.contrib import admin
from .models import (
    Profile,
    Company,
    JobCategory,
    Job,
    Application,
    SavedJob,
    JobView,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "experience", "preferred_location", "preferred_category", "expected_salary")
    list_filter = ("role", "preferred_category")
    search_fields = ("user__username", "user__email", "skills", "preferred_location")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "email", "website")
    search_fields = ("name", "location", "email")


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "category", "job_type", "location", "salary", "deadline", "posted_at")
    list_filter = ("category", "job_type", "posted_at")
    search_fields = ("title", "company__name", "required_skills", "location")
    ordering = ("-posted_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "user", "status", "applied_at")
    list_filter = ("status", "applied_at")
    search_fields = ("job__title", "user__username")


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "saved_at")
    search_fields = ("user__username", "job__title")


@admin.register(JobView)
class JobViewAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("user__username", "job__title")