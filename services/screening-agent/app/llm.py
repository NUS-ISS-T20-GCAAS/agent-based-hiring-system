"""
LLM client for AI-powered candidate screening
Uses OpenAI API with structured output
"""

import json
import re
from typing import Any

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT_SEC, QUALIFICATION_THRESHOLD


def _extract_json(text: str) -> dict[str, Any]:
    """
    Extract JSON from LLM response
    Handles markdown code blocks and other formatting
    """
    stripped = text.strip()
    
    # Remove markdown code blocks
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}")


class ScreeningLLM:
    """
    LLM-powered screening using OpenAI API
    
    Provides intelligent candidate evaluation with:
    - Skill matching and gap analysis
    - Experience assessment
    - Qualification scoring
    - Confidence estimation
    """
    
    def __init__(self) -> None:
        self.enabled = bool(OPENAI_API_KEY)
        self._client = (
            OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEC) 
            if self.enabled 
            else None
        )

    def score_candidate(
        self, 
        *, 
        parsed_resume: dict[str, Any], 
        job_description: str,
        job_requirements: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Score candidate using LLM
        
        Args:
            parsed_resume: Structured resume data with skills, experience, etc.
            job_description: Free-text job description
            job_requirements: Optional structured requirements (required_skills, etc.)
            
        Returns:
            Dictionary with scoring results:
            {
                "qualification_score": 0.85,
                "meets_threshold": True,
                "matched_skills": ["python", "sql"],
                "missing_skills": ["aws"],
                "years_experience": 7,
                "confidence": 0.90,
                "explanation": "Strong match with..."
            }
        """
        if not self._client:
            raise RuntimeError("OPENAI_API_KEY is not configured - LLM screening disabled")

        # Build comprehensive prompt
        prompt = self._build_prompt(parsed_resume, job_description, job_requirements)
        
        try:
            # Call OpenAI API
            response = self._client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent scoring
                max_tokens=1000
            )
            
            # Extract and parse response
            output_text = response.choices[0].message.content
            result = _extract_json(output_text)
            
            # Validate required fields
            self._validate_result(result)
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"LLM screening failed: {str(e)}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return (
            "You are a qualification screening agent for a hiring system. "
            "Your job is to evaluate candidates against job requirements and provide "
            "structured scoring data.\n\n"

            # ── Bias guard ──────────────────────────────────────────────────
            "FAIRNESS REQUIREMENT — you must strictly follow these rules:\n"
            "- Evaluate ONLY technical skills, years of relevant experience, "
            "and stated qualifications.\n"
            "- You MUST NOT consider, infer, or be influenced by: candidate name, "
            "gender, age, nationality, ethnicity, religion, marital status, "
            "socioeconomic background, or the prestige/location of educational "
            "institutions.\n"
            "- Do NOT use graduation year as a proxy for age.\n"
            "- Do NOT penalise non-linear career paths or employment gaps.\n"
            "- If demographic signals are present in the resume, ignore them "
            "entirely and focus only on skills and experience.\n\n"
            # ────────────────────────────────────────────────────────────────

            "You must return ONLY valid JSON with these exact keys:\n"
            "- qualification_score: float 0-1 (overall qualification)\n"
            f"- meets_threshold: boolean (true if score >= {QUALIFICATION_THRESHOLD})\n"
            "- matched_skills: array of lowercase skill strings the candidate has\n"
            "- missing_skills: array of lowercase required skills the candidate lacks\n"
            "- years_experience: integer (candidate's years of experience)\n"
            "- confidence: float 0-1 (your confidence in this assessment)\n"
            "- explanation: string (2-3 sentence explanation of your scoring)\n\n"

            "Scoring guidelines:\n"
            "- Weight required skills heavily (70% of score)\n"
            "- Preferred skills add bonus (30% of score)\n"
            "- Experience can add up to 10% bonus\n"
            "- Be conservative: only match skills you're confident about\n"
            "- Normalize all skills to lowercase\n"
            f"- Threshold for passing is {QUALIFICATION_THRESHOLD} "
            f"({QUALIFICATION_THRESHOLD:.0%})\n\n"

            "Return ONLY the JSON object, no other text."
        )

    def _build_prompt(
        self, 
        parsed_resume: dict, 
        job_description: str,
        job_requirements: dict = None
    ) -> str:
        """Build the user prompt with all relevant data"""
        parts = []
        
        # Job description
        parts.append("=== JOB DESCRIPTION ===")
        parts.append(job_description or "No description provided")
        parts.append("")
        
        # Structured requirements (if available)
        if job_requirements:
            parts.append("=== STRUCTURED REQUIREMENTS ===")
            
            if "required_skills" in job_requirements:
                parts.append(f"Required Skills: {', '.join(job_requirements['required_skills'])}")
            
            if "preferred_skills" in job_requirements:
                parts.append(f"Preferred Skills: {', '.join(job_requirements['preferred_skills'])}")
            
            if "min_years_experience" in job_requirements:
                parts.append(f"Minimum Experience: {job_requirements['min_years_experience']} years")
            
            parts.append("")
        
        # Candidate resume
        parts.append("=== CANDIDATE RESUME ===")
        parts.append(json.dumps(parsed_resume, indent=2))
        parts.append("")
        
        # Instructions
        parts.append("=== YOUR TASK ===")
        parts.append(
            "Evaluate this candidate against the job requirements. "
            "Return a JSON object with the scoring data as specified in your system prompt."
        )
        
        return "\n".join(parts)

    def _validate_result(self, result: dict) -> None:
        """Validate that LLM returned all required fields"""
        required_fields = [
            "qualification_score",
            "meets_threshold",
            "matched_skills",
            "missing_skills",
            "years_experience",
            "confidence",
            "explanation"
        ]
        
        missing = [field for field in required_fields if field not in result]
        
        if missing:
            raise ValueError(
                f"LLM response missing required fields: {', '.join(missing)}"
            )