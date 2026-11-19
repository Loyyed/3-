
(() => {
  'use strict';
  const query = (s, root = document) => root.querySelector(s);
  const all = (s, root = document) => [...root.querySelectorAll(s)];
  const selectors = all('[data-filter]');
  const filterRows = all('[data-search-row]');
  const status = query('#filter-status');
  function filter() {
    const terms = (query('#search')?.value || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
    let count = 0;
    for (const row of filterRows) {
      const fields = selectors.every(s => !s.value || (row.dataset[s.dataset.filter] || '').split('|').includes(s.value));
      const matches = fields && terms.every(x => row.dataset.searchRow.toLowerCase().includes(x));
      row.hidden = !matches;
      const nav = document.getElementById('nav-' + row.id);
      if (nav) nav.hidden = !matches;
      if (matches) count++;
    }
    if (status) status.textContent = count + ' 项';
  }
  for (const input of [...selectors, query('#search')].filter(Boolean)) input.addEventListener('input', filter);
  filter();
  const config = query('#charts');
  if (config) {
    const colors = ['#286750','#ac894a','#7c91a1','#a96f62','#829756','#727493'];
    const charts = JSON.parse(config.textContent);
    for (const figure of all('[data-chart]')) {
      const chart = charts[figure.dataset.chart], hidden = [];
      const target = query('.chart', figure);
      const draw = () => { target.innerHTML = ResultFeatures.chart(chart, hidden); };
      all('button[data-series]', figure).forEach((button, n) => {
        button.style.setProperty('--series', colors[n]);
        button.addEventListener('click', () => {
          const i = hidden.indexOf(n);
          if (i < 0) hidden.push(n);
          else hidden.splice(i, 1);
          button.setAttribute('aria-pressed', i < 0 ? 'false' : 'true');
          draw();
        });
      });
      draw();
    }
  }
  for (const link of all('a[href^="#"]')) {
    link.addEventListener('click', () => {
      const dest = document.getElementById(link.getAttribute('href').slice(1));
      if (!dest) return;
      const chapter = dest.closest('.chapter');
      if (chapter?.hidden) {
        for (const input of [...selectors, query('#search')].filter(Boolean)) input.value = '';
        filter();
      }
      for (let el = dest; el; el = el.parentElement) if (el.tagName === 'DETAILS') el.open = true;
      if (document.body.classList.contains('presenting') && chapter) {
        slide = slides.indexOf(chapter);
        drawSlide();
      }
    });
  }
  let slides = [], slide = 0;
  const present = query('#present');
  function drawSlide() {
    slides.forEach((el, i) => el.classList.toggle('active-slide', i === slide));
    if (query('#position')) query('#position').textContent =
      (slide + 1) + ' / ' + slides.length + ' · ' + (query('h2', slides[slide])?.textContent || '');
  }
  function step(amount) {
    slide = Math.max(0, Math.min(slides.length - 1, slide + amount));
    drawSlide();
    window.scrollTo(0, 0);
  }
  function end() {
    document.body.classList.remove('presenting');
    slides.forEach(x => x.classList.remove('active-slide'));
    present?.focus();
  }
  present?.addEventListener('click', () => {
    slides = all('.chapter').filter(el => !el.hidden && el.id !== 'methods');
    if (!slides.length) return;
    slide = 0;
    document.body.classList.add('presenting');
    drawSlide();
    window.scrollTo(0, 0);
    query('#exit').focus();
  });
  query('#previous')?.addEventListener('click', () => step(-1));
  query('#next-slide')?.addEventListener('click', () => step(1));
  query('#exit')?.addEventListener('click', end);
  document.addEventListener('keydown', e => {
    if (!document.body.classList.contains('presenting')) return;
    if (e.key === 'Escape') end();
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      step(e.key === 'ArrowLeft' ? -1 : 1);
    }
  });
})();
