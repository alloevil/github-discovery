"""Generate static site for GitHub Pages from discovery reports.

Uses a template-based approach: reads docs/template.html for design/layout,
and only injects the dynamic repo data sections.
"""

import os
import re
import glob
import json
import statistics
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

DIST_DIR = "docs"
OUTPUT_DIR = "output"
DATA_DIR = "data"
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
    "ai-trending": "🤖 AI/ML",
    "hf-papers": "🤗 HF Papers",
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
                             ('daily', r'🚀 Daily Growth \| (-?[\d.]+)'),
                             # 语言名可含空格和符号（C++、C#、Jupyter Notebook），
                             # 旧的 (\w+) 会漏掉这些
                             ('language', r'🔤 Language \| ([^|\n]+?) \|'),
                             ('score', r'Score: (\d+)/100'),
                             ('source', r'📡 Source \| ([\w+ -]+?) \|')]:
            m = re.search(pattern, section)
            if m:
                v = m.group(1).strip()
                repo[key] = v.replace(',', '') if key == 'stars' else v
        m = re.search(r'> (.+)', section)
        if m:
            repo['description'] = m.group(1).strip()
        if 'name' in repo:
            repos.append(repo)
    return repos


def _json_entry_to_card(e: dict) -> dict:
    """把 JSON 报告条目映射成卡片渲染所需的扁平 dict。"""
    name = e.get('full_name', '?')
    parts = name.split('/')
    daily = e.get('real_daily_stars')
    if daily is None:
        daily = e.get('daily_stars', 0)
    sources = e.get('sources') or ([e['source']] if e.get('source') else [])
    return {
        'name': name,
        'url': e.get('url', '#'),
        'owner': parts[0] if len(parts) > 1 else '',
        'repo': parts[1] if len(parts) > 1 else name,
        'stars': str(e.get('stars', 0)),
        'daily': f"{daily:.1f}",
        'score': str(e.get('scores', {}).get('total', 0)),
        'language': e.get('language', ''),
        'description': e.get('description') or 'No description',
        'source': ' + '.join(sources),
    }


def load_json_report(filepath: str) -> tuple[list[dict], list[dict]]:
    with open(filepath) as f:
        data = json.load(f)
    return ([_json_entry_to_card(e) for e in data.get('new', [])],
            [_json_entry_to_card(e) for e in data.get('repeat', [])])


def parse_report(filepath: str) -> tuple[list[dict], list[dict]]:
    """读一天的报告。优先读结构化 JSON（data/discovery-*.json），
    没有 JSON 的旧报告回退到 markdown 正则解析。"""
    m = re.search(r'discovery-(\d{4}-\d{2}-\d{2})\.md', filepath)
    if m:
        json_path = os.path.join(DATA_DIR, f'discovery-{m.group(1)}.json')
        if os.path.exists(json_path):
            try:
                return load_json_report(json_path)
            except (ValueError, OSError) as e:
                print(f"[WARN] Bad JSON report {json_path} ({e}), falling back to markdown")
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
    # 多来源仓库（"trending + hn"）逐个映射 label
    src_label = ' · '.join(filter(None, (source_label(s.strip()) for s in src.split('+'))))
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
    # Median score of the latest report's repos — more informative than the
    # top score, which is almost always 100.
    latest_scores = []
    if reports:
        for r in reports[0][1] + reports[0][2]:
            try:
                latest_scores.append(int(r.get('score', 0)))
            except (ValueError, TypeError):
                pass
    median_score = int(statistics.median(latest_scores)) if latest_scores else '?'

    date_buttons = []
    for i, (date_str, _, _) in enumerate(reports[:7]):
        selected = ' selected' if i == 0 else ''
        date_buttons.append(f'<option value="{date_str}"{selected}>{date_str}</option>')

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
        'top_score': str(median_score),
        'days_tracked': str(len(reports)),
        'num_sources': str(len(SOURCE_LABELS)),
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
    html = html.replace('id="stat-sources">6<', f'id="stat-sources">{data["num_sources"]}<')
    html = html.replace('id="stat-repos">33<', f'id="stat-repos">{data["total_repos"]}<')
    html = html.replace('id="stat-score">100<', f'id="stat-score">{data["top_score"]}<')

    html = re.sub(
        r'(<select class="date-select" id="date-select"[^>]*>)\s*\n(.*?)\s*\n(\s*</select>)',
        lambda m: f'{m.group(1)}\n        {data["date_filters"]}\n{m.group(3)}',
        html, flags=re.DOTALL
    )

    marker = '<!-- CONTENT_MARKER -->'
    if marker in html:
        parts = html.split(marker)
        html = parts[0] + data['sections'] + '\n' + parts[1]

    with open(os.path.join(DIST_DIR, 'index.html'), 'w') as f:
        f.write(html)

    # Generate Atom feed alongside index.html
    feed_xml = generate_feed(reports)
    with open(os.path.join(DIST_DIR, 'feed.xml'), 'w') as f:
        f.write(feed_xml)

    print(f"[OK] index.html ({len(reports)} reports, template-based)")
    print(f"[OK] feed.xml ({sum(len(ft[:5]) + len(rp[:3]) for _, ft, rp in reports[:FEED_DAYS])} entries)")


FEED_DAYS = 14  # 保留最近 ~14 天的条目（issue #5）


def _feed_date(date_str: str) -> str:
    """报告日期 → RFC 3339 时间戳。固定 18:00 UTC（daily workflow 的大致运行时间）。"""
    return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%dT18:00:00Z')


def generate_feed(reports):
    """把最近 FEED_DAYS 天的推荐渲染成 Atom feed（RFC 4287）。

    entry id 由 repo URL + 日期决定，稳定可复现：同一天重跑 workflow
    不产生新 id，阅读器不会显示重复条目。updated 同样由内容（最新
    报告日期）决定而不是 now()，否则每次 CI 重跑都产生 diff，导致
    同一天出现第二个空 commit。
    """
    feed = Element('feed', xmlns='http://www.w3.org/2005/Atom')
    SubElement(feed, 'title').text = SITE_TITLE
    SubElement(feed, 'subtitle').text = SITE_DESC
    SubElement(feed, 'id').text = f'{SITE_URL}/'
    latest = reports[0][0] if reports else datetime.now(timezone.utc).strftime('%Y-%m-%d')
    SubElement(feed, 'updated').text = _feed_date(latest)
    author = SubElement(feed, 'author')
    SubElement(author, 'name').text = SITE_TITLE
    link_self = SubElement(feed, 'link', rel='self', type='application/atom+xml')
    link_self.set('href', f'{SITE_URL}/feed.xml')
    link_alt = SubElement(feed, 'link', rel='alternate', type='text/html')
    link_alt.set('href', SITE_URL)
    for date_str, first_timers, repeat_performers in reports[:FEED_DAYS]:
        for r in first_timers[:5] + repeat_performers[:3]:
            entry = SubElement(feed, 'entry')
            SubElement(entry, 'title').text = f"{r.get('name', '?')} — {r.get('description', 'No description')}"
            SubElement(entry, 'id').text = f"{r.get('url', SITE_URL)}#{date_str}"
            link = SubElement(entry, 'link', rel='alternate', type='text/html')
            link.set('href', r.get('url', SITE_URL))
            SubElement(entry, 'updated').text = _feed_date(date_str)
            SubElement(entry, 'published').text = _feed_date(date_str)
            SubElement(entry, 'summary').text = (
                f"{r.get('description', '')}\n\n"
                f"Score: {r.get('score', '?')}/100 | Language: {r.get('language', '?') or '?'} | "
                f"⭐ {r.get('stars', '?')} (+{r.get('daily', '?')}/day) | Source: {r.get('source', '?')}"
            )
    xml_str = tostring(feed, encoding='unicode', xml_declaration=False)
    pretty = parseString(xml_str).toprettyxml(indent='  ', encoding=None)
    lines = pretty.split('\n')
    return '\n'.join(lines) if lines and lines[0].startswith('<?xml') else '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty


if __name__ == "__main__":
    main()
