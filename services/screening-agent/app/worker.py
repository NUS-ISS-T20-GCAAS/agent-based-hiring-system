def heuristic_screen_candidate(*, parsed_resume: dict, job_description: str) -> dict:
    candidate_skills = [skill.lower() for skill in parsed_resume.get("skills", []) if isinstance(skill, str)]
    years_experience = parsed_resume.get("years_experience") or 0

    required_skills = sorted({word for word in (job_description or "").lower().split() if len(word) > 2})
    required_skill_set = set(required_skills)

    matched_skills = [skill for skill in candidate_skills if skill in required_skill_set]
    missing_skills = [skill for skill in required_skills if skill in required_skill_set - set(matched_skills)]

    skill_score = 1.0 if not required_skills else len(matched_skills) / len(required_skills)
    experience_score = min(1.0, years_experience / 8) if isinstance(years_experience, (int, float)) else 0.0
    qualification_score = round((skill_score * 0.7) + (experience_score * 0.3), 3)

    return {
        "qualification_score": qualification_score,
        "meets_threshold": qualification_score >= 0.6,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills[:10],
        "years_experience": years_experience if isinstance(years_experience, (int, float)) else 0,
        "confidence": round(0.65 + min(0.25, 0.05 * len(candidate_skills)), 2),
        "explanation": (
            f"Qualification score={qualification_score}; "
            f"matched_skills={len(matched_skills)}; years_experience={years_experience}"
        ),
    }


def coerce_screening_result(result: dict) -> dict:
    matched_skills = result.get("matched_skills")
    missing_skills = result.get("missing_skills")

    return {
        "qualification_score": float(result.get("qualification_score") or 0.0),
        "meets_threshold": bool(result.get("meets_threshold")),
        "matched_skills": matched_skills if isinstance(matched_skills, list) else [],
        "missing_skills": missing_skills if isinstance(missing_skills, list) else [],
        "years_experience": int(float(result.get("years_experience") or 0)),
        "confidence": min(1.0, max(0.0, float(result.get("confidence") or 0.0))),
        "explanation": result.get("explanation") or "Qualification screening completed",
    }
