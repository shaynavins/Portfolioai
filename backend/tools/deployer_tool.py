"""
Deployer Tool — uploads site to Cloudflare R2 and deploys via Vercel API
Falls back to simulating deployment in development mode
"""
import boto3
import httpx
import structlog
from botocore.config import Config
from pathlib import Path

from api.config import settings

log = structlog.get_logger()
PREVIEW_DIR = Path(__file__).resolve().parents[1] / ".preview"


class DeployerTool:
    async def deploy(self, html: str, github_username: str, user_id: str) -> str:
        """
        Deploy the generated site. Returns the live URL.

        Production strategy:
          1. Upload index.html + assets to Cloudflare R2
          2. Create/update a Vercel project pointed at R2 or use Vercel's
             direct file deployment API

        For MVP, we deploy directly via Vercel's deployment API with file contents.
        """
        if settings.ENVIRONMENT == "development" or not settings.VERCEL_TOKEN:
            # Local dev: return simulated URL
            slug = github_username.lower()
            PREVIEW_DIR.mkdir(exist_ok=True)
            (PREVIEW_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
            log.info("DEV MODE: Skipping real deployment", slug=slug)
            return f"http://localhost:8000/preview/{slug}"

        try:
            url = await self._deploy_to_vercel(html, github_username)
            return url
        except Exception as e:
            log.error("Vercel deploy failed, falling back to R2", error=str(e))
            url = await self._deploy_to_r2(html, github_username)
            return url

    async def _deploy_to_vercel(self, html: str, github_username: str) -> str:
        """
        Deploy using Vercel's Deployments API.
        Creates a new deployment with the HTML file contents.
        Docs: https://vercel.com/docs/rest-api/endpoints/deployments
        """
        slug = github_username.lower().replace("_", "-")
        project_name = f"portfolio-{slug}"

        headers = {
            "Authorization": f"Bearer {settings.VERCEL_TOKEN}",
            "Content-Type": "application/json",
        }
        if settings.VERCEL_TEAM_ID:
            headers["X-Vercel-Team-Id"] = settings.VERCEL_TEAM_ID

        async with httpx.AsyncClient(timeout=60) as client:
            # Create deployment
            resp = await client.post(
                "https://api.vercel.com/v13/deployments",
                headers=headers,
                json={
                    "name": project_name,
                    "files": [
                        {
                            "file": "index.html",
                            "data": html,
                        }
                    ],
                    "projectSettings": {
                        "framework": None,
                        "buildCommand": None,
                        "outputDirectory": None,
                    },
                    "target": "production",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            deployment_url = data.get("url", "")
            if not deployment_url.startswith("http"):
                deployment_url = f"https://{deployment_url}"

            log.info("Vercel deployment created", url=deployment_url)
            return deployment_url

    async def _deploy_to_r2(self, html: str, github_username: str) -> str:
        """Upload site to Cloudflare R2 as fallback."""
        slug = github_username.lower()

        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

        key = f"sites/{slug}/index.html"
        s3.put_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=key,
            Body=html.encode("utf-8"),
            ContentType="text/html",
            CacheControl="public, max-age=300",
        )

        public_url = f"{settings.R2_PUBLIC_URL}/{key}"
        log.info("Deployed to R2", url=public_url)
        return public_url
