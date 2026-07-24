from django.test import TestCase
from django.contrib.auth.models import User
from recommender.models import Profile, Job, JobCategory, Company, Application


class RoleBasedAccessTest(TestCase):
    def setUp(self):
        self.category = JobCategory.objects.create(name="Engineering", description="Software & Tech")
        
        # Create recruiter
        self.recruiter_user = User.objects.create_user(username="recruiter1", email="recruiter@example.com", password="password123")
        self.recruiter_profile = Profile.objects.get_or_create(user=self.recruiter_user)[0]
        self.recruiter_profile.role = Profile.ROLE_RECRUITER
        self.recruiter_profile.company_name = "TechCorp"
        self.recruiter_profile.designation = "HR Director"
        self.recruiter_profile.save()

        # Create job seeker
        self.seeker_user = User.objects.create_user(username="seeker1", email="seeker@example.com", password="password123")
        self.seeker_profile = Profile.objects.get_or_create(user=self.seeker_user)[0]
        self.seeker_profile.role = Profile.ROLE_SEEKER
        self.seeker_profile.skills = "Python, Django"
        self.seeker_profile.bio = "Backend developer looking for Django roles."
        self.seeker_profile.save()

    def test_profile_role_properties(self):
        self.assertTrue(self.recruiter_profile.is_recruiter)
        self.assertFalse(self.recruiter_profile.is_seeker)
        self.assertTrue(self.recruiter_profile.is_complete)

        self.assertTrue(self.seeker_profile.is_seeker)
        self.assertFalse(self.seeker_profile.is_recruiter)
        self.assertTrue(self.seeker_profile.is_complete)

    def test_recruiter_post_job_and_reflection_for_seeker(self):
        self.client.login(username="recruiter1", password="password123")
        response = self.client.post("/jobs/create/", {
            "title": "Senior Python Engineer",
            "company_name": "TechCorp",
            "category": self.category.id,
            "job_type": "Full-Time",
            "location": "Remote",
            "salary": "95000",
            "experience_required": 3,
            "deadline": "2026-12-31",
            "required_skills": "Python, Django, PostgreSQL",
            "description": "Awesome backend opportunity.",
            "requirements": "3+ years experience with Django.",
        })
        self.assertEqual(response.status_code, 302)

        # Check job created and linked to recruiter
        job = Job.objects.get(title="Senior Python Engineer")
        self.assertEqual(job.posted_by, self.recruiter_user)

        # Check job reflects on home feed
        self.client.login(username="seeker1", password="password123")
        home_response = self.client.get("/")
        self.assertContains(home_response, "Senior Python Engineer")
        self.assertContains(home_response, "TechCorp")

    def test_job_application_flow(self):
        # Recruiter creates job
        company = Company.objects.create(name="TechCorp", location="Remote")
        job = Job.objects.create(
            title="Frontend Dev",
            company=company,
            category=self.category,
            posted_by=self.recruiter_user,
            description="React job",
            requirements="React experience",
            required_skills="React, JS",
            location="Remote",
            salary=80000,
            experience_required=2,
            job_type="Full-Time",
            deadline="2026-12-31"
        )

        # Job seeker applies
        self.client.login(username="seeker1", password="password123")
        apply_response = self.client.post(f"/jobs/{job.id}/apply/")
        self.assertEqual(apply_response.status_code, 302)
        self.assertTrue(Application.objects.filter(user=self.seeker_user, job=job).exists())

        # Recruiter checks applicants
        self.client.login(username="recruiter1", password="password123")
        applicants_response = self.client.get(f"/jobs/{job.id}/applicants/")
        self.assertContains(applicants_response, "seeker1")
