"""
Gemini-powered portfolio generator.
Uses Gemini AI to intelligently interpret user prompts and generate custom portfolio pages.
"""
import json
import structlog
from llm.client import create_gemini_llm, parse_json_response

log = structlog.get_logger()


def generate_portfolio_html(
    user_prompt: str,
    user_name: str,
    user_bio: str,
    github_url: str,
    projects: list,
    avatar_url: str,
    skills: list,
) -> str:
    """
    Use Gemini to intelligently generate a custom portfolio HTML page based on user prompt.
    
    Args:
        user_prompt: User's design and content instructions
        user_name: User's name
        user_bio: User's professional bio
        github_url: GitHub profile URL
        projects: List of GitHub projects
        avatar_url: User's avatar URL
        skills: List of programming languages/skills
        
    Returns:
        Custom HTML portfolio page
    """
    
    # Build projects JSON for the prompt
    projects_json = json.dumps([{
        "name": p.get("name", ""),
        "description": p.get("description", ""),
        "url": p.get("url", ""),
        "stars": p.get("stars", 0),
        "language": p.get("language", ""),
    } for p in projects[:8]])  # Limit to 8 for brevity
    
    system_prompt = """You are an expert web developer and UI designer. Your task is to generate a beautiful, 
custom HTML portfolio page based on the user's specific design instructions and preferences.

IMPORTANT RULES:
1. Parse the user's prompt INTELLIGENTLY to understand design intent (colors, layout, emoji, animations, etc.)
2. Generate COMPLETE, VALID HTML (single file with inline CSS and JavaScript)
3. Use modern CSS with gradients, animations, and responsive design
4. Apply the user's exact design preferences (gradient colors, emoji size, animations, etc.)
5. Display all projects prominently
6. Make the portfolio visually unique and creative
7. Ensure the HTML is self-contained with no external dependencies (except fonts)

OUTPUT: Return ONLY valid HTML code, wrapped in ```html and ```."""

    user_message = f"""Generate a custom portfolio HTML page based on these requirements:

USER DESIGN PROMPT:
{user_prompt}

USER INFORMATION:
- Name: {user_name}
- Bio: {user_bio}
- GitHub: {github_url}
- Avatar: {avatar_url}
- Skills: {', '.join(skills[:5])}

PROJECTS:
{projects_json}

QUALITY RUBRIC - ensure the output meets all standards:
✓ Layout: Hero section with name/avatar/bio, sections for projects/skills, footer
✓ Responsive: Mobile-first, works on screens 320px to 4k width
✓ Typography: Clear hierarchy (headings 2.5-3rem, body 1rem), sans-serif fonts
✓ Spacing: Consistent padding (1.5-2rem sections), whitespace breathing room
✓ Cards: Project cards with shadow/hover effects, 20px padding, rounded corners
✓ Colors: Apply user's color choices or elegant defaults if none specified
✓ Animation: Smooth transitions (0.2-0.3s), NO janky or infinite animations
✓ Accessibility: Color contrast ≥4.5:1, semantic HTML, alt text
✓ CTA: GitHub button prominent, clear link styling
✓ Fonts: Use system fonts (San Francisco/Segoe) or web-safe sans-serif

Create a visually striking, fully custom HTML portfolio that implements ALL of the user's design requirements.
Extract colors, emoji, animations, layout preferences from the prompt and apply them exactly as specified."""

    try:
        llm = create_gemini_llm()
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ])
        
        html_content = response.content
        
        # Extract HTML from markdown code blocks if present
        if "```html" in html_content:
            start = html_content.find("```html") + 7
            end = html_content.find("```", start)
            html_content = html_content[start:end].strip()
        elif "```" in html_content:
            start = html_content.find("```") + 3
            end = html_content.find("```", start)
            html_content = html_content[start:end].strip()
        
        log.info("portfolio_generated", prompt_length=len(user_prompt), html_size=len(html_content))
        return html_content
        
    except Exception as e:
        log.error("portfolio_generation_failed", error=str(e), exc_info=True)
        # Fallback to a basic HTML if generation fails
        return _generate_fallback_html(user_name, user_bio, github_url, projects, avatar_url)


def generate_portfolio_config(user_prompt: str) -> dict:
    """
    Use Gemini to extract design configuration from user prompt.
    Returns structured design config that the frontend can use.
    """
    
    system_prompt = """You are a UI design analyst. Extract design preferences from the user's portfolio prompt.
Return a JSON object with these fields:
- gradient_from: CSS color (e.g., "#000000")
- gradient_to: CSS color (e.g., "#a855f7")
- emoji: Unicode emoji character if specified
- emoji_size: Size in rem (2, 4, 8, etc.)
- animation_level: "minimal", "moderate", or "high"
- color_mood: "vibrant", "professional", "creative", "minimal"
- layout: "hero", "split", "grid"
- background_style: "gradient", "animated", "minimal"
- typography: "bold", "elegant", "playful"
- spacing: "tight", "comfortable", "spacious"

Be strict: only return colors that exist in CSS. Return null for unspecified fields."""

    try:
        llm = create_gemini_llm()
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract design config from: {user_prompt}\n\nReturn ONLY valid JSON."}
        ])
        
        config = parse_json_response(response)
        log.info("config_extracted", fields=list(config.keys()))
        return config
        
    except Exception as e:
        log.error("config_extraction_failed", error=str(e))
        return {}


def _generate_fallback_html(user_name: str, user_bio: str, github_url: str, projects: list, avatar_url: str) -> str:
    """Generate a basic fallback HTML portfolio if Gemini fails."""
    
    projects_html = "".join([
        f'<div class="project-card"><h3>{p.get("name", "")}</h3><p>{p.get("description", "")}</p>'
        f'<a href="{p.get("url", "")}" target="_blank">View Project</a></div>'
        for p in projects[:6]
    ])
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{user_name}'s Portfolio</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: white; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        .hero {{ text-align: center; margin: 60px 0; }}
        .hero h1 {{ font-size: 3rem; margin: 20px 0; }}
        .hero p {{ font-size: 1.2rem; color: #aaa; margin: 20px 0; }}
        .avatar {{ width: 120px; height: 120px; border-radius: 50%; margin: 0 auto 20px; border: 3px solid #666; }}
        .projects {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 40px 0; }}
        .project-card {{ border: 1px solid #333; padding: 20px; border-radius: 8px; transition: all 0.3s; }}
        .project-card:hover {{ border-color: #666; background: rgba(255,255,255,0.05); }}
        .project-card h3 {{ margin: 0 0 10px 0; }}
        .project-card a {{ display: inline-block; margin-top: 10px; color: #0a9fff; text-decoration: none; }}
        .footer {{ text-align: center; margin-top: 60px; padding-top: 40px; border-top: 1px solid #333; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <img src="{avatar_url}" alt="{user_name}" class="avatar">
            <h1>{user_name}</h1>
            <p>{user_bio}</p>
            <a href="{github_url}" target="_blank" style="color: #0a9fff; text-decoration: none;">GitHub Profile</a>
        </div>
        
        <div class="projects">
            {projects_html}
        </div>
        
        <div class="footer">
            <p>Built with PortfolioAI</p>
        </div>
    </div>
</body>
</html>"""
