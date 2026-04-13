"""
PortfolioAI — LangGraph Agent
5-node state machine that takes GitHub data + resume → live portfolio site

Nodes:
  1. analyzer    — fetch & score GitHub repos, extract resume data
  2. planner     — decide which projects to feature, outline structure
  3. writer      — use Gemini to write bio, project descriptions, skills
  4. builder     — generate complete HTML/CSS portfolio site
  5. deployer    — push to Cloudflare R2 + deploy to Vercel Pages
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, TypedDict, Optional, Any
import json
import asyncio
import structlog

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from tools.github_tool import GitHubTool
from tools.resume_tool import ResumeTool
from tools.deployer_tool import DeployerTool
from templates.site_builder import SiteBuilder
from llm import create_gemini_llm, parse_json_response

log = structlog.get_logger()


# ─── Agent State ──────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    job_id: str
    user_id: str
    github_username: str
    github_token: str
    theme: str
    selected_repos: Optional[list[str]]
    resume_bytes: Optional[bytes]
    resume_filename: Optional[str]
    trigger: str
    pushed_repo: Optional[str]

    # Intermediate
    repos_data: list[dict]
    resume_data: dict
    featured_projects: list[dict]
    outline: dict
    content: dict          # AI-written text content

    # Output
    site_html: str
    site_url: str
    portfolio_data: dict

    # Execution tracking
    steps: list[str]
    error: Optional[str]


# ─── Agent Class ──────────────────────────────────────────────────────────────

class PortfolioAgent:
    def __init__(self, job_id: str, user_id: str, db, **kwargs):
        self.job_id = job_id
        self.user_id = user_id
        self.db = db
        self.kwargs = kwargs
        self.llm = create_gemini_llm(max_tokens=1600)
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(AgentState)

        graph.add_node("analyzer", self.analyzer_node)
        graph.add_node("planner", self.planner_node)
        graph.add_node("writer", self.writer_node)
        graph.add_node("builder", self.builder_node)
        graph.add_node("deployer", self.deployer_node)

        graph.set_entry_point("analyzer")
        graph.add_edge("analyzer", "planner")
        graph.add_edge("planner", "writer")
        graph.add_edge("writer", "builder")
        graph.add_edge("builder", "deployer")
        graph.add_edge("deployer", END)

        return graph.compile()

    async def run(self) -> dict:
        initial_state: AgentState = {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "github_username": self.kwargs.get("github_username", ""),
            "github_token": self.kwargs.get("github_token", ""),
            "theme": self.kwargs.get("theme", "minimal"),
            "selected_repos": self.kwargs.get("selected_repos"),
            "resume_bytes": self.kwargs.get("resume_bytes"),
            "resume_filename": self.kwargs.get("resume_filename"),
            "trigger": self.kwargs.get("trigger", "manual"),
            "pushed_repo": self.kwargs.get("pushed_repo"),
            "repos_data": [],
            "resume_data": {},
            "featured_projects": [],
            "outline": {},
            "content": {},
            "site_html": "",
            "site_url": "",
            "portfolio_data": {},
            "steps": [],
            "error": None,
        }

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "site_url": final_state.get("site_url"),
            "portfolio_data": final_state.get("portfolio_data"),
        }

    # ─── Node 1: Analyzer ─────────────────────────────────────────────────────

    async def analyzer_node(self, state: AgentState) -> AgentState:
        """Fetch GitHub repos, score them, and parse resume if provided."""
        log.info("analyzer_node starting", job_id=state["job_id"])
        await self._update_progress(state["job_id"], "Analyzing GitHub repos...")

        # Fetch GitHub data
        github = GitHubTool(state["github_token"])
        repos_data = await github.get_repos_with_details(state["github_username"])

        # If user selected specific repos, filter + mark them
        if state.get("selected_repos"):
            for repo in repos_data:
                if repo["full_name"] in state["selected_repos"]:
                    repo["user_selected"] = True

        # Parse resume if provided
        resume_data = {}
        if state.get("resume_bytes"):
            resume_tool = ResumeTool()
            resume_data = await resume_tool.parse(
                state["resume_bytes"], state.get("resume_filename", "resume.pdf")
            )
            log.info("Resume parsed", skills_found=len(resume_data.get("skills", [])))

        return {
            **state,
            "repos_data": repos_data,
            "resume_data": resume_data,
            "steps": state["steps"] + ["✓ GitHub repos analyzed"],
        }

    # ─── Node 2: Planner ──────────────────────────────────────────────────────

    async def planner_node(self, state: AgentState) -> AgentState:
        """Use Gemini once for project selection, outline, and copywriting."""
        log.info("planner_node starting", job_id=state["job_id"])
        await self._update_progress(state["job_id"], "Planning portfolio structure...")

        repos_for_prompt = self._select_repos_for_prompt(state["repos_data"], state.get("selected_repos"))
        repos_summary = json.dumps([
            {
                "name": r["name"],
                "description": r.get("description", ""),
                "language": r.get("language"),
                "stars": r.get("stars", 0),
                "commits_last_90d": r.get("commits_last_90d", 0),
                "readme_snippet": r.get("readme", "")[:180],
                "topics": r.get("topics", []),
                "user_selected": r.get("user_selected", False),
            }
            for r in repos_for_prompt
        ], indent=2)

        resume_summary = json.dumps(self._summarize_resume(state.get("resume_data", {})), indent=2)

        prompt = f"""You are a portfolio architect and copywriter. Analyze these GitHub repositories and resume data, then select the BEST 3-4 projects to feature, plan the portfolio, and write concise copy.

REPOSITORIES:
{repos_summary}

RESUME DATA:
{resume_summary}

Return a JSON object with this exact structure:
{{
  "featured_projects": [
    {{
      "repo_full_name": "username/repo",
      "display_name": "Clean Display Name",
      "tagline": "One-sentence description",
      "why_featured": "Brief reason this was selected"
    }}
  ],
  "outline": {{
    "hero_headline": "2-4 word punchy headline",
    "hero_subheading": "One sentence that captures their specialty",
    "sections": ["hero", "about", "projects", "skills", "contact"],
    "primary_skills": ["skill1", "skill2", "skill3"],
    "tone": "professional|creative|technical|startup"
  }},
  "content": {{
    "hero": {{
      "name": "Full Name",
      "headline": "Short headline",
      "subheading": "One sentence subheading",
      "cta_text": "View My Work"
    }},
    "about": {{
      "bio_paragraph_1": "2 concise sentences",
      "bio_paragraph_2": "2 concise sentences",
      "years_experience": 0,
      "currently": "What they're working on"
    }},
    "projects": [
      {{
        "display_name": "...",
        "tagline": "...",
        "description": "1-2 sentence project description",
        "tech_tags": ["tag1", "tag2"],
        "github_url": "...",
        "live_url": null
      }}
    ],
    "skills": {{
      "languages": ["Python", "TypeScript"],
      "frameworks": ["FastAPI", "React"],
      "tools": ["Docker", "PostgreSQL"],
      "highlights": ["3 short skill highlights"]
    }},
    "contact": {{
      "email": "...",
      "github_url": "https://github.com/...",
      "linkedin_url": null,
      "twitter_url": null,
      "available_for": "Full-time roles / Freelance / Open source collaboration"
    }}
  }}
}}

Rules:
- Always include user_selected repos if any
- Prioritize repos with: recent commits, good README, stars, clear purpose
- Exclude: forks, tutorial projects, empty repos, class assignments
- Infer skills from both repos AND resume
- Make the hero headline memorable and specific to their work
- Keep every field compact and concrete
- Limit to 3 featured projects unless user_selected forces more
- Use at most 2 tech tags per project
- Keep each text field under 25 words when possible
- Always respond with valid JSON only"""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a portfolio architect. Always respond with valid JSON only, no markdown."),
            HumanMessage(content=prompt),
        ])

        plan = parse_json_response(response)

        # Enrich featured projects with full repo data
        repo_map = {r["full_name"]: r for r in state["repos_data"]}
        featured = []
        for fp in plan["featured_projects"]:
            repo = repo_map.get(fp["repo_full_name"], {})
            featured.append({**fp, **repo})

        return {
            **state,
            "featured_projects": featured,
            "outline": plan["outline"],
            "content": plan["content"],
            "steps": state["steps"] + ["✓ Portfolio structure planned"],
        }

    # ─── Node 3: Writer ───────────────────────────────────────────────────────

    async def writer_node(self, state: AgentState) -> AgentState:
        """Planner already generated content; skip the second LLM call."""
        log.info("writer_node starting", job_id=state["job_id"])
        return {
            **state,
            "steps": state["steps"] + ["✓ Content written by AI"],
        }

    # ─── Node 4: Builder ──────────────────────────────────────────────────────

    async def builder_node(self, state: AgentState) -> AgentState:
        """Generate complete HTML/CSS portfolio site from content."""
        log.info("builder_node starting", job_id=state["job_id"])
        await self._update_progress(state["job_id"], "Building your site...")

        builder = SiteBuilder(theme=state["theme"])
        html = builder.render(
            content=state["content"],
            github_username=state["github_username"],
        )

        # Also build the portfolio_data summary (used for dashboard preview)
        portfolio_data = {
            "hero": state["content"].get("hero", {}),
            "about": state["content"].get("about", {}),
            "projects_count": len(state["content"].get("projects", [])),
            "skills": state["content"].get("skills", {}),
            "contact": state["content"].get("contact", {}),
            "featured_repos": [p.get("repo_full_name") for p in state["featured_projects"]],
            "theme": state["theme"],
        }

        return {
            **state,
            "site_html": html,
            "portfolio_data": portfolio_data,
            "steps": state["steps"] + ["✓ Site HTML generated"],
        }

    # ─── Node 5: Deployer ─────────────────────────────────────────────────────

    async def deployer_node(self, state: AgentState) -> AgentState:
        """Upload site to R2 storage and deploy to Vercel Pages."""
        log.info("deployer_node starting", job_id=state["job_id"])
        await self._update_progress(state["job_id"], "Deploying your site...")

        deployer = DeployerTool()
        site_url = await deployer.deploy(
            html=state["site_html"],
            github_username=state["github_username"],
            user_id=state["user_id"],
        )

        # Update portfolio record in DB
        from api.database import Portfolio
        from sqlalchemy import select
        from slugify import slugify
        from datetime import datetime

        result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == state["user_id"])
        )
        portfolio = result.scalar_one_or_none()

        if portfolio:
            portfolio.site_url = site_url
            portfolio.portfolio_data = state["portfolio_data"]
            portfolio.last_built_at = datetime.utcnow()
            portfolio.is_published = True
        else:
            portfolio = Portfolio(
                user_id=state["user_id"],
                slug=slugify(state["github_username"]),
                site_url=site_url,
                theme=state["theme"],
                portfolio_data=state["portfolio_data"],
                is_published=True,
                last_built_at=datetime.utcnow(),
            )
            self.db.add(portfolio)

        await self.db.commit()

        return {
            **state,
            "site_url": site_url,
            "steps": state["steps"] + [f"✓ Live at {site_url}"],
        }

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _update_progress(self, job_id: str, step: str):
        """Update progress_steps in the DB for SSE streaming."""
        from api.database import BuildJob
        from sqlalchemy import select
        result = await self.db.execute(select(BuildJob).where(BuildJob.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            steps = job.progress_steps or []
            steps.append(step)
            job.progress_steps = steps
            await self.db.commit()

    def _select_repos_for_prompt(self, repos_data: list[dict], selected_repos: Optional[list[str]]) -> list[dict]:
        selected = set(selected_repos or [])
        scored_repos = sorted(
            repos_data,
            key=lambda repo: (
                1 if repo.get("full_name") in selected or repo.get("user_selected") else 0,
                repo.get("stars", 0),
                repo.get("commits_last_90d", 0),
                len(repo.get("readme", "") or ""),
            ),
            reverse=True,
        )
        limit = max(6, len(selected)) if selected else 6
        return scored_repos[:limit]

    def _summarize_resume(self, resume_data: dict) -> dict:
        if not resume_data:
            return {}

        summary = {}
        for key in ("name", "title", "email", "linkedin", "github"):
            value = resume_data.get(key)
            if value:
                summary[key] = value

        skills = resume_data.get("skills")
        if isinstance(skills, list):
            summary["skills"] = skills[:12]

        experience = resume_data.get("experience")
        if isinstance(experience, list):
            summary["experience"] = experience[:3]

        education = resume_data.get("education")
        if isinstance(education, list):
            summary["education"] = education[:2]

        projects = resume_data.get("projects")
        if isinstance(projects, list):
            summary["projects"] = projects[:3]

        return summary
