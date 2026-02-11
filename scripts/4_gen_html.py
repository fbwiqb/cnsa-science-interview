import sys, os, json, re, time
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
DATA_DIR = os.path.join(BASE_DIR, 'data')
SUBJECT_LABELS = {'물리': '물리학', '화학': '화학', '생물': '생명과학'}


def md_to_html(md, fig_dir_rel):
    lines = md.split('\n')
    html_parts = []
    current_section = []
    in_table = False
    table_rows = []
    in_passage = False
    past_first_question = False

    def flush_section():
        if current_section:
            html_parts.append('<div class="question-block">\n' + '\n'.join(current_section) + '\n</div>')
            current_section.clear()

    def flush_table():
        nonlocal in_table, table_rows
        if table_rows:
            thtml = '<table class="md-table">\n'
            for ri, row in enumerate(table_rows):
                tag = 'th' if ri == 0 else 'td'
                thtml += '<tr>' + ''.join(f'<{tag}>{cell}</{tag}>' for cell in row) + '</tr>\n'
            thtml += '</table>'
            current_section.append(thtml)
            table_rows = []
        in_table = False

    for line in lines:
        raw = line.strip()

        if raw.startswith('|') and raw.endswith('|'):
            cells = [c.strip() for c in raw.split('|')[1:-1]]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue
            in_table = True
            processed = []
            for cell in cells:
                cell = process_inline(cell)
                processed.append(cell)
            table_rows.append(processed)
            continue
        elif in_table:
            flush_table()

        is_q = re.match(r'\*\*\d+\.\*\*', raw) or re.match(r'\*\*\[문제', raw) or re.match(r'\*\*\[(물리|화학|생명)', raw) or re.match(r'\*\*문제\s*\d+', raw) or re.match(r'문제\s*\d+', raw)
        if is_q:
            past_first_question = True
            if in_passage:
                current_section.append('</div>')
                in_passage = False

        if not raw:
            current_section.append('<div class="spacer"></div>')
            continue

        if raw.startswith('## '):
            if in_passage:
                current_section.append('</div>')
                in_passage = False
            past_first_question = False
            flush_section()
            title = raw[3:]
            current_section.append(f'<h1 class="main-title">{title}</h1>')
            continue

        if raw.startswith('### '):
            if in_passage:
                current_section.append('</div>')
                in_passage = False
            past_first_question = True
            flush_section()
            label = raw[4:]
            current_section.append(f'<h2 class="sub-title">{label}</h2>')
            continue

        if raw.startswith('<!-- IMAGE:'):
            match = re.search(r'IMAGE:\s*(\S+)', raw)
            if match:
                img_file = match.group(1)
                img_path = f'{fig_dir_rel}/{img_file}'
                current_section.append(f'<div class="figure"><img src="{img_path}" /></div>')
            continue

        if raw.startswith('---'):
            continue

        if raw.startswith('> *') and 'AI' in raw:
            inner = raw[2:].strip().strip('*')
            current_section.append(f'<div class="ai-disclaimer">{inner}</div>')
            continue

        if raw.startswith('<표') or raw.startswith('<Table'):
            current_section.append(f'<p style="text-align:center;font-size:9pt;color:#666;">{process_inline(raw)}</p>')
            continue

        passage_bracket = re.match(r'^(?:\*\*)?(\[[가나다라마바사아자차카타파하]\])(?:\*\*)?\s*(.*)', raw)
        if passage_bracket:
            if not in_passage and not past_first_question:
                current_section.append('<div class="passage-box">')
                in_passage = True
            if in_passage:
                marker = passage_bracket.group(1)
                rest = passage_bracket.group(2).strip()
                rest_html = process_inline(rest) if rest else ''
                line_html = f'<p><span class="passage-marker">{marker}</span> {rest_html}</p>' if rest_html else f'<p><span class="passage-marker">{marker}</span></p>'
                current_section.append(line_html)
                continue

        passage_paren = re.match(r'^(?:\*\*)?\(([가나다라마바사아자차카타파하])\)(?:\*\*)?\s*(.*)', raw)
        if passage_paren and not past_first_question:
            if not in_passage:
                current_section.append('<div class="passage-box">')
                in_passage = True
            letter = passage_paren.group(1)
            rest = passage_paren.group(2).strip()
            rest_html = process_inline(rest) if rest else ''
            marker = f'({letter})'
            line_html = f'<p><span class="passage-marker">{marker}</span> {rest_html}</p>' if rest_html else f'<p><span class="passage-marker">{marker}</span></p>'
            current_section.append(line_html)
            continue

        jesimun_match = re.match(r'^(?:\*\*)?(?:<|&lt;)제시문\s*(\d*)(?:>|&gt;)(?:\*\*)?$', raw) or re.match(r'^\[제시문(?:\s*\d+)?\]$', raw)
        if jesimun_match:
            if not in_passage and not past_first_question:
                current_section.append('<div class="passage-box">')
                in_passage = True
            if in_passage:
                display = process_inline(raw).replace('<strong>', '').replace('</strong>', '')
                current_section.append(f'<p><span class="passage-marker">{display}</span></p>')
                continue

        bold_match = re.match(r'\*\*\((\d+)\)\*\*\s*(.*)', raw)
        if bold_match:
            num = bold_match.group(1)
            rest = process_inline(bold_match.group(2))
            current_section.append(f'<p class="sub-question"><span class="sq-num">({num})</span> {rest}</p>')
        else:
            text = process_inline(raw)
            if '<div class="math-block">' in text:
                current_section.append(text)
            else:
                current_section.append(f'<p>{text}</p>')

    if in_passage:
        current_section.append('</div>')
        in_passage = False
    if in_table:
        flush_table()
    flush_section()
    return '\n'.join(html_parts)


def escape_html(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def process_inline(text):
    parts = []
    i = 0
    while i < len(text):
        if text[i] == '$':
            if i + 1 < len(text) and text[i+1] == '$':
                end = text.find('$$', i+2)
                if end != -1:
                    formula = text[i+2:end].replace('·', '\\cdot ')
                    parts.append(f'<div class="math-block">\\[{formula}\\]</div>')
                    i = end + 2
                    continue
            else:
                end = text.find('$', i+1)
                if end != -1:
                    formula = text[i+1:end].replace('·', '\\cdot ')
                    parts.append(f'\\({formula}\\)')
                    i = end + 1
                    continue
        if text[i:i+2] == '**':
            end = text.find('**', i+2)
            if end != -1:
                inner = text[i+2:end]
                parts.append(f'<strong>{inner}</strong>')
                i = end + 2
                continue
        if text[i] == '<' and not text[i:].startswith('<div') and not text[i:].startswith('<span') and not text[i:].startswith('<strong') and not text[i:].startswith('<table') and not text[i:].startswith('<p'):
            parts.append('&lt;')
            i += 1
            continue
        if text[i] == '>' and i > 0 and text[i-1] != '-' and not any(text[max(0,i-5):i].endswith(t) for t in ['div', 'span', 'strong', 'table', 'tr', 'td', 'th', '/p']):
            parts.append('&gt;')
            i += 1
            continue
        parts.append(text[i])
        i += 1
    return ''.join(parts)


def generate_problem_html(meta, vision_md, subject, is_solution=False, problem_uid=None, has_solution=False):
    uid = meta['uid']
    subject_label = SUBJECT_LABELS.get(subject, subject)
    fig_dir_rel = f'../../data/{subject}/{meta["filename"]}'

    body_html = md_to_html(vision_md, fig_dir_rel)

    header_label = f'과학 면접 아카데미 &nbsp;|&nbsp; {subject_label}'
    if is_solution:
        header_label += ' &nbsp;|&nbsp; 해설'

    footer_uid = problem_uid if is_solution and problem_uid else uid

    nav_links = ''
    if is_solution and problem_uid:
        nav_links = f'<div style="text-align:right;padding:4px 20mm 0;"><a href="{problem_uid}.html" style="color:#003366;font-size:9pt;text-decoration:none;">&larr; 문제 보기</a></div>'
    elif not is_solution and has_solution:
        sol_uid = uid + '-해설'
        nav_links = f'<div style="text-align:right;padding:4px 20mm 0;"><a href="{sol_uid}.html" class="sol-link" style="color:#003366;font-size:9pt;text-decoration:none;">해설 보기 &rarr;</a></div>'

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{footer_uid} | {meta["filename"]}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>

<div class="header">
  <img src="../assets/logo.png" />
  <span class="header-text">{header_label}</span>
</div>
<div class="header-line"></div>

{nav_links}
<div class="content">
  {body_html}
</div>

<div class="footer">
  <div class="footer-line"></div>
  <div class="footer-text">{footer_uid}</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<script>
  document.addEventListener("DOMContentLoaded", function() {{
    renderMathInElement(document.body, {{
      delimiters: [
        {{left: "\\\\[", right: "\\\\]", display: true}},
        {{left: "\\\\(", right: "\\\\)", display: false}},
        {{left: "$$", right: "$$", display: true}},
        {{left: "$", right: "$", display: false}}
      ],
      throwOnError: false
    }});
  }});
</script>
</body>
</html>'''
    return html


def generate_hub_html(index_data):
    problems = [item for item in index_data if not item.get('is_solution')]
    solutions = {item['problem_uid']: item for item in index_data if item.get('is_solution')}

    subjects_data = {}
    for item in problems:
        subj = item['subject_category']
        school = item['school']
        year = item['year']
        if subj not in subjects_data:
            subjects_data[subj] = {}
        if school not in subjects_data[subj]:
            subjects_data[subj][school] = {}
        if year not in subjects_data[subj][school]:
            subjects_data[subj][school][year] = []
        subjects_data[subj][school][year].append(item)

    cards_json = json.dumps(problems, ensure_ascii=False)
    cards_json = cards_json.replace('</', '<\\/')
    cache_bust = int(time.time())

    hub_content = ''
    subject_order = ['물리', '화학', '생물']
    subj_counts = {}
    for subj in subject_order:
        if subj in subjects_data:
            subj_counts[subj] = sum(1 for item in problems if item['subject_category'] == subj)
    tab_buttons = ''
    for i, subj in enumerate(subject_order):
        if subj not in subjects_data:
            continue
        active = ' active' if i == 0 else ''
        tab_buttons += f'<button class="tab-btn{active}" data-subject="{subj}">{subj} <span class="tab-count">{subj_counts.get(subj, 0)}</span></button>\n'

    for subj in subject_order:
        if subj not in subjects_data:
            continue
        subj_count = sum(1 for item in problems if item['subject_category'] == subj)
        hub_content += f'<div class="subject-section" data-subject="{subj}">\n'
        hub_content += f'<h2 class="subject-header">{subj} ({subj_count})</h2>\n'

        for school in sorted(subjects_data[subj].keys()):
            school_count = sum(len(v) for v in subjects_data[subj][school].values())
            hub_content += f'<div class="school-section collapsed" data-school="{school}">\n'
            hub_content += f'<h3 class="school-header">{school} ({school_count})</h3>\n'
            hub_content += '<div class="school-body">\n'

            for year in sorted(subjects_data[subj][school].keys(), reverse=True):
                items = subjects_data[subj][school][year]
                hub_content += f'<div class="year-section" data-year="{year}">\n'
                hub_content += f'<h4 class="year-header">{year}년</h4>\n'
                hub_content += '<div class="card-grid">\n'
                for item in sorted(items, key=lambda x: x.get('number', '')):
                    uid = item['uid']
                    label = f'{item.get("type", "")} {item.get("number", "")}'.strip()
                    subj_prefix = subj
                    sol = solutions.get(uid)
                    sol_link = ''
                    if sol:
                        sol_link = f'<a href="{subj_prefix}/{sol["uid"]}.html" class="card-sol" title="해설 보기">해설</a>'
                        view_btn = f'<button class="card-view" data-prob="{subj_prefix}/{uid}.html" data-sol="{subj_prefix}/{sol["uid"]}.html" title="문제+해설 나란히 보기">보기</button>'
                    else:
                        view_btn = f'<button class="card-view" data-prob="{subj_prefix}/{uid}.html" data-sol="" title="문제 보기">보기</button>'
                    hub_content += f'''<div class="card" data-uid="{uid}" data-subject="{subj}" data-school="{school}" data-year="{year}">
  <input type="checkbox" class="card-check" value="{uid}">
  <a href="{subj_prefix}/{uid}.html" class="card-link">
    <span class="card-uid">{uid}</span>
    <span class="card-label">{label}</span>
  </a>
  {sol_link}
  {view_btn}
</div>\n'''
                hub_content += '</div>\n</div>\n'
            hub_content += '</div>\n</div>\n'
        hub_content += '</div>\n'

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CNSA 과학 면접 아카데미 - 문제 허브</title>
<link rel="stylesheet" href="assets/hub.css?v={cache_bust}">
</head>
<body>

<header class="hub-header">
  <div class="hub-header-inner">
    <img src="assets/logo.png" class="hub-logo" />
    <div>
      <h1>과학 면접 아카데미</h1>
      <p class="hub-subtitle">문제 허브</p>
    </div>
  </div>
</header>

<div class="toolbar">
  <div class="filters">
    <input type="hidden" id="filter-subject" value="물리">
    <select id="filter-school">
      <option value="">전체 학교</option>
    </select>
    <select id="filter-year">
      <option value="">전체 연도</option>
    </select>
    <input type="text" id="search-box" placeholder="검색..." />
  </div>
  <div class="actions">
    <button id="btn-unreviewed" class="btn btn-unreviewed">미검수만</button>
    <button id="btn-toggle-collapse" class="btn">전체 펼치기</button>
    <button id="btn-select-all" class="btn">전체 선택</button>
    <button id="btn-deselect" class="btn">선택 해제</button>
    <button id="btn-print" class="btn btn-primary">선택 인쇄</button>
    <button id="btn-export-csv" class="btn">보고 CSV<span id="report-badge" class="report-badge"></span></button>
    <button id="btn-clear-reports" class="btn">보고 초기화</button>
  </div>
</div>

<div class="tab-bar">
  {tab_buttons}
</div>

<div class="stats" id="stats"></div>

<main id="hub-content">
  {hub_content}
</main>

<div id="print-container" class="print-only"></div>

<div class="split-overlay" id="split-overlay">
  <div class="split-toolbar">
    <h3 id="split-title">문제 / 해설</h3>
    <span id="split-review-status" class="split-review-badge"></span>
    <div class="split-nav">
      <button id="btn-prev">&larr; 이전</button>
      <span id="split-counter"></span>
      <button id="btn-next">다음 &rarr;</button>
      <button id="btn-close-split" class="btn-close-split">닫기</button>
    </div>
  </div>
  <div class="split-panels">
    <iframe id="iframe-prob"></iframe>
    <div class="split-divider"></div>
    <iframe id="iframe-sol"></iframe>
  </div>
</div>

<div class="report-modal" id="report-modal">
  <div class="report-box">
    <h3>이상 보고</h3>
    <div class="report-uid-display" id="report-uid"></div>
    <label>대상</label>
    <select id="report-side">
      <option value="문제">문제</option>
      <option value="해설">해설</option>
    </select>
    <label>유형</label>
    <select id="report-type">
      <option value="">선택하세요</option>
      <option value="색상반전">색상반전</option>
      <option value="그림깨짐">그림깨짐</option>
      <option value="그림가림">그림가림</option>
      <option value="수식오류">수식오류</option>
      <option value="로고포함">로고포함</option>
      <option value="내용누락">내용누락</option>
      <option value="한글깨짐">한글깨짐</option>
      <option value="기타">기타</option>
    </select>
    <label>메모</label>
    <textarea id="report-memo" placeholder="상세 내용 입력..."></textarea>
    <div class="report-actions">
      <button id="btn-report-cancel" class="btn">취소</button>
      <button id="btn-report-save" class="btn btn-primary">보고 저장</button>
    </div>
  </div>
</div>

<script>
const ALL_DATA = {cards_json};
</script>
<script src="assets/hub.js?v={cache_bust}"></script>
</body>
</html>'''
    return html


def main():
    index_path = os.path.join(DATA_DIR, 'index.json')
    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)

    solutions_set = {item['problem_uid'] for item in index_data if item.get('is_solution')}

    for item in index_data:
        subject = item['subject_category']
        uid = item['uid']
        filename = item['filename']
        is_solution = item.get('is_solution', False)
        problem_uid = item.get('problem_uid', None)

        vision_path = os.path.join(DATA_DIR, subject, filename, 'vision.md')
        if not os.path.exists(vision_path):
            print(f'SKIP {uid}: no vision.md')
            continue

        with open(vision_path, 'r', encoding='utf-8') as f:
            vision_md = f.read()

        has_solution = uid in solutions_set
        html = generate_problem_html(item, vision_md, subject, is_solution, problem_uid, has_solution)

        out_dir = os.path.join(OUTPUT_DIR, subject)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f'{uid}.html')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'OK: {uid} -> {out_path}')

    hub_html = generate_hub_html(index_data)
    hub_path = os.path.join(OUTPUT_DIR, 'index.html')
    with open(hub_path, 'w', encoding='utf-8') as f:
        f.write(hub_html)
    print(f'\nHub: {hub_path}')
    print(f'Total: {len(index_data)} items ({sum(1 for i in index_data if not i.get("is_solution"))} problems, {sum(1 for i in index_data if i.get("is_solution"))} solutions)')


if __name__ == '__main__':
    main()
