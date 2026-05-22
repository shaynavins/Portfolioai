"""
Advanced prompt parser for intelligent portfolio generation.
Extracts bio, design intent, achievements, and configuration from user prompts.
"""
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class DesignConfig:
    """Configuration for portfolio visual design and layout."""
    color_mood: str  # "vibrant", "minimal", "professional", "creative", "bold"
    layout: str  # "hero", "split", "grid", "timeline"
    background: str  # "animated", "gradient", "minimal", "particles"
    animation_level: str  # "minimal", "moderate", "high"
    typography: str  # "minimal", "playful", "bold", "elegant"
    spacing: str  # "tight", "comfortable", "spacious"
    avatar_motion: str  # "static", "follow", "animate"
    project_style: str  # "cards", "list", "grid", "showcase"
    sections: List[str]  # ["hero", "skills", "projects", "footer"]
    gradient_from: Optional[str] = None  # CSS color for gradient start
    gradient_to: Optional[str] = None  # CSS color for gradient end
    emoji_size: str = "2rem"  # Font size for emoji avatar


@dataclass
class PortfolioSpec:
    """Complete portfolio specification extracted from prompt."""
    bio: str
    tagline: str
    highlights: List[str]
    design_emoji: Optional[str]
    interactive_bg: bool
    show_all_projects: bool
    design_config: DesignConfig
    cta_text: str


def parse_user_prompt(prompt: str, doc_text: str = "") -> PortfolioSpec:
    """
    Parse a user prompt into structured portfolio specification.
    
    Args:
        prompt: User's free-form portfolio instructions
        doc_text: Additional context from uploaded documents
        
    Returns:
        PortfolioSpec with bio, design config, and metadata
    """
    if not prompt.strip() and not doc_text.strip():
        return _default_spec()
    
    lower = prompt.lower()
    
    # ── Extract identity and role information ──
    bio = _extract_bio(prompt, doc_text)
    tagline = _extract_tagline(prompt)
    highlights = _extract_highlights(prompt)
    
    # ── Extract design preferences ──
    design_emoji = _extract_emoji(prompt)
    interactive_bg = _detect_interactive_bg(prompt)
    show_all_projects = _detect_show_all_projects(prompt)
    
    # ── Detect design mood and style ──
    color_mood = _detect_color_mood(prompt)
    layout = _detect_layout(prompt)
    background = _detect_background_style(prompt)
    animation_level = _detect_animation_level(prompt, interactive_bg)
    typography = _detect_typography_style(prompt)
    spacing = _detect_spacing_style(prompt)
    avatar_motion = _detect_avatar_motion(prompt, design_emoji)
    project_style = _detect_project_style(prompt)
    
    # ── Determine sections to include ──
    sections = _determine_sections(prompt)
    
    # ── Generate CTA text ──
    cta_text = _generate_cta(prompt)
    
    # Extract explicit colors and sizing
    gradient_from, gradient_to = _extract_gradient_colors(prompt)
    emoji_size = _extract_emoji_size(prompt, design_emoji)
    
    design_config = DesignConfig(
        color_mood=color_mood,
        layout=layout,
        background=background,
        animation_level=animation_level,
        typography=typography,
        spacing=spacing,
        avatar_motion=avatar_motion,
        project_style=project_style,
        sections=sections,
        gradient_from=gradient_from,
        gradient_to=gradient_to,
        emoji_size=emoji_size,
    )
    
    return PortfolioSpec(
        bio=bio,
        tagline=tagline,
        highlights=highlights,
        design_emoji=design_emoji,
        interactive_bg=interactive_bg,
        show_all_projects=show_all_projects,
        design_config=design_config,
        cta_text=cta_text,
    )


def _extract_bio(prompt: str, doc_text: str) -> str:
    """Extract and paraphrase professional bio from prompt."""
    text = prompt.strip()
    
    # Strip out design instructions to isolate identity text
    design_patterns = [
        r'i want (my|the|a) (design|background|portfolio|ui|theme|layout)[^.!?]*[.!?]?',
        r'(make|create|use|add|have|include) (it|the|a|my)[^.!?]*(interactive|dynamic|fun|emoji|cursor|avatar|animated|background|design)[^.!?]*[.!?]?',
        r'(background|bg) should be[^.!?]*[.!?]?',
        r'(cursor|mouse)[^.!?]*[.!?]?',
        r'(the design|my design)[^.!?]*[.!?]?',
        r'which is dynamic[^.!?]*[.!?]?',
        r'(all (my|the) (github )?(projects|repos))[^.!?]*[.!?]?',
    ]
    
    identity_text = text
    for pat in design_patterns:
        identity_text = re.sub(pat, ' ', identity_text, flags=re.I)
    identity_text = re.sub(r'\s+', ' ', identity_text).strip()
    
    # Extract structured elements
    lower = identity_text.lower()
    
    # Find role, organization, projects
    roles = re.findall(
        r'([a-z\s]{2,30}(?:developer|engineer|designer|researcher|scientist|founder|builder|creator))',
        identity_text,
        re.I
    )
    orgs = re.findall(r'(?:at|@|for)\s+([A-Z][^,.\n]*?)(?:[,.]|$)', identity_text)
    clubs = re.findall(
        r'(?:called|named|founder of|co-founder of|startup|club)\s+([A-Z][^\s.,]+)',
        identity_text,
        re.I
    )
    
    parts = []
    
    # Add roles
    if roles:
        main_role = roles[0].strip().rstrip('.,').title()
        if orgs:
            parts.append(f"{main_role} at {orgs[0].strip().title()}")
        else:
            parts.append(main_role)
    
    # Add organization if not already in role
    if orgs and not any('at' in p for p in parts):
        parts.append(f"at {orgs[0].strip().title()}")
    
    # Add clubs/startups
    if clubs:
        parts.append(f"Founder of {clubs[0].strip().title()}")
    
    # Add student status
    if 'student' in lower:
        parts.append("Student")
    
    # Build final bio
    if parts:
        bio = ' · '.join(parts)
    else:
        # Fallback to sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', identity_text) if len(s.strip()) > 15]
        bio = ' '.join(sentences[:2])[:280] if sentences else identity_text[:200]
    
    return bio if bio else "Software Developer & Builder"


def _extract_tagline(prompt: str) -> str:
    """Extract or generate a catchy tagline."""
    lower = prompt.lower()
    
    # Look for specific tagline phrases
    patterns = [
        r'(?:i am|i\'m|i am a) ([^.!?]+(?:building|creating|passionate about)[^.!?]*)',
        r'(?:my passion|love|enjoy) ([^.!?]+)',
        r'(?:dedicated to|focused on) ([^.!?]+)',
    ]
    
    for pat in patterns:
        match = re.search(pat, lower)
        if match:
            return match.group(1).strip().capitalize()
    
    # Generate from roles
    if 'founder' in lower:
        return "Turning ideas into products"
    elif 'designer' in lower:
        return "Crafting beautiful experiences"
    elif 'developer' in lower:
        return "Building innovative solutions"
    elif 'researcher' in lower:
        return "Exploring new frontiers"
    
    return "Creating meaningful work"


def _extract_highlights(prompt: str) -> List[str]:
    """Extract key achievements or highlights."""
    lower = prompt.lower()
    highlights = []
    
    # Look for clubs, startups, companies
    clubs = re.findall(r'(?:founder|founder of|co-founder|club|startup|company|organization)\s+([A-Z][^\s.,]+)', prompt, re.I)
    if clubs:
        highlights.extend([f"Founded {club}" for club in clubs[:2]])
    
    # Look for specific achievements
    if 'award' in lower or 'winner' in lower or 'achieved' in lower:
        matches = re.findall(r'(award|won|achieved)[^.!?]*', prompt, re.I)
        highlights.extend([m.capitalize() for m in matches[:2]])
    
    # Look for specific roles
    orgs = re.findall(r'(?:at|@)\s+([A-Z][^,.\n]*)', prompt)
    if orgs:
        highlights.append(f"Experience at {orgs[0].strip()}")
    
    return highlights[:3]  # Limit to 3 highlights


def _extract_emoji(prompt: str) -> Optional[str]:
    """Extract emoji descriptor from prompt."""
    lower = prompt.lower()
    
    # Detect skin tone
    skin = ""
    if any(k in lower for k in ["brown", "dark skin", "brown skin", "indian", "south asian", "medium"]):
        skin = "\U0001f3fe"  # medium-dark skin tone
    elif any(k in lower for k in ["light skin", "fair", "white"]):
        skin = "\U0001f3fb"  # light skin
    
    # Detect hair
    hair = ""
    if "curly" in lower:
        hair = "\u200d\U0001f9b1"  # curly hair
    elif "straight" in lower:
        hair = "\u200d\U0001f9b0"  # straight hair
    elif "red" in lower and "hair" in lower:
        hair = "\u200d\U0001f9b0"
    
    # Detect gender/base emoji
    if any(k in lower for k in ["girl", "woman", "she", "her", "female"]):
        base = "\U0001f469"
        return base + skin + hair if (skin or hair) else "\U0001f469\U0001f3fe\u200d\U0001f9b1"
    elif any(k in lower for k in ["boy", "man", "he", "him", "male", "guy"]):
        base = "\U0001f468"
        return base + skin + hair if (skin or hair) else "\U0001f468"
    elif "emoji" in lower or "avatar" in lower:
        return "\U0001f9d1\U0001f3fe\u200d\U0001f4bb"  # person at laptop
    
    return None


def _detect_interactive_bg(prompt: str) -> bool:
    """Detect if user wants interactive background."""
    lower = prompt.lower()
    return any(k in lower for k in [
        "interactive", "fun", "animated", "particles", "dynamic background",
        "cool bg", "cool background", "animated background", "moving", "floating"
    ])


def _detect_show_all_projects(prompt: str) -> bool:
    """Detect if user wants all projects displayed."""
    lower = prompt.lower()
    return any(k in lower for k in [
        "all my", "all github", "all projects", "every project", "all repos",
        "show all", "display all", "every repo"
    ])


def _detect_color_mood(prompt: str) -> str:
    """Detect color mood from prompt."""
    lower = prompt.lower()
    
    if any(k in lower for k in ["vibrant", "colorful", "bright", "bold", "energetic", "fun", "powerful", "purple", "gradient"]):
        return "vibrant"
    elif any(k in lower for k in ["professional", "corporate", "serious", "minimal", "clean"]):
        return "professional"
    elif any(k in lower for k in ["creative", "artistic", "playful", "experimental"]):
        return "creative"
    elif any(k in lower for k in ["dark", "moody", "elegant", "sophisticated"]):
        return "minimal"
    else:
        return "professional"


def _detect_layout(prompt: str) -> str:
    """Detect preferred layout style."""
    lower = prompt.lower()
    
    if any(k in lower for k in ["split", "two-column", "side-by-side", "divided"]):
        return "split"
    elif any(k in lower for k in ["grid", "card", "gallery"]):
        return "grid"
    elif any(k in lower for k in ["timeline", "chronological", "time"]):
        return "timeline"
    else:
        return "hero"


def _detect_background_style(prompt: str) -> str:
    """Detect background style preference."""
    lower = prompt.lower()
    
    if any(k in lower for k in ["animated", "particles", "floating", "moving", "dynamic", "gradient", "purple"]):
        return "animated"
    elif any(k in lower for k in ["gradient", "color gradient", "colorful"]):
        return "gradient"
    elif any(k in lower for k in ["minimal", "clean", "simple", "plain", "white"]):
        return "minimal"
    else:
        return "animated"


def _detect_animation_level(prompt: str, interactive_bg: bool) -> str:
    """Detect desired animation level."""
    lower = prompt.lower()
    
    if interactive_bg or any(k in lower for k in ["lots of animation", "very animated", "interactive"]):
        return "high"
    elif any(k in lower for k in ["some animation", "moderate", "subtle"]):
        return "moderate"
    else:
        return "minimal"


def _detect_typography_style(prompt: str) -> str:
    """Detect typography preference."""
    lower = prompt.lower()
    
    if any(k in lower for k in ["bold", "strong", "prominent", "large text", "big"]):
        return "bold"
    elif any(k in lower for k in ["minimal", "clean", "subtle", "simple"]):
        return "minimal"
    elif any(k in lower for k in ["playful", "fun", "creative", "artistic"]):
        return "playful"
    else:
        return "elegant"


def _detect_spacing_style(prompt: str) -> str:
    """Detect spacing preference."""
    lower = prompt.lower()
    
    if any(k in lower for k in ["spacious", "airy", "open", "spread out"]):
        return "spacious"
    elif any(k in lower for k in ["tight", "compact", "condensed", "dense"]):
        return "tight"
    else:
        return "comfortable"


def _detect_avatar_motion(prompt: str, has_emoji: bool) -> str:
    """Detect avatar motion preference."""
    if not has_emoji:
        return "static"
    
    lower = prompt.lower()
    
    if any(k in lower for k in ["cursor", "follow", "dynamic to cursor", "move with mouse"]):
        return "follow"
    elif any(k in lower for k in ["animate", "animated", "moving", "dance", "bounce"]):
        return "animate"
    else:
        return "follow"


def _detect_project_style(prompt: str) -> str:
    """Detect preferred project display style."""
    lower = prompt.lower()
    
    if any(k in lower for k in ["card", "cards"]):
        return "cards"
    elif any(k in lower for k in ["list", "simple"]):
        return "list"
    elif any(k in lower for k in ["grid"]):
        return "grid"
    else:
        return "cards"


def _determine_sections(prompt: str) -> List[str]:
    """Determine which portfolio sections to display."""
    lower = prompt.lower()
    sections = ["hero", "footer"]  # Always include
    
    if any(k in lower for k in ["skills", "tech", "technologies", "languages"]) or "all" in lower:
        sections.insert(-1, "skills")
    
    if any(k in lower for k in ["projects", "work", "repos", "repositories"]) or "all" in lower:
        sections.insert(-1, "projects")
    else:
        sections.insert(-1, "projects")  # Default to showing projects
    
    return sections


def _generate_cta(prompt: str) -> str:
    """Generate call-to-action text."""
    lower = prompt.lower()
    
    if any(k in lower for k in ["hire", "work with", "collaborat"]):
        return "Let's work together"
    elif any(k in lower for k in ["learn", "explore", "discover"]):
        return "Explore my work"
    elif any(k in lower for k in ["contact", "reach", "get in touch"]):
        return "Get in touch"
    else:
        return "View my work"


def _extract_gradient_colors(prompt: str) -> tuple:
    """Extract explicit gradient colors from prompt."""
    lower = prompt.lower()
    
    # Map color names to CSS values
    color_map = {
        "black": "#000000",
        "white": "#ffffff",
        "purple": "#a855f7",
        "blue": "#3b82f6",
        "red": "#ef4444",
        "green": "#22c55e",
        "pink": "#ec4899",
        "orange": "#f97316",
        "cyan": "#06b6d4",
        "indigo": "#6366f1",
    }
    
    gradient_from = None
    gradient_to = None
    
    # Look for "X to Y gradient" pattern
    gradient_match = re.search(r'(\w+)\s+to\s+(\w+)\s+gradient', lower)
    if gradient_match:
        color1 = gradient_match.group(1)
        color2 = gradient_match.group(2)
        gradient_from = color_map.get(color1)
        gradient_to = color_map.get(color2)
    
    return gradient_from, gradient_to


def _extract_emoji_size(prompt: str, has_emoji: bool) -> str:
    """Extract emoji size preference from prompt."""
    if not has_emoji:
        return "2rem"
    
    lower = prompt.lower()
    
    # Map size descriptors to CSS values
    if any(k in lower for k in ["huge", "giant", "massive", "big", "large", "at center", "centered"]):
        return "8rem"  # Huge size
    elif any(k in lower for k in ["medium", "normal"]):
        return "4rem"
    elif any(k in lower for k in ["small", "tiny"]):
        return "1rem"
    else:
        return "2rem"  # Default


def _default_spec() -> PortfolioSpec:
    """Return default portfolio specification."""
    return PortfolioSpec(
        bio="Software Developer & Builder",
        tagline="Creating meaningful work",
        highlights=[],
        design_emoji=None,
        interactive_bg=False,
        show_all_projects=False,
        design_config=DesignConfig(
            color_mood="professional",
            layout="hero",
            background="minimal",
            animation_level="minimal",
            typography="elegant",
            spacing="comfortable",
            avatar_motion="static",
            project_style="cards",
            sections=["hero", "projects", "footer"],
        ),
        cta_text="View my work",
    )
