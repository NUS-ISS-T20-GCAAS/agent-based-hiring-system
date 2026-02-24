from app.base_agent import BaseAgent


class ScreeningAgent(BaseAgent):
    def artifact_type(self) -> str:
        return "qualification_screening_result"

    def handle(self, input_data):
        parsed_resume = input_data.get("parsed_resume") or {}
        candidate_skills = [skill.lower() for skill in parsed_resume.get("skills", [])]
        years_experience = parsed_resume.get("years_experience") or 0

        job_description = (input_data.get("job_description") or "").lower()
        required_skills = sorted({word for word in job_description.split() if len(word) > 2})
        required_skill_set = set(required_skills)

        matched_skills = [skill for skill in candidate_skills if skill in required_skill_set]
        missing_skills = [skill for skill in required_skills if skill in required_skill_set - set(matched_skills)]

        skill_score = 1.0 if not required_skills else len(matched_skills) / len(required_skills)
        experience_score = min(1.0, years_experience / 8)
        qualification_score = round((skill_score * 0.7) + (experience_score * 0.3), 3)

        meets_threshold = qualification_score >= 0.6
        confidence = round(0.65 + min(0.25, 0.05 * len(candidate_skills)), 2)

        return {
            "payload": {
                "qualification_score": qualification_score,
                "meets_threshold": meets_threshold,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills[:10],
                "years_experience": years_experience,
            },
            "confidence": confidence,
            "explanation": (
                f"Qualification score={qualification_score}; "
                f"matched_skills={len(matched_skills)}; years_experience={years_experience}"
            ),
        }
