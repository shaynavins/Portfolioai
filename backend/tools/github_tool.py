"""
GitHub Tool — fetches repos, READMEs, commit history, and repo metadata
Used by the Analyzer node in the LangGraph agent
"""
import httpx
import asyncio
import base64
import structlog
from typing import Optional

log = structlog.get_logger()

GITHUB_API = "https://api.github.com"


class GitHubTool:
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_repos_with_details(self, username: str) -> list[dict]:
        """Fetch all owned repos + enrich top ones with README and commit data."""
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            # Fetch repo list
            repos_resp = await client.get(
                f"{GITHUB_API}/user/repos",
                params={"sort": "updated", "per_page": 50, "type": "owner"},
            )
            repos = repos_resp.json()

            # Filter out forks and empty repos
            repos = [r for r in repos if not r.get("fork") and r.get("size", 0) > 0]

            # Keep context lean to reduce downstream token usage.
            top_repos = repos[:8]
            tasks = [self._enrich_repo(client, r) for r in top_repos]
            enriched = await asyncio.gather(*tasks, return_exceptions=True)

            result = []
            for repo, enrichment in zip(top_repos, enriched):
                if isinstance(enrichment, Exception):
                    log.warning("Failed to enrich repo", repo=repo["name"], error=str(enrichment))
                    enrichment = {}
                result.append({
                    "full_name": repo["full_name"],
                    "name": repo["name"],
                    "description": repo.get("description", ""),
                    "language": repo.get("language"),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "topics": repo.get("topics", []),
                    "url": repo.get("html_url"),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "is_fork": repo.get("fork", False),
                    **enrichment,
                })

            return result

    async def _enrich_repo(self, client: httpx.AsyncClient, repo: dict) -> dict:
        """Fetch README + recent commit count for a single repo."""
        full_name = repo["full_name"]
        enrichment = {}

        # README
        try:
            readme_resp = await client.get(f"{GITHUB_API}/repos/{full_name}/readme")
            if readme_resp.status_code == 200:
                data = readme_resp.json()
                content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                enrichment["readme"] = content[:600]
        except Exception:
            pass

        # Commit activity (last 90 days approximation via stats)
        try:
            commits_resp = await client.get(
                f"{GITHUB_API}/repos/{full_name}/commits",
                params={"per_page": 100, "since": "2024-10-01"},  # rough 90-day window
            )
            if commits_resp.status_code == 200:
                enrichment["commits_last_90d"] = len(commits_resp.json())
        except Exception:
            enrichment["commits_last_90d"] = 0

        # Languages breakdown
        try:
            langs_resp = await client.get(f"{GITHUB_API}/repos/{full_name}/languages")
            if langs_resp.status_code == 200:
                enrichment["languages"] = langs_resp.json()
        except Exception:
            pass

        return enrichment

    async def setup_webhook(self, username: str, repo_name: str, webhook_url: str) -> Optional[dict]:
        """Register a push webhook on a specific repo."""
        async with httpx.AsyncClient(headers=self.headers) as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{username}/{repo_name}/hooks",
                json={
                    "name": "web",
                    "active": True,
                    "events": ["push"],
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": "your_webhook_secret",
                    },
                },
            )
            if resp.status_code == 201:
                return resp.json()
            return None
