"""
Resume Tool — extracts structured data from PDF or JSON resumes
Supports: .pdf, .json, .txt
"""
import json
import io
import re
import structlog
from typing import Optional

log = structlog.get_logger()


class ResumeTool:
    async def parse(self, file_bytes: bytes, filename: str) -> dict:
        """Parse resume file and return structured JSON."""
        ext = filename.lower().split(".")[-1]

        if ext == "pdf":
            return await self._parse_pdf(file_bytes)
        elif ext == "json":
            return self._parse_json(file_bytes)
        elif ext == "txt":
            return await self._parse_text(file_bytes.decode("utf-8"))
        else:
            log.warning("Unsupported resume format", ext=ext)
            return {}

    async def _parse_pdf(self, file_bytes: bytes) -> dict:
        """Extract text from PDF, then use lightweight local parsing."""
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            return await self._parse_text(text)
        except Exception as e:
            log.error("PDF parse failed", error=str(e))
            return {}

    def _parse_json(self, file_bytes: bytes) -> dict:
        """Parse JSON resume (standard JSON Resume format supported)."""
        try:
            data = json.loads(file_bytes)
            # Handle JSON Resume format (jsonresume.org)
            if "basics" in data:
                return {
                    "name": data["basics"].get("name"),
                    "email": data["basics"].get("email"),
                    "summary": data["basics"].get("summary"),
                    "location": data["basics"].get("location", {}).get("city"),
                    "linkedin": data["basics"].get("profiles", [{}])[0].get("url"),
                    "skills": [s["name"] for s in data.get("skills", [])],
                    "experience": [
                        {
                            "company": w.get("company"),
                            "title": w.get("position"),
                            "duration": f"{w.get('startDate','')} - {w.get('endDate','Present')}",
                            "summary": w.get("summary"),
                        }
                        for w in data.get("work", [])
                    ],
                    "education": [
                        {
                            "institution": e.get("institution"),
                            "degree": f"{e.get('studyType','')} {e.get('area','')}",
                            "year": e.get("endDate", ""),
                        }
                        for e in data.get("education", [])
                    ],
                }
            return data
        except Exception as e:
            log.error("JSON resume parse failed", error=str(e))
            return {}

    async def _parse_text(self, text: str) -> dict:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        phone_match = re.search(r"(\+\d{1,3}\s*)?[\(\d][\d\s\-\(\)]{7,}\d", text)
        linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/[^\s]+", text, re.IGNORECASE)
        github_match = re.search(r"https?://(?:www\.)?github\.com/[^\s]+", text, re.IGNORECASE)

        name = lines[0] if lines else ""
        if email_match and name.lower() in email_match.group(0).lower():
            name = lines[1] if len(lines) > 1 else ""

        summary = ""
        for line in lines[1:6]:
            if len(line.split()) >= 8 and "http" not in line.lower():
                summary = line
                break

        skills = self._extract_skills(text)

        return {
            "name": name,
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "location": "",
            "linkedin": linkedin_match.group(0) if linkedin_match else "",
            "github_url": github_match.group(0) if github_match else "",
            "summary": summary,
            "skills": skills,
            "experience": [],
            "education": [],
            "years_experience": 0,
            "certifications": [],
            "raw_text": text[:1200],
        }

    def _extract_skills(self, text: str) -> list[str]:
        skill_candidates = [
            "Python", "TypeScript", "JavaScript", "Java", "Go", "Rust", "C++",
            "React", "Next.js", "Node.js", "FastAPI", "Django", "Flask",
            "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes",
            "AWS", "GCP", "Azure", "OpenAI", "LangChain", "LangGraph",
            "Tailwind", "HTML", "CSS", "Git",
        ]
        text_lower = text.lower()
        return [skill for skill in skill_candidates if skill.lower() in text_lower][:12]
