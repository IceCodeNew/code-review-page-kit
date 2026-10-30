
(function () {
  const files = Array.from(document.querySelectorAll('.file'));
  const groups = Array.from(document.querySelectorAll('.group'));
  const navGroups = Array.from(document.querySelectorAll('.nav-group'));

  const COLOR = ['#b42318','#1d4ed8','#0f766e','#b45309','#6d28d9','#be185d'];
  const ASK = 'review-ask:';
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
  };

  function hydrateAsk(root) {
    (root || document).querySelectorAll('.ask-input, #global-ask').forEach((el) => {
      const key = ASK + (el.id === 'global-ask' ? 'global' : el.dataset.key);
      const saved = store.get(key);
      if (saved !== null && el.value === '') el.value = saved;
      el.addEventListener('input', () => {
        store.set(key, el.value);
        const file = el.closest('.file');
        if (file) setTimeout(() => layout(file), 100);
      });
    });
  }

  function downloadText(name, text) {
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  async function copyText(text, btn, idle) {
    let ok = false;
    try { await navigator.clipboard.writeText(text); ok = true; }
    catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { ok = document.execCommand('copy'); } catch { ok = false; }
      ta.remove();
    }
    btn.textContent = ok ? '已复制' : '复制失败';
    setTimeout(() => btn.textContent = idle, 1600);
  }

  function originNote(note) {
    if (!note.closest('.modal')) return note;
    const fileId = note.dataset.originFile;
    const noteId = note.dataset.originNote;
    return document.querySelector('#' + CSS.escape(fileId || '') + ' .note[data-note="' + noteId + '"]') || note;
  }

  function questionText(note) {
    const input = note.querySelector('.ask-input');
    return input ? input.value.trim() : '';
  }

  function notePrompt(note) {
    const orig = originNote(note);
    const file = orig.closest('.file');
    const path = orig.dataset.path || '';
    const letter = orig.dataset.letter || '';
    const span = orig.dataset.span || '';
    const what = orig.dataset.what || '';
    const why = orig.dataset.why || '';
    const id = orig.dataset.note;
    const diff = Array.from(file.querySelectorAll('.dl[data-note="' + id + '"]')).map((el) => {
      const sign = el.classList.contains('add') ? '+' : el.classList.contains('del') ? '-' : ' ';
      const code = el.querySelector('.code');
      return sign + (code ? code.textContent : '');
    }).join('\n');
    const q = questionText(note) || '(no question typed)';
    return '# Question about `' + path + '` · block ' + letter + ' (new lines ' + span + ')\n\n' +
      '## Review note\n**What changed:** ' + what + '\n\n**Why:** ' + why + '\n\n' +
      '## Code under review\n````diff\n' + diff + '\n````\n\n' +
      '## Question / request\n' + q + '\n';
  }

  function globalPrompt() {
    const q = (document.getElementById('global-ask').value || '').trim() || '(no question typed)';
    const title = document.body.dataset.title || 'the review';
    const heads = document.body.dataset.heads || '';
    return '# Follow-up on ' + title + '\n\n' +
      (heads ? 'Reviewed heads: ' + heads + '.\n' : '') +
      'Use `review-prompt.md` from the review page as the implementation brief.\n\n' +
      '## My question / request\n' + q + '\n';
  }

  function askFilename(note) {
    const orig = originNote(note);
    const slug = String(orig.dataset.path || 'review').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return 'question-' + slug + '-' + (orig.dataset.letter || 'note') + '.md';
  }

  function layout(file) {
    const body = file.querySelector('.file-body');
    if (!body) return;
    const notes = Array.from(body.querySelectorAll('.note'));
    if (!notes.length) return;
    const code = body.querySelector('.code-col');
    if (!code.offsetWidth) return;
    const bodyRect = body.getBoundingClientRect();
    let bottom = 0;
    const wires = [];
    notes.forEach((note) => {
      if (note.classList.contains('filtered-out')) {
        note.style.display = 'none';
        const bh = body.querySelector('.badge[data-note="' + note.dataset.note + '"]');
        if (bh) bh.style.display = 'none';
        return;
      }
      const id = note.dataset.note;
      const lines = body.querySelectorAll('.dl[data-note="' + id + '"]');
      if (!lines.length) {
        note.style.display = 'none';
        const b0 = body.querySelector('.badge[data-note="' + id + '"]');
        if (b0) b0.style.display = 'none';
        return;
      }
      note.style.display = '';
      const first = lines[0].getBoundingClientRect();
      let top = Math.max(first.top - bodyRect.top, 0);
      if (top < bottom + 8) top = bottom + 8;
      note.style.top = top + 'px';
      bottom = top + note.offsetHeight;
      const nr = note.getBoundingClientRect();
      const badge = body.querySelector('.badge[data-note="' + id + '"]');
      const badgeX = code.getBoundingClientRect().width - 20;
      if (badge) {
        badge.style.top = (first.top - bodyRect.top) + 'px';
        badge.style.left = badgeX + 'px';
        badge.style.display = '';
      }
      wires.push({
        x1: badgeX + 9,
        y1: first.top - bodyRect.top + 10,
        x2: nr.left - bodyRect.left - 2,
        y2: top + 14,
        c: getComputedStyle(note).getPropertyValue('--c').trim() || '#b42318',
      });
    });
    const svg = body.querySelector('.wires');
    const h = Math.max(code.scrollHeight, bottom + 12);
    body.style.minHeight = Math.max(h, code.offsetHeight) + 'px';
    svg.setAttribute('viewBox', '0 0 ' + body.clientWidth + ' ' + Math.max(h, 10));
    svg.setAttribute('width', body.clientWidth);
    svg.setAttribute('height', Math.max(h, 10));
    svg.innerHTML = wires.map((w) => {
      const mid = Math.max(12, (w.x2 - w.x1) / 2);
      return '<path d="M ' + w.x1 + ' ' + w.y1 + ' C ' + (w.x1 + mid) + ' ' + w.y1 + ', ' + (w.x2 - mid) + ' ' + w.y2 + ', ' + w.x2 + ' ' + w.y2 + '" fill="none" stroke="' + w.c + '" stroke-width="1.3" opacity=".85"></path>' +
             '<circle cx="' + w.x1 + '" cy="' + w.y1 + '" r="2.6" fill="' + w.c + '"></circle>' +
             '<circle cx="' + w.x2 + '" cy="' + w.y2 + '" r="2.2" fill="#fff" stroke="' + w.c + '" stroke-width="1.3"></circle>';
    }).join('');
    if (body.style.minHeight !== '0px') {
      const minH = parseFloat(body.style.minHeight);
      if (svg.getAttribute('height') < minH) svg.setAttribute('height', minH);
    }
  }

  function layoutAll() {
    files.forEach((f) => {
      if (f.classList.contains('hidden') || f.classList.contains('folded')) return;
      layout(f);
    });
  }

  document.getElementById('expand').addEventListener('click', () => document.querySelectorAll('details.fold').forEach((d) => d.open = true));
  document.getElementById('collapse').addEventListener('click', () => document.querySelectorAll('details.fold').forEach((d) => d.open = false));
  document.querySelectorAll('details.fold').forEach((d) => d.addEventListener('toggle', () => {
    const file = d.closest('.file');
    if (file) layout(file);
  }));

  let filter = 'all';
  const chips = Array.from(document.querySelectorAll('.btn.flt'));
  const search = document.getElementById('search');
  function apply() {
    const q = search.value.trim().toLowerCase();
    const visible = new Set();
    files.forEach((file) => {
      let ok = true;
      const antiNotes = file.querySelectorAll('.note[data-anti="1"]').length;
      if (filter === 'key') ok = Number(file.dataset.stars) >= 4;
      else if (filter === 'anti') ok = antiNotes > 0;
      else if (filter !== 'all') ok = file.dataset.pr.split('+').includes(filter);
      if (ok && q) ok = file.dataset.search.toLowerCase().includes(q);
      file.querySelectorAll('.note').forEach((note) => {
        const dim = filter === 'anti' && note.dataset.anti !== '1';
        note.classList.toggle('filtered-out', dim);
      });
      file.querySelectorAll('.badge').forEach((b) => {
        const note = file.querySelector('.note[data-note="' + b.dataset.note + '"]');
        b.classList.toggle('filtered-out', !note || note.classList.contains('filtered-out'));
      });
      file.querySelectorAll('.dl.ann').forEach((line) => {
        const note = file.querySelector('.note[data-note="' + line.dataset.note + '"]');
        line.classList.toggle('ann-muted', !note || note.classList.contains('filtered-out'));
      });
      file.classList.toggle('hidden', !ok);
      if (ok) visible.add(file.id);
    });
    groups.forEach((g) => {
      const any = Array.from(g.querySelectorAll('.file')).some((f) => !f.classList.contains('hidden'));
      g.classList.toggle('hidden', !any);
    });
    navGroups.forEach((g) => {
      let any = false;
      g.querySelectorAll('.nav-file').forEach((a) => {
        const show = visible.has(a.getAttribute('href').slice(1));
        a.classList.toggle('hidden', !show);
        any = any || show;
      });
      g.classList.toggle('hidden', !any);
    });
    requestAnimationFrame(layoutAll);
  }
  chips.forEach((c) => c.addEventListener('click', () => {
    filter = c.dataset.f;
    chips.forEach((x) => x.setAttribute('aria-pressed', String(x === c)));
    apply();
  }));
  search.addEventListener('input', apply);

  const modal = document.getElementById('modal');
  const modalBody = document.getElementById('modal-body');
  modal.querySelector('.close').addEventListener('click', () => modal.classList.remove('open'));
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('open'); });

  document.addEventListener('click', (e) => {
    const b = e.target.closest('.badge');
    if (!b) return;
    const file = b.closest('.file');
    const note = file.querySelector('.note[data-note="' + b.dataset.note + '"]');
    if (!note) return;
    if (window.innerWidth > 1240) {
      note.classList.remove('flash');
      void note.offsetWidth;
      note.classList.add('flash');
    } else {
      const clone = note.cloneNode(true);
      clone.style.position = 'static';
      clone.style.top = 'auto';
      clone.style.left = '0';
      clone.style.right = 'auto';
      clone.style.width = '100%';
      clone.classList.remove('flash');
      clone.dataset.originFile = file.id;
      clone.dataset.originNote = note.dataset.note;
      modalBody.replaceChildren(clone);
      hydrateAsk(clone);
      modal.classList.add('open');
    }
  });

  document.addEventListener('click', (e) => {
    const copy = e.target.closest('.ask-copy');
    if (copy) {
      const note = copy.closest('.note');
      if (!questionText(note)) {
        const input = note.querySelector('.ask-input');
        if (input) input.focus();
        copy.textContent = '请先输入';
        setTimeout(() => copy.textContent = '复制提问', 1400);
        return;
      }
      copyText(notePrompt(note), copy, '复制提问');
      return;
    }
    const dl = e.target.closest('.ask-download');
    if (dl) {
      const note = dl.closest('.note');
      if (!questionText(note)) {
        const input = note.querySelector('.ask-input');
        if (input) input.focus();
        dl.textContent = '请先输入';
        setTimeout(() => dl.textContent = '下载 .md', 1400);
        return;
      }
      downloadText(askFilename(note), notePrompt(note));
      dl.textContent = '已下载';
      setTimeout(() => dl.textContent = '下载 .md', 1400);
      return;
    }
    if (e.target.id === 'global-copy') {
      const q = (document.getElementById('global-ask').value || '').trim();
      if (!q) { document.getElementById('global-ask').focus(); return; }
      copyText(globalPrompt(), e.target, '复制问题');
      return;
    }
    if (e.target.id === 'global-download') {
      const q = (document.getElementById('global-ask').value || '').trim();
      if (!q) { document.getElementById('global-ask').focus(); return; }
      downloadText('review-question.md', globalPrompt());
      e.target.textContent = '已下载';
      setTimeout(() => e.target.textContent = '下载 .md', 1400);
    }
  });

  document.querySelectorAll('details.ask').forEach((d) => d.addEventListener('toggle', () => {
    const file = d.closest('.file');
    if (file) setTimeout(() => layout(file), 0);
  }));

  hydrateAsk(document);

  let timer = null;
  window.addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(layoutAll, 120); });
  window.addEventListener('load', layoutAll);
  requestAnimationFrame(layoutAll);
  setTimeout(layoutAll, 400);
  const copyBtn = document.getElementById('copy-prompt');
  if (copyBtn) copyBtn.addEventListener('click', async () => {
    const text = document.getElementById('prompt-body').textContent;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = '已复制';
      setTimeout(() => copyBtn.textContent = '复制 Markdown', 1400);
    } catch {
      const range = document.createRange(); range.selectNodeContents(document.getElementById('prompt-body'));
      const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
      copyBtn.textContent = '请按 Ctrl/Cmd+C';
    }
  });

  const themeBtn = document.getElementById('theme');
  const mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  function themePref() {
    return document.documentElement.dataset.pref || 'auto';
  }
  function applyTheme(pref) {
    const dark = pref === 'dark' || (pref === 'auto' && mq && mq.matches);
    document.documentElement.dataset.pref = pref;
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    try { localStorage.setItem('review-theme', pref); } catch (e) {}
    if (themeBtn) {
      themeBtn.textContent = pref === 'auto' ? 'Auto' : pref === 'dark' ? 'Dark' : 'Light';
      themeBtn.title = 'Theme: ' + pref + ' (click to cycle)';
      themeBtn.setAttribute('aria-label', 'Theme: ' + pref + '; click to cycle');
    }
  }
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const order = ['auto', 'light', 'dark'];
      const next = order[(order.indexOf(themePref()) + 1) % order.length];
      applyTheme(next);
    });
  }
  if (mq) mq.addEventListener('change', () => { if (themePref() === 'auto') applyTheme('auto'); });
  applyTheme(themePref());

  window.addEventListener('beforeprint', () => {
    printTheme = document.documentElement.dataset.theme;
    if (printTheme === 'dark') document.documentElement.dataset.theme = 'light';
    document.querySelectorAll('details.fold').forEach((d) => d.open = true);
    layoutAll();
  });
  window.addEventListener('afterprint', () => {
    if (printTheme) document.documentElement.dataset.theme = printTheme;
  });
})();
