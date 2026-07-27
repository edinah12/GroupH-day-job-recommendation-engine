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

Preference boost (up to 15 pts additive, capped so total never exceeds 100):
    Saved-job category match    +8 pts  (mutually exclusive with below)
    Applied-job category match  +5 pts
    Viewed-job category match   +2 pts
    Interest skill overlap      +7 pts max (proportional)
    ─────────────────────────────────────
    Boost subtotal              15 pts max
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils import timezone

from ..models import Application, Job, JobView, Profile, SavedJob

# ---------------------------------------------------------------------------
# Score weights — must sum to 100
# ---------------------------------------------------------------------------
SKILL_WEIGHT: float = 50.0
EXPERIENCE_WEIGHT: float = 20.0
LOCATION_WEIGHT: float = 10.0
CATEGORY_WEIGHT: float = 10.0
SALARY_WEIGHT: float = 10.0

# Preference boost weights (additive, capped at PREFERENCE_MAX)
PREFERENCE_MAX: float = 15.0
_PREF_CAT_SAVED: float = 8.0
_PREF_CAT_APPLIED: float = 5.0
_PREF_CAT_VIEWED: float = 2.0
_PREF_SKILL_MAX: float = 7.0

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


# ---------------------------------------------------------------------------
# Preference boost (user interaction history)
# ---------------------------------------------------------------------------

def _build_preference_context(profile: Profile) -> dict[str, Any]:
    """
    Pre-compute the user's interaction history in exactly 3 DB queries.

    This is called once per ``recommend_jobs`` invocation and then passed
    through to ``calculate_preference_boost`` for every job, so no extra
    queries are fired inside the scoring loop.

    Returns:
        A dict with the following keys:
            saved_categories  (set[int])  — category IDs of saved jobs
            applied_categories(set[int])  — category IDs of applied jobs
            viewed_categories (set[int])  — category IDs of recently viewed jobs
            interest_skills   (set[str])  — normalised skills from saved + applied jobs
    """
    user = profile.user

    # 1 — Saved jobs: category IDs + required skills
    saved_qs = (
        SavedJob.objects
        .filter(user=user)
        .values_list("job__category_id", "job__required_skills")
    )
    saved_categories: set[int] = set()
    saved_skills: set[str] = set()
    for cat_id, skills in saved_qs:
        if cat_id:
            saved_categories.add(cat_id)
        saved_skills |= _parse_skills(skills or "")

    # 2 — Applied jobs: category IDs + required skills
    applied_qs = (
        Application.objects
        .filter(user=user)
        .values_list("job__category_id", "job__required_skills")
    )
    applied_categories: set[int] = set()
    applied_skills: set[str] = set()
    for cat_id, skills in applied_qs:
        if cat_id:
            applied_categories.add(cat_id)
        applied_skills |= _parse_skills(skills or "")

    # 3 — Recently viewed jobs: category IDs only (last 20 unique views)
    viewed_categories: set[int] = set(
        filter(
            None,
            JobView.objects
            .filter(user=user)
            .order_by("-viewed_at")
            .values_list("job__category_id", flat=True)[:20],
        )
    )

    return {
        "saved_categories": saved_categories,
        "applied_categories": applied_categories,
        "viewed_categories": viewed_categories,
        "interest_skills": saved_skills | applied_skills,
    }


def calculate_preference_boost(job: Job, context: dict[str, Any]) -> float:
    """
    Calculate a preference-based score boost (max 15 points).

    Uses the pre-built ``context`` dict from ``_build_preference_context``
    so no additional DB queries are fired per job.

    Boost logic:
        Category boost (mutually exclusive, highest tier wins):
            Saved-job category match    +8 pts
            Applied-job category match  +5 pts
            Viewed-job category match   +2 pts

        Skill boost (proportional, up to +7 pts):
            % overlap between job skills and user's saved/applied skills

    The total boost is capped at PREFERENCE_MAX (15 pts).
    """
    boost: float = 0.0

    # ── Category boost ───────────────────────────────────────────────
    job_cat_id: int | None = job.category_id
    if job_cat_id:
        if job_cat_id in context["saved_categories"]:
            boost += _PREF_CAT_SAVED
        elif job_cat_id in context["applied_categories"]:
            boost += _PREF_CAT_APPLIED
        elif job_cat_id in context["viewed_categories"]:
            boost += _PREF_CAT_VIEWED

    # ── Skill boost ──────────────────────────────────────────────────
    job_skills: set[str] = _parse_skills(job.required_skills or "")
    interest_skills: set[str] = context["interest_skills"]
    if job_skills and interest_skills:
        matched = sum(
            1
            for s in job_skills
            if any(s == i or s in i or i in s for i in interest_skills)
        )
        boost += round((matched / len(job_skills)) * _PREF_SKILL_MAX, 2)

    return min(boost, PREFERENCE_MAX)


def calculate_match_score(
    profile: Profile,
    job: Job,
    preference_context: dict[str, Any] | None = None,
) -> float:
    """
    Combine all weighted scoring rules into a final score out of 100.

    Args:
        profile:            The authenticated user's Profile instance.
        job:                The Job being evaluated.
        preference_context: Optional pre-built dict from
                            ``_build_preference_context``.  When supplied,
                            a preference boost (up to 15 pts) is added.
                            Passing ``None`` keeps the original behaviour
                            (no boost), so existing callers and tests are
                            unaffected.

    Returns:
        A float between 0.0 and 100.0 (inclusive), rounded to 1 decimal place.
    """
    score: float = 0.0
    score += calculate_skill_score(profile, job)
    score += calculate_experience_score(profile, job)
    score += calculate_location_score(profile, job)
    score += calculate_category_score(profile, job)
    score += calculate_salary_score(profile, job)

    if preference_context is not None:
        score += calculate_preference_boost(job, preference_context)

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
    Jobs scoring below ``threshold`` are excluded. If no jobs match at high
    threshold, fall back to a lower threshold so candidates receive options.

    Preference context is pre-built in 3 queries before the scoring loop,
    so there are no N+1 DB queries regardless of how many jobs exist.

    Uses select_related to avoid N+1 queries on company and category lookups.
    """
    today = timezone.localdate()

    active_jobs = list(
        Job.objects
        .select_related("company", "category")
        .filter(deadline__gte=today)
    )

    # Pre-build once; reused for every job scored below (3 queries total)
    pref_context = _build_preference_context(profile)

    scored_jobs = [
        {
            "job": job,
            "score": calculate_match_score(profile, job, pref_context),
        }
        for job in active_jobs
    ]

    filtered = [item for item in scored_jobs if item["score"] >= threshold]

    # Fallback to lower threshold if strict threshold returns empty results
    if not filtered and scored_jobs:
        filtered = [item for item in scored_jobs if item["score"] > 0]

    return sorted(filtered, key=lambda item: item["score"], reverse=True)
