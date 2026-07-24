from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="Password123!",
            email="test@example.com"
        )

    def test_welcome_page_unauthenticated(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "welcome.html")
        self.assertContains(response, "Find Your Dream Job")

    def test_home_page_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, "Welcome back, testuser")

    def test_register_page_get(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")
        # Ensure bulky Django default help text is NOT present
        self.assertNotContains(response, "Your password can't be too similar")

    def test_job_detail_view(self):
        from recommender.models import Company, JobCategory, Job
        import datetime
        company = Company.objects.create(name="Test Co", location="Kampala")
        category = JobCategory.objects.create(name="Tech")
        job = Job.objects.create(
            title="Python Dev",
            company=company,
            category=category,
            description="Write python code",
            requirements="CS degree",
            required_skills="Python, Django",
            location="Kampala",
            salary=1000.00,
            experience_required=1,
            job_type="Full-Time",
            deadline=datetime.date.today()
        )
        response = self.client.get(reverse("job_detail", args=[job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "jobs/detail.html")
        self.assertContains(response, "Python Dev")
        self.assertContains(response, "Test Co")
