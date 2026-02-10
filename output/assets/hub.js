const filterSubject = document.getElementById('filter-subject');
const filterSchool = document.getElementById('filter-school');
const filterYear = document.getElementById('filter-year');
const searchBox = document.getElementById('search-box');
const statsEl = document.getElementById('stats');
const cards = document.querySelectorAll('.card');
const sections = {
  subject: document.querySelectorAll('.subject-section'),
  school: document.querySelectorAll('.school-section'),
  year: document.querySelectorAll('.year-section')
};

const schools = [...new Set(ALL_DATA.map(d => d.school))].sort();
const years = [...new Set(ALL_DATA.map(d => d.year))].sort().reverse();

schools.forEach(s => {
  const opt = document.createElement('option');
  opt.value = s;
  opt.textContent = s;
  filterSchool.appendChild(opt);
});
years.forEach(y => {
  const opt = document.createElement('option');
  opt.value = y;
  opt.textContent = y + '년';
  filterYear.appendChild(opt);
});

let reviewed = JSON.parse(localStorage.getItem('hub_reviewed') || '{}');

function applyReviewedStyles() {
  cards.forEach(card => {
    const uid = card.dataset.uid;
    if (reviewed[uid]) {
      card.classList.add('reviewed');
    } else {
      card.classList.remove('reviewed');
    }
  });
}

const tabBtns = document.querySelectorAll('.tab-btn');

function switchTab(subj) {
  filterSubject.value = subj;
  tabBtns.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.subject === subj);
  });
  sections.subject.forEach(sec => {
    sec.classList.toggle('active', sec.dataset.subject === subj);
  });
  applyFilters();
}

tabBtns.forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.subject));
});

document.querySelectorAll('.school-header').forEach(header => {
  header.addEventListener('click', () => {
    header.closest('.school-section').classList.toggle('collapsed');
  });
});

let showUnreviewedOnly = false;
document.getElementById('btn-unreviewed').addEventListener('click', () => {
  showUnreviewedOnly = !showUnreviewedOnly;
  const btn = document.getElementById('btn-unreviewed');
  btn.classList.toggle('active', showUnreviewedOnly);
  btn.textContent = showUnreviewedOnly ? '전체 보기' : '미검수만';
  applyFilters();
});

let allExpanded = false;
document.getElementById('btn-toggle-collapse').addEventListener('click', () => {
  allExpanded = !allExpanded;
  const activeSubj = document.querySelector('.subject-section.active');
  if (!activeSubj) return;
  activeSubj.querySelectorAll('.school-section').forEach(sec => {
    sec.classList.toggle('collapsed', !allExpanded);
  });
  document.getElementById('btn-toggle-collapse').textContent = allExpanded ? '전체 접기' : '전체 펼치기';
});

function applyFilters() {
  const subj = filterSubject.value;
  const school = filterSchool.value;
  const year = filterYear.value;
  const query = searchBox.value.trim().toLowerCase();

  let visible = 0;
  cards.forEach(card => {
    const ds = card.dataset.subject;
    const dsc = card.dataset.school;
    const dy = card.dataset.year;
    const duid = card.dataset.uid.toLowerCase();
    const text = card.textContent.toLowerCase();

    let show = true;
    if (subj && ds !== subj) show = false;
    if (school && dsc !== school) show = false;
    if (year && dy !== year) show = false;
    if (query && !text.includes(query) && !duid.includes(query)) show = false;
    if (showUnreviewedOnly && reviewed[card.dataset.uid]) show = false;

    card.classList.toggle('hidden', !show);
    if (show) visible++;
  });

  sections.year.forEach(sec => {
    const visCards = sec.querySelectorAll('.card:not(.hidden)');
    sec.style.display = visCards.length ? '' : 'none';
  });
  sections.school.forEach(sec => {
    const hasVisible = [...sec.querySelectorAll('.card:not(.hidden)')].length > 0;
    sec.style.display = hasVisible ? '' : 'none';
  });
  sections.subject.forEach(sec => {
    if (subj && sec.dataset.subject !== subj) return;
    const hasVisible = [...sec.querySelectorAll('.card:not(.hidden)')].length > 0;
    if (!subj) sec.style.display = hasVisible ? '' : 'none';
  });

  const totalInTab = [...cards].filter(c => c.dataset.subject === subj).length;
  const reviewedInTab = [...cards].filter(c => c.dataset.subject === subj && reviewed[c.dataset.uid]).length;
  statsEl.textContent = `${visible}개 표시 / ${totalInTab}개 중 검수 완료 ${reviewedInTab}개`;
}

filterSchool.addEventListener('change', applyFilters);
filterYear.addEventListener('change', applyFilters);
searchBox.addEventListener('input', applyFilters);

document.getElementById('btn-select-all').addEventListener('click', () => {
  cards.forEach(card => {
    if (!card.classList.contains('hidden')) {
      card.querySelector('.card-check').checked = true;
    }
  });
});

document.getElementById('btn-deselect').addEventListener('click', () => {
  document.querySelectorAll('.card-check').forEach(cb => cb.checked = false);
});

document.getElementById('btn-print').addEventListener('click', () => {
  const checked = [...document.querySelectorAll('.card-check:checked')];
  if (checked.length === 0) {
    alert('인쇄할 문제를 선택하세요.');
    return;
  }

  const urls = checked.map(cb => {
    const card = cb.closest('.card');
    return card.querySelector('.card-link').href;
  });

  const printWin = window.open('', '_blank');
  printWin.document.write(`<!DOCTYPE html><html><head>
    <meta charset="UTF-8">
    <title>인쇄 - ${checked.length}개 문제</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <link rel="stylesheet" href="assets/style.css">
    <style>
      .page-separator { page-break-before: always; }
      .problem-container { position: relative; }
      .loading { text-align: center; padding: 40px; font-size: 16px; color: #666; }
    </style>
  </head><body>
    <div class="loading" id="loading">문제 ${checked.length}개 로딩 중...</div>
  </body></html>`);

  let loaded = 0;
  const container = printWin.document.body;

  urls.forEach((url, i) => {
    fetch(url)
      .then(r => r.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const content = doc.querySelector('.content');
        const header = doc.querySelector('.header');
        const footer = doc.querySelector('.footer');
        const headerLine = doc.querySelector('.header-line');

        const wrapper = printWin.document.createElement('div');
        wrapper.className = 'problem-container' + (i > 0 ? ' page-separator' : '');
        if (header) wrapper.appendChild(header.cloneNode(true));
        if (headerLine) wrapper.appendChild(headerLine.cloneNode(true));
        if (content) wrapper.appendChild(content.cloneNode(true));
        if (footer) wrapper.appendChild(footer.cloneNode(true));

        wrapper.dataset.order = i;
        container.appendChild(wrapper);

        loaded++;
        if (loaded === urls.length) {
          printWin.document.getElementById('loading').remove();
          const wrappers = [...container.querySelectorAll('.problem-container')];
          wrappers.sort((a, b) => a.dataset.order - b.dataset.order);
          wrappers.forEach(w => container.appendChild(w));

          const katexScript = printWin.document.createElement('script');
          katexScript.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';
          katexScript.onload = () => {
            const renderScript = printWin.document.createElement('script');
            renderScript.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js';
            renderScript.onload = () => {
              printWin.renderMathInElement(printWin.document.body, {
                delimiters: [
                  {left: '\\\\[', right: '\\\\]', display: true},
                  {left: '\\\\(', right: '\\\\)', display: false}
                ],
                throwOnError: false
              });
              setTimeout(() => printWin.print(), 500);
            };
            printWin.document.head.appendChild(renderScript);
          };
          printWin.document.head.appendChild(katexScript);
        }
      });
  });
});

switchTab('물리');
applyReviewedStyles();

const splitOverlay = document.getElementById('split-overlay');
const splitTitle = document.getElementById('split-title');
const iframeProb = document.getElementById('iframe-prob');
const iframeSol = document.getElementById('iframe-sol');

let viewList = [];
let viewIndex = 0;

function buildViewList() {
  viewList = [];
  cards.forEach(card => {
    if (card.classList.contains('hidden')) return;
    const viewBtn = card.querySelector('.card-view');
    if (!viewBtn) return;
    viewList.push({
      prob: viewBtn.dataset.prob,
      sol: viewBtn.dataset.sol,
      uid: card.dataset.uid
    });
  });
}

const cacheBust = Date.now();

function getSplitTitle(uid) {
  const item = ALL_DATA.find(d => d.uid === uid);
  if (item) {
    const hasSol = viewList[viewIndex] && viewList[viewIndex].sol;
    const suffix = hasSol ? ' - 문제 / 해설' : ' - 문제';
    return item.year + ' ' + item.school + ' ' + (item.subject || '') + ' ' + (item.number || '') + suffix;
  }
  return uid;
}

function updateSplitUI() {
  const v = viewList[viewIndex];
  if (!v) return;
  iframeProb.src = v.prob + '?v=' + cacheBust;
  iframeSol.src = v.sol ? v.sol + '?v=' + cacheBust : 'about:blank';
  splitTitle.textContent = getSplitTitle(v.uid);
  document.getElementById('split-counter').textContent = (viewIndex + 1) + ' / ' + viewList.length;
  const isReviewed = !!reviewed[v.uid];
  document.getElementById('split-review-status').textContent = isReviewed ? '검수 완료' : '';
  document.getElementById('split-review-status').style.display = isReviewed ? 'inline-block' : 'none';
  preloadNext(5);
}

function openSplit(probUrl, solUrl, uid) {
  buildViewList();
  viewIndex = viewList.findIndex(v => v.uid === uid);
  if (viewIndex < 0) viewIndex = 0;
  splitOverlay.classList.add('active');
  updateSplitUI();
}

function closeSplit() {
  splitOverlay.classList.remove('active');
  iframeProb.src = '';
  iframeSol.src = '';
}

function preloadNext(count) {
  for (let i = 1; i <= count; i++) {
    let idx = (viewIndex + i) % viewList.length;
    const v = viewList[idx];
    if (v && !v._preloaded) {
      const l1 = document.createElement('link');
      l1.rel = 'prefetch';
      l1.href = v.prob;
      document.head.appendChild(l1);
      if (v.sol) {
        const l2 = document.createElement('link');
        l2.rel = 'prefetch';
        l2.href = v.sol;
        document.head.appendChild(l2);
      }
      v._preloaded = true;
    }
  }
}

function markReviewed() {
  const v = viewList[viewIndex];
  if (!v) return;
  reviewed[v.uid] = true;
  localStorage.setItem('hub_reviewed', JSON.stringify(reviewed));
  const card = document.querySelector(`.card[data-uid="${v.uid}"]`);
  if (card) card.classList.add('reviewed');
  applyFilters();
}

function navSplit(delta) {
  viewIndex += delta;
  if (viewIndex < 0) viewIndex = viewList.length - 1;
  if (viewIndex >= viewList.length) viewIndex = 0;
  updateSplitUI();
}

function navAndReview() {
  markReviewed();
  navSplit(1);
}

document.addEventListener('click', e => {
  const btn = e.target.closest('.card-view');
  if (!btn) return;
  e.preventDefault();
  const card = btn.closest('.card');
  openSplit(btn.dataset.prob, btn.dataset.sol, card.dataset.uid);
});

document.getElementById('btn-close-split').addEventListener('click', closeSplit);
document.getElementById('btn-prev').addEventListener('click', () => navSplit(-1));
document.getElementById('btn-next').addEventListener('click', () => navSplit(1));

document.addEventListener('keydown', e => {
  if (document.getElementById('report-modal').classList.contains('active')) {
    if (e.key === 'Escape') closeReportModal();
    return;
  }
  if (!splitOverlay.classList.contains('active')) return;
  if (e.key === 'Escape') closeSplit();
  if (e.key === 'ArrowLeft') navSplit(-1);
  if (e.key === 'ArrowRight') navSplit(1);
  if (e.key === 'Enter') { e.preventDefault(); navAndReview(); }
  if (e.key === 'Tab') { e.preventDefault(); openReportModal('문제'); }
});

const reportModal = document.getElementById('report-modal');
const reportUid = document.getElementById('report-uid');
const reportSide = document.getElementById('report-side');
const reportType = document.getElementById('report-type');
const reportMemo = document.getElementById('report-memo');
let reports = JSON.parse(localStorage.getItem('hub_reports') || '[]');

function updateReportBadge() {
  const badge = document.getElementById('report-badge');
  badge.textContent = reports.length;
  badge.style.display = reports.length > 0 ? 'inline-block' : 'none';
}
updateReportBadge();


function openReportModal(side) {
  const v = viewList[viewIndex];
  if (!v) return;
  reportUid.textContent = v.uid;
  reportSide.value = side;
  reportType.value = '';
  reportMemo.value = '';
  reportModal.classList.add('active');
  reportMemo.focus();
}

function closeReportModal() {
  reportModal.classList.remove('active');
}

document.getElementById('btn-report-cancel').addEventListener('click', closeReportModal);

document.getElementById('btn-report-save').addEventListener('click', () => {
  const v = viewList[viewIndex];
  if (!v) return;
  if (!reportType.value) {
    alert('유형을 선택하세요.');
    return;
  }
  reports.push({
    uid: v.uid,
    side: reportSide.value,
    type: reportType.value,
    memo: reportMemo.value.trim(),
    timestamp: new Date().toISOString()
  });
  localStorage.setItem('hub_reports', JSON.stringify(reports));
  updateReportBadge();
  closeReportModal();
});

document.getElementById('btn-export-csv').addEventListener('click', () => {
  if (reports.length === 0) {
    alert('보고된 항목이 없습니다.');
    return;
  }
  const bom = '\uFEFF';
  const header = 'uid,side,type,memo,timestamp\n';
  const rows = reports.map(r =>
    `${r.uid},${r.side},${r.type},"${(r.memo || '').replace(/"/g, '""')}",${r.timestamp}`
  ).join('\n');
  const blob = new Blob([bom + header + rows], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `report_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});

document.getElementById('btn-clear-reports').addEventListener('click', () => {
  if (reports.length === 0) return;
  if (!confirm(`보고 ${reports.length}건을 모두 삭제하시겠습니까?`)) return;
  reports = [];
  localStorage.setItem('hub_reports', JSON.stringify(reports));
  updateReportBadge();
});
