"""
Recommendation service for the Job Recommendation Engine.

Business logic is intentionally kept here and never placed inside views.
The scoring algorithm is fully deterministic and weighted — no ML involved.

Scoring breakdown (max 100 points):
    Skills      50 pts  — percentage overlap of comma-separated skill sets
    Experience  20 pts  — binary: user meets or exceeds required years
    Location    10 pts  — binary: exact string match (case/whitespace insensitive)
    Category    10 pts  — binary: exact string match (case/whitespace insensitive)
    Salary      10 pts  — binary: job salary >= user's expected salary
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils import timezone

from ..models import Job, Profile

# ---------------------------------------------------------------------------
# Score weights — must sum to 100
# ---------------------------------------------------------------------------
SKILL_WEIGHT: float = 50.0
EXPERIENCE_WEIGHT: float = 20.0
LOCATION_WEIGHT: float = 10.0
CATEGORY_WEIGHT: float = 10.0
SALARY_WEIGHT: float = 10.0

# Minimum score a job must reach to be included in recommendations
DEFAULT_THRESHOLD: float = 40.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize(value: str) -> str:
    """Strip surrounding whitespace and lowercase a string."""
    return value.strip().lower()


def _parse_skills(raw: str) -> set[str]:
    """
    Split a comma-separated skill string into a normalised set.

    Handles extra whitespace and is case-insensitive.

    Example:
        "Python, Django , SQL" -> {"python", "django", "sql"}
    """
    if not raw or not raw.strip():
        return set()
    return {_normalize(skill) for skill in raw.split(",") if skill.strip()}


# ---------------------------------------------------------------------------
# Public scoring functions
# ---------------------------------------------------------------------------

def calculate_skill_score(profile: Profile, job: Job) -> float:
    """
    Calculate the skill-based match score (max 50 points).

    Formula:
        score = (number of matching skills / number of required skills) * 50

    Returns 0 if the job has no required skills listed.
    """
    user_skills: set[str] = _parse_skills(profile.skills or "")
    job_skills: set[str] = _parse_skills(job.required_skills or "")

    if not job_skills:
        return 0.0

    matched = 0
    for j_skill in job_skills:
        if any(u_skill == j_skill or u_skill in j_skill or j_skill in u_skill for u_skill in user_skills):
            matched += 1

    return round((matched / len(job_skills)) * SKILL_WEIGHT, 2)


def calculate_experience_score(profile: Profile, job: Job) -> float:
    """
    Calculate the experience-based match score (max 20 points).

    Binary rule:
        user.experience >= job.experience_required  -> 20 pts
        otherwise                                   ->  0 pts
    """
    if profile.experience >= job.experience_required:
        return EXPERIENCE_WEIGHT
    return 0.0


def calculate_location_score(profile: Profile, job: Job) -> float:
    """
    Calculate the location-based match score (max 10 points).

    Matches exact or partial location strings (case/whitespace insensitive).
    """
    if not profile.preferred_location or not job.location:
        return 0.0

    p_loc = _normalize(profile.preferred_location)
    j_loc = _normalize(job.location)

    if p_loc == j_loc or p_loc in j_loc or j_loc in p_loc:
        return LOCATION_WEIGHT
    return 0.0


def calculate_category_score(profile: Profile, job: Job) -> float:
    """
    Calculate the category-based match score (max 10 points).

    Matches exact or partial category names (case/whitespace insensitive).
    """
    if not profile.preferred_category or not job.category:
        return 0.0

    p_cat = _normalize(profile.preferred_category)
    j_cat = _normalize(job.category.name)

    if p_cat == j_cat or p_cat in j_cat or j_cat in p_cat:
        return CATEGORY_WEIGHT
    return 0.0


def calculate_salary_score(profile: Profile, job: Job) -> float:
    """
    Calculate the salary-based match score (max 10 points).

    Binary rule:
        job.salary >= user.expected_salary -> 10 pts
        otherwise                          ->  0 pts

    If the user has not set an expected salary (0 or None), returns 0.
    """
    expected: Decimal = Decimal(profile.expected_salary or 0)

    if expected <= 0:
        return 0.0

    if job.salary >= expected:
        return SALARY_WEIGHT
    return 0.0


def calculate_match_score(profile: Profile, job: Job) -> float:
    """
    Combine all weighted scoring rules into a final score out of 100.

    Args:
        profile: The authenticated user's Profile instance.
        job:     The Job being evaluated.

    Returns:
        A float between 0.0 and 100.0 (inclusive), rounded to 1 decimal place.
    """
    score: float = 0.0
    score += calculate_skill_score(profile, job)
    score += calculate_experience_score(profile, job)
    score += calculate_location_score(profile, job)
    score += calculate_category_score(profile, job)
    score += calculate_salary_score(profile, job)

    return round(min(score, 100.0), 1)


# ---------------------------------------------------------------------------
# Public recommendation function
# ---------------------------------------------------------------------------

def recommend_jobs(
    profile: Profile,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Return a sorted list of job recommendations for a given user profile.

    Only jobs whose deadline has not passed are considered (active jobs).
    Jobs scoring below ``threshold`` are excluded. If no jobs match at high threshold,
    fall back to a lower threshold so candidates receive options.

    Uses select_related to avoid N+1 queries on company and category lookups.
    """
    today = timezone.localdate()

    active_jobs = list(
        Job.objects
        .select_related("company", "category")
        .filter(deadline__gte=today)
    )

    scored_jobs = [
        {"job": job, "score": calculate_match_score(profile, job)}
        for job in active_jobs
    ]

    filtered = [item for item in scored_jobs if item["score"] >= threshold]

    # Fallback to lower threshold if strict threshold returns empty results
    if not filtered and scored_jobs:
        filtered = [item for item in scored_jobs if item["score"] > 0]

    return sorted(filtered, key=lambda item: item["score"], reverse=True)

