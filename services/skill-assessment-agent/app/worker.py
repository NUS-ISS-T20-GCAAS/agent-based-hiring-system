from __future__ import annotations

import re

from app.config import PREFERRED_SKILLS_WEIGHT, REQUIRED_SKILLS_WEIGHT, SOFT_SKILLS_WEIGHT

HARD_SKILL_KEYWORDS = (
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
    "android",
    "ios",
    "swift",
    "java",
)

SOFT_SKILL_KEYWORDS = {
    "communication": ("communication", "communicate", "present", "presentation"),
    "leadership": ("leadership", "lead", "led", "mentored", "managed"),
    "collaboration": ("collaboration", "collaborative", "cross-functional", "teamwork", "partnered"),
    "problem solving": ("problem solving", "solve", "solved", "troubleshoot", "debug"),
    "ownership": ("ownership", "owned", "owner", "initiative"),
    "adaptability": ("adaptability", "adaptable", "flexible", "fast-paced"),
    "stakeholder management": ("stakeholder", "stakeholders", "client-facing"),
}


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for item in items:
        cleaned = " ".join(str(item or "").strip().lower().split())
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def normalize_skill_list(skills: list | None) -> list[str]:
    if not isinstance(skills, list):
        return []
    return _unique([skill for skill in skills if isinstance(skill, str)])


def _extract_hard_skills(text: str) -> list[str]:
    lower_text = (text or "").lower()
    return [skill for skill in HARD_SKILL_KEYWORDS if skill in lower_text]


def _extract_soft_skills(text: str) -> list[str]:
    lower_text = (text or "").lower()
    detected: list[str] = []
    for label, patterns in SOFT_SKILL_KEYWORDS.items():
        if any(pattern in lower_text for pattern in patterns):
            detected.append(label)
    return detected


def heuristic_assess_skills(
    *,
    parsed_resume: dict,
    resume_text: str,
    job_description: str,
    job_requirements: dict | None = None,
) -> dict:
    job_requirements = job_requirements or {}
    summary = parsed_resume.get("summary") or ""

    candidate_source = " ".join(
        [
            resume_text or "",
            summary if isinstance(summary, str) else "",
            " ".join(parsed_resume.get("skills") or []),
        ]
    )

    candidate_hard_skills = _unique(
        normalize_skill_list(parsed_resume.get("skills")) + _extract_hard_skills(candidate_source)
    )
    candidate_soft_skills = _extract_soft_skills(candidate_source)

    required_skills = normalize_skill_list(job_requirements.get("required_skills"))
    preferred_skills = normalize_skill_list(job_requirements.get("preferred_skills"))

    if not required_skills:
        required_skills = _extract_hard_skills(job_description)

    desired_soft_skills = _extract_soft_skills(job_description)

    candidate_hard_set = set(candidate_hard_skills)
    candidate_soft_set = set(candidate_soft_skills)

    matched_required = [skill for skill in required_skills if skill in candidate_hard_set]
    missing_required = [skill for skill in required_skills if skill not in candidate_hard_set]
    matched_preferred = [skill for skill in preferred_skills if skill in candidate_hard_set]
    missing_preferred = [skill for skill in preferred_skills if skill not in candidate_hard_set]
    matched_soft = [skill for skill in desired_soft_skills if skill in candidate_soft_set]
    missing_soft = [skill for skill in desired_soft_skills if skill not in candidate_soft_set]

    required_score = 1.0 if not required_skills else len(matched_required) / len(required_skills)
    preferred_score = 1.0 if not preferred_skills else len(matched_preferred) / len(preferred_skills)
    soft_score = 1.0 if not desired_soft_skills else len(matched_soft) / len(desired_soft_skills)

    skills_score = round(
        min(
            1.0,
            (required_score * REQUIRED_SKILLS_WEIGHT)
            + (preferred_score * PREFERRED_SKILLS_WEIGHT)
            + (soft_score * SOFT_SKILLS_WEIGHT),
        ),
        3,
    )

    strengths = _unique(matched_required + matched_preferred + matched_soft)[:8]
    gaps = _unique(missing_required + missing_preferred + missing_soft)[:8]
    confidence = round(
        min(
            0.95,
            0.62
            + min(0.18, 0.03 * len(candidate_hard_skills))
            + (0.08 if summary else 0.0)
            + (0.05 if resume_text else 0.0),
        ),
        2,
    )

    explanation = (
        f"Skill assessment used heuristic matching. Score={skills_score:.1%} "
        f"(required={required_score:.1%}, preferred={preferred_score:.1%}, soft={soft_score:.1%}). "
        f"Matched {len(matched_required)}/{len(required_skills) or len(candidate_hard_skills) or 1} required skills"
        f"{f' and {len(matched_preferred)}/{len(preferred_skills)} preferred skills' if preferred_skills else ''}. "
        f"Detected soft skills: {', '.join(candidate_soft_skills[:4]) if candidate_soft_skills else 'none'}."
    )

    return {
        "skills_score": skills_score,
        "matched_required_skills": matched_required,
        "matched_preferred_skills": matched_preferred,
        "missing_required_skills": missing_required,
        "missing_preferred_skills": missing_preferred,
        "detected_soft_skills": candidate_soft_skills,
        "matched_soft_skills": matched_soft,
        "missing_soft_skills": missing_soft,
        "strengths": strengths,
        "gaps": gaps,
        "gap_analysis": explanation,
        "confidence": confidence,
    }


def coerce_skill_assessment_result(result: dict) -> dict:
    def _list(key: str) -> list[str]:
        value = result.get(key)
        if not isinstance(value, list):
            return []
        return _unique([item for item in value if isinstance(item, str)])

    try:
        skills_score = float(result.get("skills_score") or 0.0)
    except (TypeError, ValueError):
        skills_score = 0.0
    skills_score = max(0.0, min(1.0, skills_score))

    try:
        confidence = float(result.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    gap_analysis = result.get("gap_analysis")
    if not isinstance(gap_analysis, str) or not gap_analysis.strip():
        gap_analysis = f"Skill assessment completed with score {skills_score:.1%}"

    return {
        "skills_score": skills_score,
        "matched_required_skills": _list("matched_required_skills"),
        "matched_preferred_skills": _list("matched_preferred_skills"),
        "missing_required_skills": _list("missing_required_skills"),
        "missing_preferred_skills": _list("missing_preferred_skills"),
        "detected_soft_skills": _list("detected_soft_skills"),
        "matched_soft_skills": _list("matched_soft_skills"),
        "missing_soft_skills": _list("missing_soft_skills"),
        "strengths": _list("strengths"),
        "gaps": _list("gaps"),
        "gap_analysis": gap_analysis.strip(),
        "confidence": confidence,
    }
