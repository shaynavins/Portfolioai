"""
Site Builder — generates complete HTML/CSS portfolio sites from structured content
Includes 3 themes: minimal, dark, and creative
"""
from jinja2 import Environment, BaseLoader
from typing import Optional
import html as html_lib


THEMES = {
    "minimal": {
        "bg": "#fafafa",
        "surface": "#ffffff",
        "text": "#1a1a1a",
        "text_muted": "#6b7280",
        "accent": "#2563eb",
        "accent_light": "#dbeafe",
        "border": "#e5e7eb",
        "font_heading": "'Playfair Display', serif",
        "font_body": "'Inter', sans-serif",
        "hero_bg": "#ffffff",
    },
    "dark": {
        "bg": "#0f172a",
        "surface": "#1e293b",
        "text": "#f1f5f9",
        "text_muted": "#94a3b8",
        "accent": "#38bdf8",
        "accent_light": "#0c4a6e",
        "border": "#334155",
        "font_heading": "'Space Grotesk', sans-serif",
        "font_body": "'Inter', sans-serif",
        "hero_bg": "#020617",
    },
    "creative": {
        "bg": "#fffbf5",
        "surface": "#ffffff",
        "text": "#1c1917",
        "text_muted": "#78716c",
        "accent": "#ea580c",
        "accent_light": "#fff7ed",
        "border": "#e7e5e4",
        "font_heading": "'DM Serif Display', serif",
        "font_body": "'DM Sans', sans-serif",
        "hero_bg": "#1c1917",
    },
}

PORTFOLIO_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ content.hero.name }} — Portfolio</title>
  <meta name="description" content="{{ content.hero.subheading }}">

  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Serif+Display&family=Space+Grotesk:wght@400;500;600&family=Inter:wght@400;500;600&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">

  <!-- Open Graph -->
  <meta property="og:title" content="{{ content.hero.name }} — Portfolio">
  <meta property="og:description" content="{{ content.hero.subheading }}">
  <meta property="og:type" content="website">

  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg: {{ theme.bg }};
      --surface: {{ theme.surface }};
      --text: {{ theme.text }};
      --text-muted: {{ theme.text_muted }};
      --accent: {{ theme.accent }};
      --accent-light: {{ theme.accent_light }};
      --border: {{ theme.border }};
      --font-heading: {{ theme.font_heading }};
      --font-body: {{ theme.font_body }};
      --hero-bg: {{ theme.hero_bg }};
      --max-w: 780px;
      --radius: 12px;
    }

    html { scroll-behavior: smooth; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-body);
      font-size: 16px;
      line-height: 1.7;
      -webkit-font-smoothing: antialiased;
    }

    /* ── Navigation ─────────────────────────────── */
    nav {
      position: fixed; top: 0; left: 0; right: 0;
      z-index: 100;
      background: var(--bg);
      border-bottom: 1px solid var(--border);
      padding: 0 2rem;
      height: 60px;
      display: flex; align-items: center; justify-content: space-between;
      backdrop-filter: blur(8px);
    }
    nav .logo {
      font-family: var(--font-heading);
      font-weight: 700; font-size: 1.1rem;
      color: var(--text); text-decoration: none;
    }
    nav ul { list-style: none; display: flex; gap: 2rem; }
    nav ul a {
      color: var(--text-muted); text-decoration: none;
      font-size: 0.9rem; font-weight: 500;
      transition: color .2s;
    }
    nav ul a:hover { color: var(--accent); }

    /* ── Hero ───────────────────────────────────── */
    #hero {
      background: var(--hero-bg);
      min-height: 100vh;
      display: flex; align-items: center;
      padding: 8rem 2rem 6rem;
    }
    .hero-inner { max-width: var(--max-w); margin: 0 auto; }
    .hero-badge {
      display: inline-block;
      background: var(--accent-light);
      color: var(--accent);
      border-radius: 100px; padding: .35rem 1rem;
      font-size: .85rem; font-weight: 500;
      margin-bottom: 2rem;
    }
    h1 {
      font-family: var(--font-heading);
      font-size: clamp(2.8rem, 6vw, 4.5rem);
      font-weight: 700; line-height: 1.1;
      color: {% if theme_name == 'dark' or theme_name == 'creative' %}#f1f5f9{% else %}var(--text){% endif %};
      margin-bottom: 1.5rem;
    }
    .hero-sub {
      font-size: 1.2rem; line-height: 1.7;
      color: {% if theme_name == 'dark' or theme_name == 'creative' %}#94a3b8{% else %}var(--text-muted){% endif %};
      max-width: 540px;
      margin-bottom: 2.5rem;
    }
    .hero-cta {
      display: inline-flex; align-items: center; gap: .5rem;
      background: var(--accent); color: #fff;
      padding: .9rem 2rem; border-radius: var(--radius);
      font-weight: 600; text-decoration: none; font-size: 1rem;
      transition: transform .15s, box-shadow .15s;
    }
    .hero-cta:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,0,0,.15); }

    /* ── Section ────────────────────────────────── */
    section { padding: 6rem 2rem; }
    section:nth-child(even) { background: var(--surface); }
    .section-inner { max-width: var(--max-w); margin: 0 auto; }
    .section-label {
      font-size: .8rem; letter-spacing: .12em; text-transform: uppercase;
      color: var(--accent); font-weight: 600; margin-bottom: .75rem;
    }
    h2 {
      font-family: var(--font-heading);
      font-size: 2.2rem; font-weight: 700; line-height: 1.2;
      margin-bottom: 1.5rem;
    }

    /* ── About ──────────────────────────────────── */
    .about-text { font-size: 1.05rem; color: var(--text-muted); }
    .about-text p + p { margin-top: 1rem; }
    .about-meta {
      display: flex; gap: 2rem; flex-wrap: wrap;
      margin-top: 2.5rem; padding-top: 2rem;
      border-top: 1px solid var(--border);
    }
    .meta-item span { display: block; }
    .meta-item .meta-val { font-weight: 600; font-size: 1.1rem; }
    .meta-item .meta-key { font-size: .85rem; color: var(--text-muted); margin-top: .2rem; }

    /* ── Projects ───────────────────────────────── */
    .projects-grid { display: grid; gap: 1.5rem; }
    .project-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      transition: transform .15s, border-color .15s;
    }
    .project-card:hover { transform: translateY(-2px); border-color: var(--accent); }
    .project-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
    .project-title { font-family: var(--font-heading); font-size: 1.3rem; font-weight: 600; }
    .project-links { display: flex; gap: .75rem; flex-shrink: 0; }
    .project-links a {
      color: var(--text-muted); text-decoration: none; font-size: .85rem;
      border: 1px solid var(--border); border-radius: 8px; padding: .35rem .75rem;
      transition: all .15s;
    }
    .project-links a:hover { color: var(--accent); border-color: var(--accent); }
    .project-desc { margin-top: .75rem; color: var(--text-muted); font-size: .95rem; }
    .tech-tags { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.25rem; }
    .tech-tag {
      background: var(--accent-light); color: var(--accent);
      font-size: .78rem; font-weight: 500; padding: .3rem .75rem;
      border-radius: 100px;
    }

    /* ── Skills ─────────────────────────────────── */
    .skills-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; }
    .skill-group h3 {
      font-size: .85rem; letter-spacing: .08em; text-transform: uppercase;
      color: var(--text-muted); margin-bottom: 1rem;
    }
    .skill-pills { display: flex; flex-wrap: wrap; gap: .5rem; }
    .skill-pill {
      background: var(--bg); border: 1px solid var(--border);
      border-radius: 8px; padding: .4rem .9rem;
      font-size: .9rem; font-weight: 500;
    }
    .skill-highlights { margin-top: 2.5rem; }
    .skill-highlight {
      padding: 1rem 1.25rem; border-left: 3px solid var(--accent);
      margin-bottom: .75rem; background: var(--surface); border-radius: 0 8px 8px 0;
      font-size: .95rem;
    }

    /* ── Contact ────────────────────────────────── */
    .contact-box {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 3rem;
      display: grid; grid-template-columns: 1fr 1fr; gap: 3rem;
      align-items: center;
    }
    .contact-headline { font-family: var(--font-heading); font-size: 1.8rem; font-weight: 700; margin-bottom: 1rem; }
    .contact-sub { color: var(--text-muted); margin-bottom: 2rem; }
    .contact-available {
      display: inline-block; background: #dcfce7; color: #15803d;
      border-radius: 100px; padding: .35rem 1rem; font-size: .85rem; font-weight: 500;
    }
    .contact-links { display: flex; flex-direction: column; gap: 1rem; }
    .contact-link {
      display: flex; align-items: center; gap: .75rem;
      color: var(--text); text-decoration: none; font-weight: 500;
      padding: .75rem 1rem; border: 1px solid var(--border); border-radius: 10px;
      transition: all .15s;
    }
    .contact-link:hover { border-color: var(--accent); color: var(--accent); }
    .contact-link .link-icon { font-size: 1.1rem; }

    /* ── Footer ─────────────────────────────────── */
    footer {
      text-align: center; padding: 3rem 2rem;
      border-top: 1px solid var(--border);
      color: var(--text-muted); font-size: .85rem;
    }
    footer a { color: var(--accent); text-decoration: none; }

    /* ── Responsive ─────────────────────────────── */
    @media (max-width: 640px) {
      nav ul { display: none; }
      .contact-box { grid-template-columns: 1fr; }
      h1 { font-size: 2.4rem; }
    }

    /* ── Fade-in animation ──────────────────────── */
    .fade-in { opacity: 0; transform: translateY(20px); transition: opacity .5s, transform .5s; }
    .fade-in.visible { opacity: 1; transform: none; }
  </style>
</head>
<body>

<!-- Navigation -->
<nav>
  <a href="#hero" class="logo">{{ content.hero.name.split()[0] }}</a>
  <ul>
    <li><a href="#about">About</a></li>
    <li><a href="#projects">Projects</a></li>
    <li><a href="#skills">Skills</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul>
</nav>

<!-- Hero -->
<section id="hero">
  <div class="hero-inner fade-in">
    <div class="hero-badge">✦ Open to opportunities</div>
    <h1>{{ content.hero.headline }}</h1>
    <p class="hero-sub">{{ content.hero.subheading }}</p>
    <a href="#projects" class="hero-cta">{{ content.hero.cta_text }} →</a>
  </div>
</section>

<!-- About -->
<section id="about">
  <div class="section-inner fade-in">
    <p class="section-label">About</p>
    <h2>Who I Am</h2>
    <div class="about-text">
      <p>{{ content.about.bio_paragraph_1 }}</p>
      <p>{{ content.about.bio_paragraph_2 }}</p>
    </div>
    <div class="about-meta">
      {% if content.about.years_experience %}
      <div class="meta-item">
        <span class="meta-val">{{ content.about.years_experience }}+</span>
        <span class="meta-key">Years experience</span>
      </div>
      {% endif %}
      <div class="meta-item">
        <span class="meta-val">{{ content.projects|length }}</span>
        <span class="meta-key">Featured projects</span>
      </div>
      {% if content.about.currently %}
      <div class="meta-item">
        <span class="meta-val">{{ content.about.currently }}</span>
        <span class="meta-key">Currently</span>
      </div>
      {% endif %}
    </div>
  </div>
</section>

<!-- Projects -->
<section id="projects">
  <div class="section-inner">
    <p class="section-label">Work</p>
    <h2 class="fade-in">Featured Projects</h2>
    <div class="projects-grid">
      {% for project in content.projects %}
      <div class="project-card fade-in">
        <div class="project-header">
          <h3 class="project-title">{{ project.display_name }}</h3>
          <div class="project-links">
            {% if project.github_url %}
            <a href="{{ project.github_url }}" target="_blank" rel="noopener">GitHub ↗</a>
            {% endif %}
            {% if project.live_url %}
            <a href="{{ project.live_url }}" target="_blank" rel="noopener">Live ↗</a>
            {% endif %}
          </div>
        </div>
        <p class="project-desc">{{ project.description }}</p>
        {% if project.tech_tags %}
        <div class="tech-tags">
          {% for tag in project.tech_tags[:6] %}
          <span class="tech-tag">{{ tag }}</span>
          {% endfor %}
        </div>
        {% endif %}
      </div>
      {% endfor %}
    </div>
  </div>
</section>

<!-- Skills -->
<section id="skills">
  <div class="section-inner fade-in">
    <p class="section-label">Skills</p>
    <h2>What I Work With</h2>
    <div class="skills-grid">
      {% if content.skills.languages %}
      <div class="skill-group">
        <h3>Languages</h3>
        <div class="skill-pills">
          {% for s in content.skills.languages %}
          <span class="skill-pill">{{ s }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}
      {% if content.skills.frameworks %}
      <div class="skill-group">
        <h3>Frameworks</h3>
        <div class="skill-pills">
          {% for s in content.skills.frameworks %}
          <span class="skill-pill">{{ s }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}
      {% if content.skills.tools %}
      <div class="skill-group">
        <h3>Tools & Infra</h3>
        <div class="skill-pills">
          {% for s in content.skills.tools %}
          <span class="skill-pill">{{ s }}</span>
          {% endfor %}
        </div>
      </div>
      {% endif %}
    </div>
    {% if content.skills.highlights %}
    <div class="skill-highlights">
      {% for h in content.skills.highlights %}
      <div class="skill-highlight">{{ h }}</div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
</section>

<!-- Contact -->
<section id="contact">
  <div class="section-inner fade-in">
    <p class="section-label">Contact</p>
    <div class="contact-box">
      <div>
        <p class="contact-headline">Let's build something together</p>
        <p class="contact-sub">{{ content.contact.available_for }}</p>
        <span class="contact-available">✓ Available for opportunities</span>
      </div>
      <div class="contact-links">
        {% if content.contact.email %}
        <a href="mailto:{{ content.contact.email }}" class="contact-link">
          <span class="link-icon">✉</span> {{ content.contact.email }}
        </a>
        {% endif %}
        {% if content.contact.github_url %}
        <a href="{{ content.contact.github_url }}" target="_blank" rel="noopener" class="contact-link">
          <span class="link-icon">⬡</span> GitHub
        </a>
        {% endif %}
        {% if content.contact.linkedin_url %}
        <a href="{{ content.contact.linkedin_url }}" target="_blank" rel="noopener" class="contact-link">
          <span class="link-icon">in</span> LinkedIn
        </a>
        {% endif %}
        {% if content.contact.twitter_url %}
        <a href="{{ content.contact.twitter_url }}" target="_blank" rel="noopener" class="contact-link">
          <span class="link-icon">✖</span> Twitter / X
        </a>
        {% endif %}
      </div>
    </div>
  </div>
</section>

<!-- Footer -->
<footer>
  Built with <a href="https://portfolioai.app" target="_blank">PortfolioAI</a> · Auto-updated from GitHub
</footer>

<script>
  // Scroll-triggered fade-ins
  const observer = new IntersectionObserver(
    (entries) => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); }),
    { threshold: 0.1 }
  );
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

  // Smooth scroll for nav links
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      document.querySelector(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth' });
    });
  });
</script>
</body>
</html>"""


class SiteBuilder:
    def __init__(self, theme: str = "minimal"):
        self.theme_name = theme if theme in THEMES else "minimal"
        self.theme = THEMES[self.theme_name]

    def render(self, content: dict, github_username: str) -> str:
        """Render the portfolio HTML from content dict."""
        env = Environment(loader=BaseLoader())
        template = env.from_string(PORTFOLIO_TEMPLATE)
        return template.render(
            content=content,
            theme=self.theme,
            theme_name=self.theme_name,
            github_username=github_username,
        )
