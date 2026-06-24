"""Generate static site for GitHub Pages from discovery reports."""

import os
import re
import glob
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

DIST_DIR = "docs"
OUTPUT_DIR = "output"
SITE_TITLE = "GitHub Discovery"
SITE_DESC = "Discover trending GitHub repos before they go viral"
SITE_URL = "https://alloevil.github.io/github-discovery"

LANG_COLORS = {
    "python": "#3572A5", "javascript": "#f1e05a", "typescript": "#3178c6",
    "rust": "#dea584", "go": "#00ADD8", "java": "#b07219", "c": "#555555",
    "c++": "#f34b7d", "c#": "#178600", "ruby": "#701516", "php": "#4F5D95",
    "swift": "#F05138", "kotlin": "#A97BFF", "shell": "#89e051",
    "html": "#e34c26", "css": "#563d7c", "vue": "#41b883", "svelte": "#ff3e00",
    "zig": "#ec915c", "lua": "#000080", "dart": "#00B4AB", "elixir": "#6e4a7e",
}


def lang_color(lang: str) -> str:
    return LANG_COLORS.get(lang.lower(), "#8b949e") if lang else "#8b949e"


def _parse_sections(content: str) -> list[dict]:
    """Parse repo sections from markdown content."""
    repos = []
    for section in re.split(r'### \d+\.', content)[1:]:
        repo = {}
        m = re.search(r'\[([^\]]+)\]\((https://github\.com/[^\)]+)\)', section)
        if m:
            repo['name'] = m.group(1)
            repo['url'] = m.group(2)
            parts = repo['name'].split('/')
            repo['owner'] = parts[0] if len(parts) > 1 else ''
            repo['repo'] = parts[1] if len(parts) > 1 else repo['name']
        for key, pattern in [('stars', r'⭐ Stars \| ([\d,]+)'), ('age', r'📅 Age \| (\d+)'),
                             ('daily', r'🚀 Daily Growth \| ([\d.]+)'), ('language', r'🔤 Language \| (\w+)'),
                             ('score', r'Score: (\d+)/100'), ('source', r'📡 Source \| (\w+)')]:
            m = re.search(pattern, section)
            if m:
                repo[key] = m.group(1).replace(',', '') if key == 'stars' else m.group(1)
        m = re.search(r'> (.+)', section)
        if m:
            repo['description'] = m.group(1).strip()
        if 'name' in repo:
            repos.append(repo)
    return repos


def parse_report(filepath: str) -> tuple[list[dict], list[dict]]:
    """Parse report, returning (first_timers, repeat_performers)."""
    with open(filepath) as f:
        content = f.read()
    
    # Split into First Timers and Repeat Performers sections
    if 'First Timers' in content and 'Repeat Performers' in content:
        parts = content.split('Repeat Performers')
        first_part = parts[0]
        repeat_part = parts[1] if len(parts) > 1 else ''
        return _parse_sections(first_part), _parse_sections(repeat_part)
    else:
        return _parse_sections(content), []


def card(r: dict) -> str:
    owner = r.get('owner', '')
    repo_name = r.get('repo', r.get('name', '?'))
    url = r.get('url', '#')
    stars = r.get('stars', '0')
    daily = r.get('daily', '0')
    score = r.get('score', '0')
    desc = r.get('description', 'No description')
    lang = r.get('language', '')
    color = lang_color(lang)
    avatar = f"https://github.com/{owner}.png" if owner else ""
    si = int(score)
    sc = "score-gold" if si >= 98 else ("score-high" if si >= 95 else ("score-mid" if si >= 90 else "score-low"))
    lang_html = f'<span class="meta-item"><span class="lang-dot" style="background:{color}"></span>{lang}</span>' if lang else ''
    lang_attr = lang.lower() if lang else 'unknown'
    return f'''    <div class="Box-row" data-lang="{lang_attr}">
      <div class="Box-row-header">
        <img class="avatar" src="{avatar}" alt="{owner}" onerror="this.style.display='none'">
        <h3><a href="{url}"><span class="owner">{owner} /</span> {repo_name}</a></h3>
      </div>
      <div class="Box-row-desc">{desc}</div>
      <div class="Box-row-meta">
        {lang_html}
        <span class="meta-item"><svg viewBox="0 0 16 16" width="14" height="14" fill="#e3b341"><path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25z"/></svg> {stars}</span>
        <span class="meta-item"><svg viewBox="0 0 16 16" width="14" height="14" fill="#3fb950"><path d="M8 14V2.5l-6 6H0v7h8z"/></svg> {daily}/day</span>
        <span class="score-pill {sc}">Score: {score}</span>
      </div>
    </div>'''


def generate_index_html(reports: list[tuple[str, list[dict], list[dict]]]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_repos = sum(len(ft) + len(rp) for _, ft, rp in reports)
    top_score = reports[0][1][0]['score'] if reports and reports[0][1] else '?'

    sections = ""
    date_tabs = ""
    for i, (date_str, first_timers, repeat_performers) in enumerate(reports[:7]):
        active_cls = ' active' if i == 0 else ''
        date_tabs += f'        <button class="date-tab{active_cls}" onclick="switchDate(\'{date_str}\')">{date_str}</button>\n'
        section_cards = ""
        # First Timers section
        if first_timers:
            cards = "\n".join(card(r) for r in first_timers[:10])
            section_cards += f"""
      <div class="date-heading">
        <h2>⭐ {date_str} — First Timers</h2>
        <span class="count">{len(first_timers)} repos</span>
      </div>
{cards}
"""
        # Repeat Performers section
        if repeat_performers:
            cards = "\n".join(card(r) for r in repeat_performers[:5])
            section_cards += f"""
      <div class="date-heading">
        <h2>🔄 {date_str} — Repeat Performers</h2>
        <span class="count">{len(repeat_performers)} repos</span>
      </div>
{cards}
"""
        display = '' if i == 0 else 'none'
        sections += f'      <div class="date-section" data-date="{date_str}" style="display:{display}">\n{section_cards}      </div>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🔥 GitHub Discovery — {now}</title>
  <meta property="og:title" content="GitHub Discovery — {now}" />
  <meta property="og:description" content="{SITE_DESC}" />
  <link rel="alternate" type="application/rss+xml" title="RSS" href="{SITE_URL}/feed.xml" />
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Share Tech Mono', 'Courier New', monospace; background: #0a0a0f; color: #c0c0d0; line-height: 1.6; position: relative; overflow-x: hidden; }}
    /* Scanline overlay */
    body::before {{ content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px); pointer-events: none; z-index: 9999; }}
    /* Noise texture */
    body::after {{ content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E"); pointer-events: none; z-index: 9998; }}
    a {{ color: #00ffff; text-decoration: none; transition: all 0.2s; }}
    a:hover {{ color: #ff00ff; text-shadow: 0 0 8px #ff00ff; text-decoration: none; }}
    a:active {{ opacity: 0.7; }}

    .page-header {{ background: linear-gradient(180deg, #0f0f1a 0%, #0a0a0f 100%); border-bottom: 1px solid #00ffff33; padding: 16px 0; position: relative; }}
    .page-header::after {{ content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 1px; background: linear-gradient(90deg, transparent, #00ffff, #ff00ff, #00ffff, transparent); opacity: 0.6; }}
    .container {{ max-width: 960px; margin: 0 auto; padding: 0 24px; }}
    .page-body {{ padding: 24px 0 48px; }}

    .site-header {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; }}
    .site-title {{ display: flex; align-items: center; gap: 12px; }}
    .site-title h1 {{ font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 900; color: #fff; letter-spacing: 2px; text-transform: uppercase; text-shadow: 0 0 10px #00ffff88, 0 0 30px #00ffff44; }}
    .site-title .emoji {{ font-size: 28px; filter: drop-shadow(0 0 6px #ff6600); }}
    .site-nav {{ display: flex; align-items: center; gap: 12px; }}
    .site-nav a {{ color: #e6edf3; font-size: 13px; font-weight: 500; padding: 8px 18px; border: 1px solid #00ffff55; clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px); transition: all 0.2s; letter-spacing: 1px; text-transform: uppercase; font-family: 'Orbitron', sans-serif; font-size: 11px; }}
    .site-nav a:hover {{ text-decoration: none; background: #00ffff11; box-shadow: 0 0 15px #00ffff33, inset 0 0 15px #00ffff11; }}
    .btn-rss {{ background: linear-gradient(135deg, #ff00ff22, #ff00ff44); border-color: #ff00ff55; color: #ff88ff !important; }}
    .btn-rss:hover {{ background: #ff00ff22; box-shadow: 0 0 15px #ff00ff33, inset 0 0 15px #ff00ff11; }}
    .btn-gh {{ background: transparent; }}
    .btn-gh:hover {{ background: #00ffff11; }}

    .summary-bar {{ display: flex; gap: 24px; padding: 20px 0; border-bottom: 1px solid #ffffff0a; margin-bottom: 20px; flex-wrap: wrap; }}
    .summary-item {{ text-align: center; flex: 1; min-width: 80px; padding: 16px 8px; background: linear-gradient(135deg, #00ffff08, #ff00ff05); border: 1px solid #00ffff15; clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px); }}
    .summary-item .num {{ font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 900; color: #00ffff; display: block; line-height: 1.2; text-shadow: 0 0 10px #00ffff66; }}
    .summary-item .label {{ font-size: 10px; color: #666680; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; }}

    .date-heading {{ display: flex; align-items: center; gap: 12px; margin: 36px 0 14px; padding: 10px 0; border-bottom: 1px solid #00ffff22; position: relative; }}
    .date-heading::before {{ content: '>'; color: #ff00ff; font-weight: 700; margin-right: 4px; }}
    .date-heading h2 {{ font-family: 'Orbitron', sans-serif; font-size: 15px; font-weight: 700; color: #fff; letter-spacing: 1px; text-transform: uppercase; }}
    .date-heading .count {{ font-size: 11px; color: #00ffff; background: #00ffff11; padding: 2px 10px; border: 1px solid #00ffff33; white-space: nowrap; clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px); }}

    .Box-row {{ padding: 16px 18px; border: 1px solid #ffffff0f; margin-bottom: 10px; transition: all 0.25s ease; cursor: pointer; position: relative; background: linear-gradient(135deg, #0a0a14, #0d0d1a); clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); }}
    .Box-row::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, #00ffff44, transparent); opacity: 0; transition: opacity 0.3s; }}
    .Box-row:hover {{ border-color: #00ffff44; background: linear-gradient(135deg, #0a0a1a, #0f0f22); transform: translateY(-2px); box-shadow: 0 0 20px #00ffff11, 0 4px 12px rgba(0,0,0,0.3), inset 0 0 30px #00ffff05; }}
    .Box-row:hover::before {{ opacity: 1; }}
    .Box-row:active {{ transform: translateY(0); }}
    .Box-row-header {{ display: flex; align-items: flex-start; gap: 10px; }}
    .Box-row-header .avatar {{ width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; margin-top: 2px; border: 1px solid #00ffff33; filter: saturate(0.8); }}
    .Box-row-header h3 {{ font-size: 15px; font-weight: 600; line-height: 1.3; font-family: 'Share Tech Mono', monospace; }}
    .Box-row-header h3 a {{ color: #00ffff; transition: all 0.2s; }}
    .Box-row-header h3 a:hover {{ color: #ff00ff; text-shadow: 0 0 8px #ff00ff66; text-decoration: none; }}
    .Box-row-header .owner {{ color: #666680; font-weight: 400; }}
    .Box-row-desc {{ font-size: 13px; color: #8888a0; line-height: 1.5; padding-left: 36px; margin-top: 4px; }}
    .Box-row-meta {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding-left: 36px; margin-top: 8px; font-size: 11px; }}
    .meta-item {{ display: inline-flex; align-items: center; gap: 4px; color: #666680; white-space: nowrap; }}
    .lang-dot {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.1); }}
    .score-pill {{ padding: 2px 10px; font-size: 11px; font-weight: 700; white-space: nowrap; font-family: 'Orbitron', sans-serif; letter-spacing: 0.5px; clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px); }}
    .score-high {{ background: #00ff8822; color: #00ff88; border: 1px solid #00ff8844; text-shadow: 0 0 6px #00ff8844; }}
    .score-mid {{ background: #00ffff22; color: #00ffff; border: 1px solid #00ffff44; }}
    .score-low {{ background: #ffffff08; color: #444460; border: 1px solid #ffffff11; }}
    .score-gold {{ background: linear-gradient(135deg, #ffaa0022, #ff660022); color: #ffaa00; border: 1px solid #ffaa0044; text-shadow: 0 0 8px #ffaa0044; }}

    .date-nav {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; padding: 12px 0; border-bottom: 1px solid #00ffff15; }}
    .date-tab {{ padding: 8px 16px; border: 1px solid #ffffff15; background: #ffffff05; color: #666680; font-size: 13px; cursor: pointer; transition: all 0.2s; font-family: 'Orbitron', sans-serif; font-weight: 700; letter-spacing: 0.5px; clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px); }}
    .date-tab:hover {{ border-color: #00ffff44; color: #00ffff; background: #00ffff08; }}
    .date-tab.active {{ background: linear-gradient(135deg, #00ffff18, #ff00ff10); border-color: #00ffff66; color: #00ffff; box-shadow: 0 0 12px #00ffff22, inset 0 0 12px #00ffff08; text-shadow: 0 0 6px #00ffff66; }}

    .lang-filter {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }}
    .lang-filter button {{ padding: 6px 14px; border: 1px solid #ffffff15; background: #ffffff05; color: #8888a0; font-size: 12px; cursor: pointer; transition: all 0.2s; white-space: nowrap; font-family: 'Share Tech Mono', monospace; letter-spacing: 0.5px; clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px); }}
    .lang-filter button:hover {{ border-color: #00ffff44; color: #00ffff; background: #00ffff08; }}
    .lang-filter button.active {{ background: #00ffff15; border-color: #00ffff55; color: #00ffff; box-shadow: 0 0 10px #00ffff22; }}
    .subscribe-box {{ margin: 24px 0 20px; padding: 20px; background: linear-gradient(135deg, #00ffff06, #ff00ff04); border: 1px solid #00ffff22; position: relative; clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); }}
    .subscribe-box::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, #00ffff66, #ff00ff44, #00ffff66, transparent); }}
    .subscribe-title {{ font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 700; color: #00ffff; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; text-shadow: 0 0 8px #00ffff44; }}
    .subscribe-desc {{ font-size: 12px; color: #666680; margin-bottom: 14px; }}
    .subscribe-btn-link {{ display: inline-block; padding: 10px 24px; background: linear-gradient(135deg, #00ffff18, #ff00ff10); border: 1px solid #00ffff55; color: #00ffff; font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; text-decoration: none; cursor: pointer; transition: all 0.2s; clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px); }}
    .subscribe-btn-link:hover {{ background: linear-gradient(135deg, #00ffff28, #ff00ff18); box-shadow: 0 0 15px #00ffff33, inset 0 0 15px #00ffff11; color: #fff; }}
    .subscribe-form {{ display: flex; gap: 10px; }}
    .subscribe-form input[type="email"] {{ flex: 1; padding: 10px 14px; background: #0a0a14; border: 1px solid #ffffff18; color: #c0c0d0; font-family: 'Share Tech Mono', monospace; font-size: 13px; outline: none; transition: all 0.2s; clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px); }}
    .subscribe-form input[type="email"]::placeholder {{ color: #444460; }}
    .subscribe-form input[type="email"]:focus {{ border-color: #00ffff55; box-shadow: 0 0 10px #00ffff22, inset 0 0 10px #00ffff08; }}
    .subscribe-form button {{ padding: 10px 20px; background: linear-gradient(135deg, #00ffff18, #ff00ff10); border: 1px solid #00ffff55; color: #00ffff; font-family: 'Orbitron', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; cursor: pointer; transition: all 0.2s; white-space: nowrap; clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px); }}
    .subscribe-form button:hover {{ background: linear-gradient(135deg, #00ffff28, #ff00ff18); box-shadow: 0 0 15px #00ffff33, inset 0 0 15px #00ffff11; color: #fff; }}
    .subscribe-form button:active {{ transform: scale(0.97); }}
    .subscribe-hint {{ font-size: 11px; color: #444460; margin-top: 10px; }}

    .site-footer {{ border-top: 1px solid #ffffff0a; padding: 32px 0; text-align: center; color: #333350; font-size: 12px; margin-top: 48px; }}
    .site-footer p {{ margin-bottom: 8px; }}
    .site-footer a {{ color: #555570; }}
    .site-footer a:hover {{ color: #00ffff; }}

    @media (max-width: 768px) {{
      .container {{ padding: 0 16px; }}
      .site-header {{ flex-direction: column; align-items: flex-start; gap: 12px; }}
      .site-nav {{ width: 100%; }}
      .site-nav a {{ flex: 1; text-align: center; padding: 10px 12px; font-size: 10px; }}
      .summary-bar {{ gap: 12px; padding: 16px 0; }}
      .summary-item {{ min-width: 60px; padding: 12px 6px; }}
      .summary-item .num {{ font-size: 22px; }}
      .summary-item .label {{ font-size: 9px; }}
      .Box-row {{ padding: 14px; }}
      .Box-row-desc {{ padding-left: 0; }}
      .Box-row-meta {{ padding-left: 0; gap: 10px; margin-top: 10px; }}
      .Box-row-header h3 {{ font-size: 14px; }}
      .date-heading {{ margin: 28px 0 12px; }}
      .date-heading h2 {{ font-size: 13px; }}
      .date-nav {{ gap: 4px; margin-bottom: 16px; }}
      .date-tab {{ padding: 6px 12px; font-size: 11px; }}
      .subscribe-btn-link {{ width: 100%; text-align: center; padding: 12px; }}
      .subscribe-form {{ flex-direction: column; }}
      .subscribe-form button {{ padding: 12px; }}
    }}

    @media (max-width: 480px) {{
      .lang-filter {{ gap: 4px; }}
      .lang-filter button {{ padding: 5px 10px; font-size: 11px; }}
      .summary-bar {{ gap: 8px; }}
      .Box-row-meta {{ gap: 8px; font-size: 10px; }}
      .score-pill {{ padding: 1px 8px; font-size: 10px; }}
      .date-tab {{ padding: 5px 10px; font-size: 10px; }}
    }}
  </style>
</head>
<body>
  <header class="page-header">
    <div class="container">
      <div class="site-header">
        <div class="site-title">
          <span class="emoji">🔥</span>
          <h1>GitHub Discovery</h1>
        </div>
        <nav class="site-nav">
          <a class="btn-gh" href="https://github.com/alloevil/github-discovery">⭐ GitHub</a>
          <a class="btn-rss" href="{SITE_URL}/feed.xml">📡 RSS</a>
        </nav>
      </div>
    </div>
  </header>

  <main class="page-body">
    <div class="container">
      <div class="summary-bar">
        <div class="summary-item"><span class="num">{len(reports)}</span><span class="label">Days Tracked</span></div>
        <div class="summary-item"><span class="num">{total_repos}</span><span class="label">Repos Discovered</span></div>
        <div class="summary-item"><span class="num">{top_score}</span><span class="label">Top Score</span></div>
      </div>
      <div class="subscribe-box">
        <div class="subscribe-title">📡 Subscribe to GitHub Discovery</div>
        <div class="subscribe-desc">Get the top trending repos delivered to your inbox daily.</div>
        <form class="subscribe-form" onsubmit="handleSubscribe(event)">
          <input type="email" name="email" placeholder="your@email.com" required />
          <button type="submit">Subscribe</button>
        </form>
        <div class="subscribe-success">✅ Subscribed! You'll receive daily updates.</div>
      </div>
      <div class="date-nav">
{date_tabs}      </div>
      <div class="lang-filter">
        <button class="active" onclick="filterLang('all')">All</button>
        <button onclick="filterLang('python')">Python</button>
        <button onclick="filterLang('typescript')">TypeScript</button>
        <button onclick="filterLang('javascript')">JavaScript</button>
        <button onclick="filterLang('rust')">Rust</button>
        <button onclick="filterLang('go')">Go</button>
        <button onclick="filterLang('java')">Java</button>
        <button onclick="filterLang('c++')">C++</button>
        <button onclick="filterLang('other')">Other</button>
      </div>
{sections}
    </div>
  </main>

  <script>
    function handleSubscribe(e) {{
      e.preventDefault();
      const form = e.target;
      const btn = form.querySelector('button');
      const email = form.querySelector('input[name="email"]').value;
      if (!email) return;
      btn.textContent = '...';
      btn.disabled = true;
      fetch('https://script.google.com/macros/s/AKfycbzCnDRaclzhiaIlj7Jo9mdXXKDp-wHe51TvNTjMFdDVde8_b3oLAwfvQjr-eV3MpfnYbA/exec', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ email: email }}),
        mode: 'no-cors'
      }}).then(() => {{
        form.style.display = 'none';
        form.nextElementSibling.style.display = 'block';
      }}).catch(() => {{
        form.style.display = 'none';
        form.nextElementSibling.style.display = 'block';
      }});
    }}
    function switchDate(date) {{
      document.querySelectorAll('.date-tab').forEach(t => t.classList.remove('active'));
      event.target.classList.add('active');
      document.querySelectorAll('.date-section').forEach(s => {{
        s.style.display = s.getAttribute('data-date') === date ? '' : 'none';
      }});
      // Reset lang filter to All when switching date
      document.querySelectorAll('.lang-filter button').forEach(b => b.classList.remove('active'));
      document.querySelector('.lang-filter button').classList.add('active');
      document.querySelectorAll('.Box-row').forEach(row => {{ row.style.display = ''; }});
    }}
    function filterLang(lang) {{
      document.querySelectorAll('.lang-filter button').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      document.querySelectorAll('.Box-row').forEach(row => {{
        const rowLang = row.getAttribute('data-lang') || 'unknown';
        if (lang === 'all') {{
          row.style.display = '';
        }} else if (lang === 'other') {{
          const mainLangs = ['python','typescript','javascript','rust','go','java','c++'];
          row.style.display = mainLangs.includes(rowLang) ? 'none' : '';
        }} else {{
          row.style.display = rowLang === lang ? '' : 'none';
        }}
      }});
    }}
  </script>

  <footer class="site-footer">
    <div class="container">
      <p>Generated by <a href="https://github.com/alloevil/github-discovery">GitHub Discovery</a> · Updated daily at 18:00 CST</p>
      <p><a href="{SITE_URL}/feed.xml">📡 RSS Feed</a> · Inspired by <a href="https://github.com/thechangelog/nightly">Changelog Nightly</a></p>
    </div>
  </footer>
</body>
</html>"""


def generate_rss(reports: list[tuple[str, list[dict], list[dict]]]) -> str:
    rss = Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    ch = SubElement(rss, 'channel')
    SubElement(ch, 'title').text = SITE_TITLE
    SubElement(ch, 'description').text = SITE_DESC
    SubElement(ch, 'link').text = SITE_URL
    SubElement(ch, 'language').text = 'en'
    SubElement(ch, 'lastBuildDate').text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    al = SubElement(ch, 'atom:link')
    al.set('href', f'{SITE_URL}/feed.xml')
    al.set('rel', 'self')
    al.set('type', 'application/rss+xml')
    for date_str, first_timers, repeat_performers in reports[:10]:
        all_repos = first_timers[:5] + repeat_performers[:3]
        for r in all_repos:
            item = SubElement(ch, 'item')
            SubElement(item, 'title').text = f"🔥 {r.get('name','?')} — {r.get('stars','?')}⭐ ({r.get('daily','?')}/day)"
            SubElement(item, 'description').text = f"{r.get('description','')}\n\nScore: {r.get('score','?')}/100 | Language: {r.get('language','?')}"
            SubElement(item, 'link').text = r.get('url', SITE_URL)
            SubElement(item, 'guid').text = f"{r.get('url','')}#{date_str}"
            SubElement(item, 'pubDate').text = datetime.strptime(date_str, '%Y-%m-%d').strftime('%a, %d %b %Y 18:00:00 +0000')
    xml_str = tostring(rss, encoding='unicode', xml_declaration=False)
    pretty = parseString(xml_str).toprettyxml(indent='  ', encoding=None)
    lines = pretty.split('\n')
    return '\n'.join(lines) if lines and lines[0].startswith('<?xml') else '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty


def main():
    os.makedirs(DIST_DIR, exist_ok=True)
    report_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'discovery-*.md')), reverse=True)
    reports = []  # list of (date, first_timers, repeat_performers)
    for f in report_files:
        m = re.search(r'discovery-(\d{4}-\d{2}-\d{2})\.md', f)
        if m:
            first, repeat = parse_report(f)
            if first or repeat:
                reports.append((m.group(1), first, repeat))
    if not reports:
        print("[WARN] No reports found")
        return
    with open(os.path.join(DIST_DIR, 'index.html'), 'w') as f:
        f.write(generate_index_html(reports))
    with open(os.path.join(DIST_DIR, 'feed.xml'), 'w') as f:
        f.write(generate_rss(reports))
    print(f"[OK] index.html ({len(reports)} reports)")
    print("[OK] feed.xml")


if __name__ == "__main__":
    main()
