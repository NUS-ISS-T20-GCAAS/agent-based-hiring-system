"""
Worker utility functions for screening
Provides heuristic fallback and result normalization
"""

from app.config import QUALIFICATION_THRESHOLD


KNOWN_SKILL_KEYWORDS = (
    "api design",
    "ci/cd",
    "python",
    "fastapi",
    "django",
    "flask",
    "sql",
    "postgresql",
    "mysql",
    "redis",
    "aws",
    "docker",
    "kubernetes",
    "testing",
    "javascript",
    "typescript",
    "react",
    "git",
)


def _normalize_skill_list(skills: list | None) -> list[str]:
    if not isinstance(skills, list):
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for skill in skills:
        if not isinstance(skill, str):
            continue
        cleaned = " ".join(skill.strip().lower().split())
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _extract_skill_keywords(text: str) -> list[str]:
    lower_text = (text or "").lower()
    return [skill for skill in KNOWN_SKILL_KEYWORDS if skill in lower_text]


def heuristic_screen_candidate(
    *, 
    parsed_resume: dict, 
    job_description: str,
    job_requirements: dict = None
) -> dict:
    """
    Rule-based screening fallback when LLM is unavailable
    
    Algorithm:
    1. Extract candidate skills and normalize to lowercase
    2. Extract required skills from job description and requirements
    3. Calculate skill match ratio
    4. Factor in years of experience
    5. Compute weighted qualification score (70% skills, 30% experience)
    """
    # Extract and normalize candidate data
    candidate_skills = _normalize_skill_list(parsed_resume.get("skills", []))
    years_experience = parsed_resume.get("years_experience") or 0

    required_skills = _normalize_skill_list((job_requirements or {}).get("required_skills"))
    preferred_skills = _normalize_skill_list((job_requirements or {}).get("preferred_skills"))

    if not required_skills:
        required_skills = _extract_skill_keywords(job_description)

    required_set = set(required_skills)
    preferred_set = set(preferred_skills)
    candidate_set = set(candidate_skills)

    matched_required = [skill for skill in required_skills if skill in candidate_set]
    missing_required = [skill for skill in required_skills if skill not in candidate_set]
    matched_preferred = [skill for skill in preferred_skills if skill in candidate_set]
    missing_preferred = [skill for skill in preferred_skills if skill not in candidate_set]

    matched_skills = matched_required + [skill for skill in matched_preferred if skill not in matched_required]
    missing_skills = missing_required + [skill for skill in missing_preferred if skill not in missing_required]

    required_score = 1.0 if not required_skills else len(matched_required) / len(required_skills)
    preferred_score = 1.0 if not preferred_skills else len(matched_preferred) / len(preferred_skills)
    skill_score = required_score if not preferred_skills else min(1.0, (required_score * 0.85) + (preferred_score * 0.15))

    min_years = (job_requirements or {}).get("min_years_experience")
    if isinstance(years_experience, (int, float)):
        if isinstance(min_years, (int, float)) and min_years > 0:
            experience_score = min(1.0, years_experience / min_years)
        else:
            experience_score = min(1.0, years_experience / 8)
    else:
        experience_score = 0.0

    qualification_score = round((skill_score * 0.75) + (experience_score * 0.25), 3)
    
    # Pass threshold driven by config — not hardcoded
    meets_threshold = qualification_score >= QUALIFICATION_THRESHOLD
    
    # Confidence based on data quality
    # Base confidence 0.65, up to 0.90 with more skills
    confidence = round(0.65 + min(0.25, 0.05 * len(candidate_skills)), 2)
    
    # Build explanation
    explanation = (
        f"Heuristic screening used structured skill matching where available. "
        f"Score={qualification_score:.1%} "
        f"(required={required_score:.1%}, preferred={preferred_score:.1%}, experience={experience_score:.1%}). "
        f"Matched {len(matched_required)}/{len(required_skills) or len(matched_skills) or 1} required skills"
        f"{f' and {len(matched_preferred)}/{len(preferred_skills)} preferred skills' if preferred_skills else ''}. "
        f"Years experience={years_experience}; threshold={QUALIFICATION_THRESHOLD:.0%}."
    )
    
    return {
        "qualification_score": qualification_score,
        "meets_threshold": meets_threshold,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills[:10],  # Limit output
        "years_experience": years_experience if isinstance(years_experience, (int, float)) else 0,
        "confidence": confidence,
        "explanation": explanation,
    }


def coerce_screening_result(result: dict) -> dict:
    """
    Normalize and validate LLM screening result
    
    Ensures all required fields are present with correct types
    Handles missing or malformed data gracefully
    """
    # Extract and validate matched/missing skills
    matched_skills = result.get("matched_skills")
    if not isinstance(matched_skills, list):
        matched_skills = []
    
    missing_skills = result.get("missing_skills")
    if not isinstance(missing_skills, list):
        missing_skills = []
    
    # Extract and validate numeric scores
    qualification_score = result.get("qualification_score")
    try:
        qualification_score = float(qualification_score or 0.0)
        qualification_score = max(0.0, min(1.0, qualification_score))  # Clamp to [0, 1]
    except (TypeError, ValueError):
        qualification_score = 0.0
    
    # Extract and validate confidence
    confidence = result.get("confidence")
    try:
        confidence = float(confidence or 0.0)
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
    except (TypeError, ValueError):
        confidence = 0.5  # Default medium confidence
    
    # Extract years of experience
    years_experience = result.get("years_experience")
    try:
        years_experience = int(float(years_experience or 0))
        years_experience = max(0, years_experience)  # No negative years
    except (TypeError, ValueError):
        years_experience = 0
    
    # Extract or compute meets_threshold using configurable value
    meets_threshold = result.get("meets_threshold")
    if meets_threshold is None:
        meets_threshold = qualification_score >= QUALIFICATION_THRESHOLD
    else:
        meets_threshold = bool(meets_threshold)
    
    # Extract explanation
    explanation = result.get("explanation")
    if not explanation or not isinstance(explanation, str):
        explanation = f"Qualification screening completed with score {qualification_score:.1%}"
    
    return {
        "qualification_score": qualification_score,
        "meets_threshold": meets_threshold,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "years_experience": years_experience,
        "confidence": confidence,
        "explanation": explanation,
    }
