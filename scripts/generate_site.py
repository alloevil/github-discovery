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

# Language colors (GitHub-style)
LANG_COLORS = {
    "python": "#3572A5", "javascript": "#f1e05a", "typescript": "#3178c6",
    "rust": "#dea584", "go": "#00ADD8", "java": "#b07219", "c": "#555555",
    "c++": "#f34b7d", "c#": "#178600", "ruby": "#701516", "php": "#4F5D95",
    "swift": "#F05138", "kotlin": "#A97BFF", "scala": "#c22d40",
    "shell": "#89e051", "html": "#e34c26", "css": "#563d7c",
    "vue": "#41b883", "svelte": "#ff3e00", "zig": "#ec915c",
    "lua": "#000080", "dart": "#00B4AB", "elixir": "#6e4a7e",
    "haskell": "#5e5086", "julia": "#a270ba", "r": "#198CE7",
    "scala": "#c22d40", "objective-c": "#438eff", "assembly": "#6E4C13",
}


def lang_color(language: str) -> str:
    return LANG_COLORS.get(language.lower(), "#8b949e")


def parse_report(filepath: str) -> list[dict]:
    """Parse a discovery markdown report into structured data."""
    with open(filepath) as f:
        content = f.read()

    repos = []
    sections = re.split(r'### \d+\.', content)[1:]
    for section in sections:
        repo = {}
        link_match = re.search(r'\[([^\]]+)\]\((https://github\.com/[^\)]+)\)', section)
        if link_match:
            repo['name'] = link_match.group(1)
            repo['url'] = link_match.group(2)
            repo['owner'] = repo['name'].split('/')[0] if '/' in repo['name'] else ''
            repo['repo'] = repo['name'].split('/')[1] if '/' in repo['name'] else repo['name']

        stars_match = re.search(r'⭐ Stars \| ([\d,]+)', section)
        if stars_match:
            repo['stars'] = stars_match.group(1).replace(',', '')

        age_match = re.search(r'📅 Age \| (\d+) days?', section)
        if age_match:
            repo['age'] = age_match.group(1)

        daily_match = re.search(r'🚀 Daily Growth \| ([\d.]+)', section)
        if daily_match:
            repo['daily'] = daily_match.group(1)

        lang_match = re.search(r'🔤 Language \| (\w+)', section)
        if lang_match:
            repo['language'] = lang_match.group(1)

        score_match = re.search(r'Score: (\d+)/100', section)
        if score_match:
            repo['score'] = score_match.group(1)

        desc_match = re.search(r'> (.+)', section)
        if desc_match:
            repo['description'] = desc_match.group(1).strip()

        source_match = re.search(r'📡 Source \| (\w+)', section)
        if source_match:
            repo['source'] = source_match.group(1)

        if 'name' in repo:
            repos.append(repo)

    return repos


def repo_card_html(repo: dict, rank: int) -> str:
    """Generate a single repo card in Nightly style."""
    name = repo.get('name', 'unknown')
    url = repo.get('url', '#')
    owner = repo.get('owner', '')
    repo_name = repo.get('repo', name)
    stars = repo.get('stars', '0')
    daily = repo.get('daily', '0')
    score = repo.get('score', '0')
    desc = repo.get('description', 'No description')
    lang = repo.get('language', '')
    lang_cls = lang.lower().replace('+', 'plusplus').replace('#', 'sharp') if lang else 'default'
    color = lang_color(lang)
    avatar = f"https://github.com/{owner}.png" if owner else ""

    # Score badge color
    score_int = int(score)
    if score_int >= 95:
        badge_color = "#3fb950"  # green
    elif score_int >= 90:
        badge_color = "#58a6ff"  # blue
    else:
        badge_color = "#8b949e"  # grey

    return f"""
    <div class="repository">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr class="stats">
          <td width="28" valign="top">
            <a href="https://github.com/{owner}" title="{owner}">
              <img class="avatar" src="{avatar}" width="20" height="20" onerror="this.style.display='none'">
            </a>
          </td>
          <td valign="middle">
            <p>
              <span class="score-badge" style="background:{badge_color}">{score}</span>
              <span title="Total Stars"><img height="10" alt="Star" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0iI2UzYzMwMCI+PHBhdGggZD0iTTggLjI1YS43NS43NSAwIDAgMSAuNjczLjQxOGwxLjg4MiAzLjgxNSA0LjIxLjYxMmEuNzUuNzUgMCAwIC40MTYgMS4yNzlsLTMuMDQ2IDIuOTcuNzE5IDQuMTkyYS43NS43NSAwIDAgMS0xLjA4OC43OTFMOCAxMi4zNDdsLTMuNzY2IDEuOTlhLjc1Ljc1IDAgMCAxLTEuMDg4LS43OWwuNzItNC4xOUwuMjkzIDYuODdhLjc1Ljc1IDAgMCAuNDE2LTEuMjhsNC4yMS0uNjEzTDEuMzI3LjY2OEEuNzUuNzUgMCAwIDEgMi4wMDQuMjVIOHoiLz48L3N2Zz4=" />&nbsp;{stars}</span>
              &nbsp;&nbsp;
              <span title="Daily Growth"><img height="10" alt="Up" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0iIzNiODJmNiI+PHBhdGggZD0iTTggMTRWMS41bC02IDZIMHY3aDhoMHoiLz48L3N2Zz4=" />&nbsp;{daily}/d</span>
              {'&nbsp;&nbsp;<span class="lang-dot" style="background:' + color + '"></span>&nbsp;<a class="repository-language" href="https://github.com/trending/' + lang.lower() + '">' + lang + '</a>' if lang else ''}
            </p>
          </td>
        </tr>
        <tr class="about">
          <td width="28" valign="top"></td>
          <td valign="top">
            <h3><a href="{url}" title="{name}">{name}</a></h3>
            <p>{desc}</p>
          </td>
        </tr>
      </table>
    </div>
    <hr class="separator">
"""


def generate_index_html(reports: list[tuple[str, list[dict]]]) -> str:
    """Generate Nightly-style index.html."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build repo sections by date
    sections_html = ""
    for date_str, repos in reports[:7]:  # last 7 days
        cards = ""
        for i, repo in enumerate(repos[:10]):
            cards += repo_card_html(repo, i + 1)

        sections_html += f"""
    <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td width="100%">
          <table width="780" cellpadding="20" cellspacing="0" border="0" align="center">
            <tr>
              <td class="section" width="780">
                <h2>🔥 {date_str} &mdash; Top Discoveries</h2>
                <div class="repositories">
                  {cards}
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
"""

    # Archive links
    archive_links = ""
    for date_str, repos in reports[:30]:
        repo_count = len(repos)
        archive_links += f'          <a href="#{date_str}">{date_str}</a> ({repo_count} repos)<br>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <title>GitHub Discovery - {now}</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta property="og:title" content="GitHub Discovery - {now}" />
  <meta property="og:description" content="{SITE_DESC}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{SITE_URL}" />
  <link rel="alternate" type="application/rss+xml" title="GitHub Discovery RSS" href="{SITE_URL}/feed.xml" />
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; background: #0d1117; color: #a8a8a8; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    /* Top bar */
    .top-bar {{ background: #010409; padding: 8px 0; }}
    .top-bar p {{ font-size: 12px; line-height: 28px; text-align: center; color: #8b949e; }}
    .top-bar a {{ color: #8b949e; }}

    /* Wrapper */
    .wrapper {{ background: #0d1117; }}

    /* Header */
    .header {{ padding: 30px 20px 10px; }}
    .header h1 {{ color: #fff; font-size: 24px; font-weight: 600; }}
    .header .subtitle {{ color: #8b949e; font-size: 14px; margin-top: 6px; }}
    .header .subscribe {{ display: inline-block; background: #f0883e; color: #fff; padding: 4px 12px; border-radius: 4px; font-size: 12px; text-decoration: none; margin-top: 10px; }}
    .header .subscribe:hover {{ background: #d2701e; text-decoration: none; }}

    /* Section */
    .section {{ padding-bottom: 20px; }}
    .section h2 {{ color: #fff; font-size: 16px; margin-bottom: 15px; font-weight: 600; }}

    /* Repository */
    .repository {{ margin-bottom: 12px; }}
    .repository h3 {{ font-size: 14px; font-weight: 600; line-height: 1.3; margin-bottom: 4px; }}
    .repository h3 a {{ color: #fff; }}
    .repository p {{ font-size: 13px; line-height: 1.5; color: #8b949e; }}
    .stats p {{ font-size: 12px; line-height: 1; margin-bottom: 4px; }}
    .stats p img {{ margin-right: 2px; vertical-align: middle; }}
    .avatar {{ border-radius: 4px; margin-top: 2px; }}
    .separator {{ border: none; border-top: 1px solid #21262d; margin: 12px 0; }}

    /* Language dot */
    .lang-dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; vertical-align: middle; }}
    .repository-language {{ color: #8b949e; font-size: 12px; }}

    /* Score badge */
    .score-badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; color: #fff; font-size: 11px; font-weight: 600; margin-right: 8px; vertical-align: middle; }}

    /* Footer */
    .footer {{ color: #484f58; padding: 30px 20px; text-align: center; font-size: 13px; }}
    .footer a {{ color: #8b949e; }}
    .footer p {{ margin-bottom: 8px; }}

    /* Cross-promotion */
    .cross-promotion {{ background: #161b22; text-align: center; padding: 14px; border-top: 1px solid #21262d; border-bottom: 1px solid #21262d; }}
    .cross-promotion p {{ color: #8b949e; font-size: 13px; }}
    .cross-promotion a {{ color: #58a6ff; font-weight: 600; }}

    /* Stats bar */
    .stats-bar {{ display: flex; justify-content: center; gap: 30px; padding: 15px 20px; }}
    .stat-item {{ text-align: center; }}
    .stat-num {{ color: #58a6ff; font-size: 20px; font-weight: 700; }}
    .stat-label {{ color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}

    @media (max-width: 480px) {{
      .stats-bar {{ flex-wrap: wrap; gap: 15px; }}
      table {{ width: 100% !important; }}
    }}
  </style>
</head>
<body>
  <!-- Top Bar -->
  <table class="top-bar" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="100%">
        <table width="780" cellpadding="0" cellspacing="0" border="0" align="center">
          <tr>
            <td>
              <p>
                <a href="{SITE_URL}">View on Web</a>
                &nbsp;&nbsp;/&nbsp;&nbsp;
                <a href="https://github.com/alloevil/github-discovery">Fork on GitHub</a>
                &nbsp;&nbsp;/&nbsp;&nbsp;
                <a href="{SITE_URL}/feed.xml">RSS Feed</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Header -->
  <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="100%">
        <table width="780" cellpadding="20" cellspacing="0" border="0" align="center">
          <tr>
            <td class="header" width="780">
              <h1>🔥 GitHub Discovery</h1>
              <p class="subtitle">Discover trending repos before they go viral</p>
              <a class="subscribe" href="{SITE_URL}/feed.xml">📡 Subscribe via RSS</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Stats -->
  <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="100%">
        <table width="780" cellpadding="0" cellspacing="0" border="0" align="center">
          <tr>
            <td class="stats-bar" width="780">
              <div class="stat-item">
                <div class="stat-num">{len(reports)}</div>
                <div class="stat-label">Days Tracked</div>
              </div>
              <div class="stat-item">
                <div class="stat-num">{sum(len(r) for _, r in reports)}</div>
                <div class="stat-label">Repos Found</div>
              </div>
              <div class="stat-item">
                <div class="stat-num">{reports[0][1][0]['score'] if reports and reports[0][1] else '?'}</div>
                <div class="stat-label">Top Score</div>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Cross-promotion -->
  <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="100%">
        <table width="780" cellpadding="0" cellspacing="0" border="0" align="center">
          <tr>
            <td class="cross-promotion" width="780">
              <p>🚀 Found by GitHub Discovery &mdash; <a href="https://github.com/alloevil/github-discovery">Star on GitHub</a> &middot; <a href="{SITE_URL}/feed.xml">RSS</a></p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Daily Sections -->
  {sections_html}

  <!-- Footer -->
  <table class="wrapper" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td width="100%">
        <table width="780" cellpadding="20" cellspacing="0" border="0" align="center">
          <tr>
            <td class="footer" width="780">
              <p>Generated by <a href="https://github.com/alloevil/github-discovery">GitHub Discovery</a></p>
              <p>Updated daily at 18:00 CST &middot; <a href="{SITE_URL}/feed.xml">RSS</a></p>
              <p style="font-size:11px; color:#484f58; margin-top:15px;">Inspired by <a href="https://github.com/thechangelog/nightly">Changelog Nightly</a></p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def generate_rss(reports: list[tuple[str, list[dict]]]) -> str:
    """Generate RSS feed."""
    rss = Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    channel = SubElement(rss, 'channel')
    SubElement(channel, 'title').text = SITE_TITLE
    SubElement(channel, 'description').text = SITE_DESC
    SubElement(channel, 'link').text = SITE_URL
    SubElement(channel, 'language').text = 'en'
    SubElement(channel, 'lastBuildDate').text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    atom_link = SubElement(channel, 'atom:link')
    atom_link.set('href', f'{SITE_URL}/feed.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')

    for date_str, repos in reports[:10]:
        for repo in repos[:5]:
            item = SubElement(channel, 'item')
            score = repo.get('score', '?')
            stars = repo.get('stars', '?')
            daily = repo.get('daily', '?')
            lang = repo.get('language', 'Unknown')
            SubElement(item, 'title').text = f"🔥 {repo.get('name', 'Unknown')} — {stars}⭐ ({daily}/day)"
            desc = repo.get('description', '')
            SubElement(item, 'description').text = f"{desc}\n\nScore: {score}/100 | Growth: {daily} stars/day | Language: {lang}"
            SubElement(item, 'link').text = repo.get('url', SITE_URL)
            SubElement(item, 'guid').text = f"{repo.get('url', '')}#{date_str}"
            SubElement(item, 'pubDate').text = datetime.strptime(date_str, '%Y-%m-%d').strftime('%a, %d %b %Y 18:00:00 +0000')

    xml_str = tostring(rss, encoding='unicode', xml_declaration=False)
    pretty = parseString(xml_str).toprettyxml(indent='  ', encoding=None)
    lines = pretty.split('\n')
    if lines and lines[0].startswith('<?xml'):
        return '\n'.join(lines)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty


def main():
    os.makedirs(DIST_DIR, exist_ok=True)

    report_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'discovery-*.md')), reverse=True)

    reports = []
    for f in report_files:
        date_match = re.search(r'discovery-(\d{4}-\d{2}-\d{2})\.md', f)
        if date_match:
            date_str = date_match.group(1)
            repos = parse_report(f)
            if repos:
                reports.append((date_str, repos))

    if not reports:
        print("[WARN] No reports found to generate site")
        return

    html = generate_index_html(reports)
    with open(os.path.join(DIST_DIR, 'index.html'), 'w') as f:
        f.write(html)
    print(f"[OK] Generated index.html ({len(reports)} reports)")

    rss = generate_rss(reports)
    with open(os.path.join(DIST_DIR, 'feed.xml'), 'w') as f:
        f.write(rss)
    print(f"[OK] Generated feed.xml")


if __name__ == "__main__":
    main()
