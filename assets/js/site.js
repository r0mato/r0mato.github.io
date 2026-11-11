/* r0mato.github.io — interacciones del sitio. Sin dependencias. */
(function () {
  'use strict';

  /* ── Tema claro / oscuro ──────────────────────────────────── */
  var root = document.documentElement;
  var toggle = document.getElementById('theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
    });
  }

  /* ── Menú móvil ───────────────────────────────────────────── */
  var navToggle = document.getElementById('nav-toggle');
  var nav = document.getElementById('nav');
  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  /* ── Filtros y búsqueda del archivo de writeups ───────────── */
  var list = document.getElementById('writeup-list');
  if (list) {
    var cards = [].slice.call(list.querySelectorAll('.card'));
    var search = document.getElementById('q');
    var counter = document.getElementById('results-count');
    var empty = document.getElementById('empty');
    var state = { severity: 'all', class: 'all', q: '' };

    function apply() {
      var shown = 0;
      cards.forEach(function (card) {
        var okSev = state.severity === 'all' || card.dataset.severity === state.severity;
        var okCls = state.class === 'all' || card.dataset.class === state.class;
        var hay = (card.dataset.title + ' ' + card.dataset.class + ' ' + card.dataset.tags);
        var okQ = !state.q || hay.indexOf(state.q) !== -1;
        var visible = okSev && okCls && okQ;
        card.hidden = !visible;
        if (visible) shown++;
      });
      if (counter) {
        var one = counter.dataset.one || 'resultado';
        var many = counter.dataset.many || 'resultados';
        counter.textContent = shown + ' ' + (shown === 1 ? one : many);
      }
      if (empty) empty.hidden = shown !== 0;
    }

    document.querySelectorAll('.filter').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var key = btn.dataset.key;
        state[key] = btn.dataset.value;
        btn.parentNode.querySelectorAll('.filter').forEach(function (b) {
          b.classList.toggle('is-active', b === btn);
        });
        apply();
      });
    });

    if (search) {
      search.addEventListener('input', function () {
        state.q = search.value.toLowerCase().trim();
        apply();
      });
    }
    apply();
  }

  /* ── Índice del artículo (se genera solo desde los h2/h3) ─── */
  var article = document.getElementById('article');
  var tocList = document.getElementById('toc-list');
  if (article && tocList) {
    var heads = [].slice.call(article.querySelectorAll('h2, h3'))
      .filter(function (h) { return !h.closest('.takeaways'); });

    if (heads.length < 2) {
      var toc = document.getElementById('toc');
      if (toc) toc.style.display = 'none';
    } else {
      heads.forEach(function (h, i) {
        if (!h.id) {
          h.id = (h.textContent || '').toLowerCase()
            .normalize('NFD').replace(/[̀-ͯ]/g, '')
            .replace(/[^a-z0-9\s-]/g, '').trim().replace(/\s+/g, '-') || ('seccion-' + i);
        }
        var li = document.createElement('li');
        li.className = 'lvl-' + h.tagName.charAt(1);
        var a = document.createElement('a');
        a.href = '#' + h.id;
        a.textContent = h.textContent;
        li.appendChild(a);
        tocList.appendChild(li);
      });

      var links = [].slice.call(tocList.querySelectorAll('a'));
      if ('IntersectionObserver' in window) {
        var seen = new Map();
        var obs = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) { seen.set(e.target.id, e.isIntersecting ? e.intersectionRatio : 0); });
          var best = null, bestTop = Infinity;
          heads.forEach(function (h) {
            var top = h.getBoundingClientRect().top;
            if (top < 140 && Math.abs(top) < bestTop) { bestTop = Math.abs(top); best = h.id; }
          });
          if (!best && heads[0]) best = heads[0].id;
          links.forEach(function (a) {
            a.classList.toggle('is-current', a.getAttribute('href') === '#' + best);
          });
        }, { rootMargin: '-80px 0px -60% 0px', threshold: [0, 0.5, 1] });
        heads.forEach(function (h) { obs.observe(h); });
      }
    }
  }

  /* ── Botón «copiar» en los bloques de código ──────────────── */
  var isEn = (document.documentElement.lang || 'es').indexOf('en') === 0;
  var labelIdle = isEn ? 'copy' : 'copiar';
  var labelDone = isEn ? 'copied!' : '¡copiado!';

  document.querySelectorAll('.prose pre').forEach(function (pre) {
    var btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.type = 'button';
    btn.textContent = labelIdle;
    btn.addEventListener('click', function () {
      var code = pre.querySelector('code') || pre;
      navigator.clipboard.writeText(code.innerText).then(function () {
        btn.textContent = labelDone;
        setTimeout(function () { btn.textContent = labelIdle; }, 1600);
      });
    });
    pre.appendChild(btn);
  });

  /* ── Lightbox de imágenes del writeup ─────────────────────── */
  var imgs = document.querySelectorAll('.prose img');
  if (imgs.length) {
    var box = null;
    imgs.forEach(function (img) {
      img.classList.add('zoomable');
      img.addEventListener('click', function () {
        if (!box) {
          box = document.createElement('div');
          box.style.cssText = 'position:fixed;inset:0;z-index:999;background:rgba(5,10,20,.92);' +
            'display:grid;place-items:center;padding:4vmin;cursor:zoom-out;overflow:auto';
          box.addEventListener('click', function () { box.style.display = 'none'; });
          document.body.appendChild(box);
        }
        box.innerHTML = '';
        var big = img.cloneNode();
        big.classList.remove('zoomable');
        big.style.cssText = 'max-width:100%;max-height:92vh;border-radius:8px;box-shadow:0 30px 60px rgba(0,0,0,.6)';
        box.appendChild(big);
        box.style.display = 'grid';
      });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && box) box.style.display = 'none';
    });
  }
})();
