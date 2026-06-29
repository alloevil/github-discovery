"""Generate static site for GitHub Pages from discovery reports.

Uses a template-based approach: reads docs/template.html for design/layout,
and only injects the dynamic repo data sections.
"""

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


# Display label (emoji + friendly name) for each discovery source.
SOURCE_LABELS = {
    "trending": "🔥 Trending",
    "search": "🔍 Search",
    "hn": "🟠 HN",
    "rising": "📈 Rising",
    "ai-trending": "🤖 AI",
}


def source_label(source: str) -> str:
    return SOURCE_LABELS.get((source or "").lower(), source or "")


def _parse_sections(content: str) -> list[dict]:
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
                             ('score', r'Score: (\d+)/100'), ('source', r'📡 Source \| ([\w-]+)')]:
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
    with open(filepath) as f:
        content = f.read()
    if 'First Timers' in content and 'Repeat Performers' in content:
        parts = content.split('Repeat Performers')
        return _parse_sections(parts[0]), _parse_sections(parts[1] if len(parts) > 1 else '')
    return _parse_sections(content), []


def repo_card(r: dict) -> str:
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
    sc = "high" if si >= 95 else ("mid" if si >= 90 else "low")
    lang_html = f'<span class="repo-meta-item"><span class="lang-dot" style="background:{color}"></span>{lang}</span>' if lang else ''
    lang_attr = lang.lower() if lang else 'unknown'
    src = r.get('source', '')
    src_label = source_label(src)
    src_html = f'<span class="repo-meta-item source-tag" title="Discovered via {src}">{src_label}</span>' if src_label else ''
    return f'''      <div class="repo" data-lang="{lang_attr}" data-source="{src.lower()}">
        <div class="repo-top">
          <img class="repo-avatar" src="{avatar}" alt="{owner}" onerror="this.style.display='none'">
          <div class="repo-name"><a href="{url}"><span class="repo-owner">{owner} /</span> {repo_name}</a></div>
        </div>
        <div class="repo-desc">{desc}</div>
        <div class="repo-meta">
          {lang_html}
          <span class="repo-meta-item">⭐ {stars}</span>
          <span class="repo-meta-item">📈 +{daily}/day</span>
          <span class="score-tag {sc}">Score {score}</span>
          {src_html}
        </div>
      </div>'''


def generate_content(reports):
    total_repos = sum(len(ft) + len(rp) for _, ft, rp in reports)
    top_score = reports[0][1][0]['score'] if reports and reports[0][1] else '?'

    date_buttons = []
    for i, (date_str, _, _) in enumerate(reports[:7]):
        active = ' active' if i == 0 else ''
        date_buttons.append(f'<button class="filter-btn{active}" onclick="switchDate(\'{date_str}\')">{date_str}</button>')

    sections = []
    for i, (date_str, first_timers, repeat_performers) in enumerate(reports[:7]):
        display = '' if i == 0 else 'none'
        cards = []
        if first_timers:
            cards.append(f'      <div class="section-label"><span class="label-icon">⭐</span><span>First Timers</span><span class="label-count">{len(first_timers)}</span></div>')
            for r in first_timers[:10]:
                cards.append(repo_card(r))
        if repeat_performers:
            cards.append(f'      <div class="section-label"><span class="label-icon">🔄</span><span>Repeat Performers</span><span class="label-count">{len(repeat_performers)}</span></div>')
            for r in repeat_performers[:5]:
                cards.append(repo_card(r))
        sections.append(f'    <div class="date-section" data-date="{date_str}" style="display:{display}">\n      <div class="date-header"><h3>{date_str}</h3><span class="date-count">{len(first_timers) + len(repeat_performers)} repos</span></div>\n' + '\n'.join(cards) + '\n    </div>')

    return {
        'date_filters': '\n        '.join(date_buttons),
        'sections': '\n'.join(sections),
        'total_repos': str(total_repos),
        'top_score': str(top_score),
        'days_tracked': str(len(reports)),
    }


def main():
    os.makedirs(DIST_DIR, exist_ok=True)

    template_path = os.path.join(DIST_DIR, 'template.html')
    try:
        with open(template_path) as f:
            template = f.read()
    except FileNotFoundError:
        print("[ERROR] docs/template.html not found!")
        return

    report_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'discovery-*.md')), reverse=True)
    reports = []
    for f in report_files:
        m = re.search(r'discovery-(\d{4}-\d{2}-\d{2})\.md', f)
        if m:
            first, repeat = parse_report(f)
            if first or repeat:
                reports.append((m.group(1), first, repeat))

    if not reports:
        print("[WARN] No reports found")
        return

    data = generate_content(reports)

    html = template
    html = html.replace('id="stat-sources">6<', f'id="stat-sources">{data["days_tracked"]}<')
    html = html.replace('id="stat-repos">33<', f'id="stat-repos">{data["total_repos"]}<')
    html = html.replace('id="stat-score">100<', f'id="stat-score">{data["top_score"]}<')

    html = re.sub(
        r'(<div class="filter-group" id="date-filters">)\s*\n(.*?)\s*\n(\s*</div>)',
        lambda m: f'{m.group(1)}\n        {data["date_filters"]}\n{m.group(3)}',
        html, flags=re.DOTALL
    )

    marker = '<!-- CONTENT_MARKER -->'
    if marker in html:
        parts = html.split(marker)
        html = parts[0] + data['sections'] + '\n' + parts[1]

    with open(os.path.join(DIST_DIR, 'index.html'), 'w') as f:
        f.write(html)

    # Generate RSS feed alongside index.html
    rss_xml = generate_rss(reports)
    with open(os.path.join(DIST_DIR, 'feed.xml'), 'w') as f:
        f.write(rss_xml)

    print(f"[OK] index.html ({len(reports)} reports, template-based)")
    print(f"[OK] feed.xml ({sum(len(ft[:5]) + len(rp[:3]) for _, ft, rp in reports[:10])} items)")


def generate_rss(reports):
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


if __name__ == "__main__":
    main()
