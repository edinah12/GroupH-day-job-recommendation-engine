from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from recommender.models import Company, Job, JobCategory, Profile
from recommender.recommendations.services import (
    calculate_match_score,
    calculate_skill_score,
    recommend_jobs,
)


class RecommendationServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="candidate",
            password="strong-password",
        )

        self.profile = Profile.objects.create(
            user=self.user,
            experience=3,
            skills="Python, Django, SQL",
            preferred_location="Kampala",
            preferred_category="Engineering",
            expected_salary=Decimal("2000000"),
        )

        self.company = Company.objects.create(
            name="Acme Corp",
            location="Kampala",
        )

        self.category = JobCategory.objects.create(
            name="Engineering",
        )

    def test_calculate_skill_score_computes_matching_percentage(self):
        job = Job.objects.create(
            title="Backend Engineer",
            company=self.company,
            category=self.category,
            description="Build services",
            requirements="",
            required_skills="Python, Django, Git",
            location="Kampala",
            salary=Decimal("2500000"),
            experience_required=2,
            job_type="Full-Time",
            deadline="2099-12-31",
        )

        score = calculate_skill_score(self.profile, job)

        self.assertEqual(score, 33.33333333333333)

    def test_calculate_match_score_gives_full_points_for_match(self):
        job = Job.objects.create(
            title="Backend Engineer",
            company=self.company,
            category=self.category,
            description="Build services",
            requirements="",
            required_skills="Python, Django, Git",
            location="Kampala",
            salary=Decimal("2500000"),
            experience_required=2,
            job_type="Full-Time",
            deadline="2099-12-31",
        )

        score = calculate_match_score(self.profile, job)

        self.assertAlmostEqual(score, 63.3, places=1)

    def test_recommend_jobs_filters_below_threshold_and_sorts_results(self):
        low_score_job = Job.objects.create(
            title="Support Technician",
            company=self.company,
            category=self.category,
            description="Help customers",
            requirements="",
            required_skills="Windows, Helpdesk",
            location="Nairobi",
            salary=Decimal("1500000"),
            experience_required=5,
            job_type="Full-Time",
            deadline="2099-12-31",
        )

        strong_job = Job.objects.create(
            title="Senior Backend Engineer",
            company=self.company,
            category=self.category,
            description="Build services",
            requirements="",
            required_skills="Python, Django, SQL",
            location="Kampala",
            salary=Decimal("3000000"),
            experience_required=2,
            job_type="Full-Time",
            deadline="2099-12-31",
        )

        recommended = recommend_jobs(self.profile)

        self.assertEqual(len(recommended), 1)
        self.assertEqual(recommended[0]["job"], strong_job)
        self.assertGreater(recommended[0]["score"], 80)


class RecommendedJobsViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="candidate",
            password="strong-password",
        )

        self.profile = Profile.objects.create(
            user=self.user,
            experience=3,
            skills="Python, Django, SQL",
            preferred_location="Kampala",
            preferred_category="Engineering",
            expected_salary=Decimal("2000000"),
        )

    def test_recommendations_page_requires_login(self):
        response = self.client.get(reverse("recommended_jobs"))

        self.assertEqual(response.status_code, 302)

    def test_recommendations_page_renders_for_authenticated_user(self):
        self.client.login(username="candidate", password="strong-password")
        response = self.client.get(reverse("recommended_jobs"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recommendations/recommended_jobs.html")

    def test_home_page_exposes_recommended_jobs_for_profiled_user(self):
        Job.objects.create(
            title="Backend Engineer",
            company=self.company,
            category=self.category,
            description="Build services",
            requirements="",
            required_skills="Python, Django, SQL",
            location="Kampala",
            salary=Decimal("3000000"),
            experience_required=2,
            job_type="Full-Time",
            deadline="2099-12-31",
        )

        self.client.login(username="candidate", password="strong-password")
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("recommended_jobs", response.context)
        self.assertEqual(len(response.context["recommended_jobs"]), 1)
