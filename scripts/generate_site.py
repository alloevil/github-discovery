"""Generate static site for GitHub Pages from discovery reports."""

import os
import re
import glob
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

DIST_DIR = "dist"
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


def parse_report(filepath: str) -> list[dict]:
    with open(filepath) as f:
        content = f.read()
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
    sc = "score-high" if si >= 95 else ("score-mid" if si >= 90 else "score-low")
    lang_html = f'<span class="meta-item"><span class="lang-dot" style="background:{color}"></span>{lang}</span>' if lang else ''
    return f'''    <div class="Box-row">
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


def generate_index_html(reports: list[tuple[str, list[dict]]]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_repos = sum(len(r) for _, r in reports)
    top_score = reports[0][1][0]['score'] if reports and reports[0][1] else '?'

    sections = ""
    for date_str, repos in reports[:7]:
        cards = "\n".join(card(r) for r in repos[:10])
        sections += f"""
      <div class="date-heading">
        <h2>📅 {date_str}</h2>
        <span class="count">{len(repos)} repos</span>
      </div>
{cards}
"""

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
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; background: #0d1117; color: #e6edf3; line-height: 1.5; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ color: #79c0ff; text-decoration: underline; }}

    .page-header {{ background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 0; }}
    .container {{ max-width: 1280px; margin: 0 auto; padding: 0 24px; }}
    .page-body {{ padding: 24px 0 48px; }}

    .site-header {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; }}
    .site-title {{ display: flex; align-items: center; gap: 12px; }}
    .site-title h1 {{ font-size: 24px; font-weight: 600; color: #e6edf3; }}
    .site-title .emoji {{ font-size: 28px; }}
    .site-nav {{ display: flex; align-items: center; gap: 12px; }}
    .site-nav a {{ color: #e6edf3; font-size: 14px; font-weight: 500; padding: 6px 16px; border-radius: 6px; transition: all 0.15s; }}
    .site-nav a:hover {{ text-decoration: none; }}
    .btn-rss {{ background: #f0883e; color: #fff !important; }}
    .btn-rss:hover {{ background: #d2701e; }}
    .btn-gh {{ border: 1px solid #30363d; }}
    .btn-gh:hover {{ border-color: #8b949e; background: rgba(136,147,158,0.1); }}

    .summary-bar {{ display: flex; gap: 40px; padding: 24px 0; border-bottom: 1px solid #21262d; margin-bottom: 24px; flex-wrap: wrap; }}
    .summary-item .num {{ font-size: 28px; font-weight: 700; color: #58a6ff; display: block; }}
    .summary-item .label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; }}

    .date-heading {{ display: flex; align-items: center; gap: 12px; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 1px solid #21262d; }}
    .date-heading h2 {{ font-size: 18px; font-weight: 600; color: #e6edf3; }}
    .date-heading .count {{ font-size: 12px; color: #8b949e; background: #21262d; padding: 2px 10px; border-radius: 10px; }}

    .Box-row {{ padding: 16px; border: 1px solid #30363d; border-radius: 6px; margin-bottom: 8px; transition: border-color 0.15s; }}
    .Box-row:hover {{ border-color: rgba(88,166,255,0.25); }}
    .Box-row-header {{ display: flex; align-items: flex-start; gap: 10px; }}
    .Box-row-header .avatar {{ width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; margin-top: 2px; }}
    .Box-row-header h3 {{ font-size: 16px; font-weight: 600; line-height: 1.3; }}
    .Box-row-header h3 a {{ color: #58a6ff; }}
    .Box-row-header .owner {{ color: #8b949e; font-weight: 400; }}
    .Box-row-desc {{ font-size: 14px; color: #8b949e; line-height: 1.5; padding-left: 36px; margin-top: 4px; }}
    .Box-row-meta {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding-left: 36px; margin-top: 8px; font-size: 12px; }}
    .meta-item {{ display: inline-flex; align-items: center; gap: 4px; color: #8b949e; }}
    .lang-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
    .score-pill {{ padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
    .score-high {{ background: #238636; color: #fff; }}
    .score-mid {{ background: #1f6feb; color: #fff; }}
    .score-low {{ background: #30363d; color: #8b949e; }}

    .site-footer {{ border-top: 1px solid #21262d; padding: 32px 0; text-align: center; color: #484f58; font-size: 13px; margin-top: 48px; }}
    .site-footer p {{ margin-bottom: 8px; }}
    .site-footer a {{ color: #8b949e; }}

    @media (max-width: 768px) {{
      .container {{ padding: 0 16px; }}
      .site-header {{ flex-direction: column; align-items: flex-start; }}
      .summary-bar {{ gap: 20px; }}
      .summary-item .num {{ font-size: 22px; }}
      .Box-row-desc, .Box-row-meta {{ padding-left: 0; }}
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
{sections}
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>Generated by <a href="https://github.com/alloevil/github-discovery">GitHub Discovery</a> · Updated daily at 18:00 CST</p>
      <p><a href="{SITE_URL}/feed.xml">📡 RSS Feed</a> · Inspired by <a href="https://github.com/thechangelog/nightly">Changelog Nightly</a></p>
    </div>
  </footer>
</body>
</html>"""


def generate_rss(reports: list[tuple[str, list[dict]]]) -> str:
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
    for date_str, repos in reports[:10]:
        for r in repos[:5]:
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
    reports = []
    for f in report_files:
        m = re.search(r'discovery-(\d{4}-\d{2}-\d{2})\.md', f)
        if m:
            repos = parse_report(f)
            if repos:
                reports.append((m.group(1), repos))
    if not reports:
        print("[WARN] No reports found")
        return
    with open(os.path.join(DIST_DIR, 'index.html'), 'w') as f:
        f.write(generate_index_html(reports))
    print(f"[OK] index.html ({len(reports)} reports)")
    with open(os.path.join(DIST_DIR, 'feed.xml'), 'w') as f:
        f.write(generate_rss(reports))
    print("[OK] feed.xml")


if __name__ == "__main__":
    main()
