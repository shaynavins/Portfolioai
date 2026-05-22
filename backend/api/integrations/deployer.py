"""
Portfolio deployment service.
Handles publishing portfolios to public URLs via R2 (Cloudflare) or fallback to database.
"""
import json
import structlog
import boto3
from botocore.config import Config
from api.config import settings

log = structlog.get_logger()


def _get_r2_client():
    """Create and return R2 (S3-compatible) client."""
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        return None
    
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


async def deploy_portfolio_html(user_id: str, username: str, html_content: str) -> str:
    """
    Deploy portfolio HTML to public URL via R2 (Cloudflare).
    Falls back to database-served URL if R2 not configured.
    
    Args:
        user_id: User's unique ID
        username: GitHub username for URL slug
        html_content: Generated HTML portfolio
        
    Returns:
        Public URL where portfolio is accessible
    """
    
    # Debug: log config values
    log.info(
        "deploy_portfolio_html_called",
        user_id=user_id,
        username=username,
        has_access_key=bool(settings.R2_ACCESS_KEY_ID),
        has_secret_key=bool(settings.R2_SECRET_ACCESS_KEY),
        has_public_url=bool(settings.R2_PUBLIC_URL),
        access_key_len=len(settings.R2_ACCESS_KEY_ID or ""),
        secret_key_len=len(settings.R2_SECRET_ACCESS_KEY or ""),
    )
    
    # Try R2 deployment if configured
    if settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_PUBLIC_URL:
        try:
            s3 = _get_r2_client()
            if s3:
                key = f"portfolios/{username}/index.html"
                log.info(f"Uploading to R2: bucket={settings.R2_BUCKET_NAME}, key={key}")
                s3.put_object(
                    Bucket=settings.R2_BUCKET_NAME,
                    Key=key,
                    Body=html_content.encode("utf-8"),
                    ContentType="text/html; charset=utf-8",
                    CacheControl="public, max-age=300",
                )
                
                public_url = f"{settings.R2_PUBLIC_URL}/{key}"
                log.info(
                    "portfolio_deployed_to_r2",
                    user_id=user_id,
                    username=username,
                    html_size=len(html_content),
                    public_url=public_url
                )
                return public_url
        except Exception as e:
            log.error(
                "r2_deployment_failed_falling_back",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
    
    # Fallback: Return database-served URL
    public_url = f"{settings.APP_URL}/portfolio/{username}"
    log.info(
        "portfolio_deployed_fallback",
        user_id=user_id,
        username=username,
        html_size=len(html_content),
        public_url=public_url
    )
    return public_url


async def get_portfolio_html(username: str) -> str | None:
    """
    Retrieve deployed portfolio HTML by username.
    In MVP: fetched from database portfolio_data["html"]
    In production: fetched from R2
    
    Args:
        username: GitHub username
        
    Returns:
        HTML content or None if not found
    """
    # This is handled by the portfolio route that reads from database
    # The route returns portfolio_data from DB which includes the HTML
    return None


async def publish_portfolio(portfolio_id: str, html_content: str, username: str) -> dict:
    """
    Publish portfolio: upload HTML to R2 and return deployment metadata.
    
    Args:
        portfolio_id: Portfolio's unique ID
        html_content: Generated HTML
        username: Username for slug
        
    Returns:
        Dict with site_url, is_published, and status
    """
    
    public_url = await deploy_portfolio_html(
        user_id=portfolio_id,
        username=username,
        html_content=html_content
    )
    
    return {
        "site_url": public_url,
        "is_published": True,
        "status": "deployed"
    }
