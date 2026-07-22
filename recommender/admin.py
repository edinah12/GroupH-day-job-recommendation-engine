from django.contrib import admin
from .models import (
    Profile,
    Company,
    JobCategory,
    Job,
    Application,
    SavedJob,
)

admin.site.register(Profile)
admin.site.register(Company)
admin.site.register(JobCategory)
admin.site.register(Job)
admin.site.register(Application)
admin.site.register(SavedJob)