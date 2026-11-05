/* Căminul Adina — scripturi site (fără dependențe) */
(function () {
  'use strict';
  var CFG = window.ADINA || {};
  var KEY = 'adina-consent';
  var VERSION = 1;

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function store(get, val) {
    try {
      if (get) return JSON.parse(localStorage.getItem(KEY) || 'null');
      localStorage.setItem(KEY, JSON.stringify(val));
    } catch (e) { return null; }
  }

  /* ---------- meniu mobil ---------- */
  var menuBtn = $('.menu-btn'), nav = $('.nav');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      menuBtn.textContent = open ? 'Închide' : 'Meniu';
    });
  }
  /* dropdown locații: se închide la click în afară */
  document.addEventListener('click', function (e) {
    $$('.drop[open]').forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute('open'); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') $$('.drop[open]').forEach(function (d) { d.removeAttribute('open'); d.querySelector('summary').focus(); });
  });

  /* ---------- bara de apel pe mobil ---------- */
  var bar = $('.callbar'), heroCta = $('[data-hero-cta]'), typing = false, heroGone = false;
  function updBar() { if (bar) bar.classList.toggle('show', heroGone && !typing); }
  if (bar) {
    if (heroCta && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (en) { heroGone = !en[0].isIntersecting; updBar(); }).observe(heroCta);
    } else { heroGone = true; updBar(); }
    $$('form').forEach(function (f) {
      f.addEventListener('focusin', function () { typing = true; updBar(); });
      f.addEventListener('focusout', function () { setTimeout(function () { typing = f.contains(document.activeElement); updBar(); }, 0); });
    });
  }

  /* ---------- postere video, încărcate când se apropie de ecran ---------- */
  var vids = $$('video[data-poster]');
  function setPoster(v) { v.poster = v.getAttribute('data-poster'); v.removeAttribute('data-poster'); }
  if ('IntersectionObserver' in window) {
    var vio = new IntersectionObserver(function (en) { en.forEach(function (e) { if (e.isIntersecting) { setPoster(e.target); vio.unobserve(e.target); } }); }, { rootMargin: '400px 0px' });
    vids.forEach(function (v) { vio.observe(v); });
  } else vids.forEach(setPoster);

  /* ---------- galerie + lightbox ---------- */
  var lb, lbImg, lbCnt, list = [], idx = 0, lastFocus;
  function buildLb() {
    lb = document.createElement('div');
    lb.className = 'lb'; lb.setAttribute('role', 'dialog'); lb.setAttribute('aria-modal', 'true'); lb.setAttribute('aria-label', 'Fotografie mărită');
    lb.innerHTML = '<img alt=""><button class="x" type="button" aria-label="Închide">×</button><button class="pv" type="button" aria-label="Fotografia anterioară">‹</button><button class="nx" type="button" aria-label="Fotografia următoare">›</button><div class="cnt" aria-live="polite"></div>';
    document.body.appendChild(lb);
    lbImg = $('img', lb); lbCnt = $('.cnt', lb);
    $('.x', lb).onclick = closeLb; $('.pv', lb).onclick = function () { show(idx - 1); }; $('.nx', lb).onclick = function () { show(idx + 1); };
    lb.addEventListener('click', function (e) { if (e.target === lb) closeLb(); });
    document.addEventListener('keydown', function (e) {
      if (!lb.classList.contains('open')) return;
      if (e.key === 'Escape') closeLb();
      if (e.key === 'ArrowLeft') show(idx - 1);
      if (e.key === 'ArrowRight') show(idx + 1);
      if (e.key === 'Tab') { var b = $$('button', lb), i = b.indexOf(document.activeElement); e.preventDefault(); b[(i + (e.shiftKey ? -1 : 1) + b.length) % b.length].focus(); }
    });
  }
  function show(i) {
    idx = (i + list.length) % list.length;
    var b = list[idx];
    lbImg.src = b.getAttribute('data-full'); lbImg.alt = $('img', b).alt;
    lbCnt.textContent = (idx + 1) + ' din ' + list.length;
  }
  function closeLb() { lb.classList.remove('open'); document.body.style.overflow = ''; if (lastFocus) lastFocus.focus(); }
  $$('.gallery').forEach(function (g) {
    var items = $$('button[data-full]', g);
    items.forEach(function (b, i) {
      b.addEventListener('click', function () {
        if (!lb) buildLb();
        list = items; lastFocus = b; // toate pozele galeriei, inclusiv cele ascunse sub „Vezi toate”
        show(list.indexOf(b)); lb.classList.add('open'); document.body.style.overflow = 'hidden'; $('.x', lb).focus();
      });
    });
  });
  $$('[data-expand]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var g = document.getElementById(btn.getAttribute('data-expand'));
      var first = $('.more-hidden', g);
      g.classList.add('expanded'); btn.remove();
      if (first) first.focus();
    });
  });

  /* ---------- consimțământ (GDPR) ---------- */
  var banner = $('#consent'), dlg = $('#consent-dialog');
  var state = store(true);
  if (state && (state.v !== VERSION || (state.ts && Date.now() - Date.parse(state.ts) > 365 * 864e5))) state = null; // reîntrebăm după 12 luni

  function save(s) {
    s.v = VERSION; s.ts = new Date().toISOString();
    store(false, s); state = s; apply();
    if (banner) banner.hidden = true;
  }
  function apply() {
    if (!state) return;
    if (state.externe) $$('[data-embed]').forEach(loadEmbed);
    if (state.statistici && CFG.ga4) loadGA(CFG.ga4);
    if (window.gtag) gtag('consent', 'update', { analytics_storage: state.statistici ? 'granted' : 'denied' });
  }
  function loadGA(id) {
    if (window.__ga) return; window.__ga = true;
    var s = document.createElement('script'); s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || []; window.gtag = function () { dataLayer.push(arguments); };
    gtag('consent', 'default', { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'granted' });
    gtag('js', new Date()); gtag('config', id, { anonymize_ip: true });
  }
  function loadEmbed(box) {
    if (box.getAttribute('data-loaded')) return;
    var f = document.createElement('iframe');
    f.src = box.getAttribute('data-embed'); f.title = box.getAttribute('data-title') || 'Conținut extern';
    f.loading = 'lazy'; f.allow = 'autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share'; f.allowFullscreen = true;
    f.referrerPolicy = 'strict-origin-when-cross-origin';
    box.appendChild(f); box.setAttribute('data-loaded', '1');
  }
  $$('[data-embed]').forEach(function (box) {
    var once = $('[data-load-once]', box), always = $('[data-load-always]', box);
    if (once) once.addEventListener('click', function () { loadEmbed(box); });
    if (always) always.addEventListener('click', function () { var s = state || { statistici: false }; s.externe = true; save(s); });
  });

  if (banner && !state) banner.hidden = false;
  $$('[data-consent=all]').forEach(function (b) { b.addEventListener('click', function () { save({ statistici: true, externe: true }); if (dlg && dlg.open) dlg.close(); }); });
  $$('[data-consent=none]').forEach(function (b) { b.addEventListener('click', function () { save({ statistici: false, externe: false }); if (dlg && dlg.open) dlg.close(); }); });
  $$('[data-consent=settings]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (!dlg) return;
      $('#c-stat', dlg).checked = !!(state && state.statistici);
      $('#c-ext', dlg).checked = !!(state && state.externe);
      dlg.showModal();
    });
  });
  if (dlg) {
    $('[data-consent=save]', dlg).addEventListener('click', function () {
      save({ statistici: $('#c-stat', dlg).checked, externe: $('#c-ext', dlg).checked }); dlg.close();
    });
  }
  apply();

  /* ---------- formular programare vizită ---------- */
  var form = $('#visit-form');
  if (form) {
    var msg = $('.form-msg', form);
    var MSG = {
      nume: 'Scrieți numele, ca să știm cu cine vorbim.',
      telefon: 'Scrieți un număr de telefon, ca să vă putem suna.',
      telScurt: 'Numărul pare incomplet. Are nevoie de 10 cifre, de exemplu 0756 604 755.',
      acord: 'Bifați acordul, altfel nu vă putem contacta.'
    };
    var preset = new URLSearchParams(location.search).get('locatia');
    if (preset && form.locatia) { $$('option', form.locatia).forEach(function (o) { if (o.value === preset) form.locatia.value = preset; }); }
    function check(i) {
      var m = '';
      if (i.type === 'checkbox') { if (!i.checked) m = MSG.acord; }
      else if (!i.value.trim()) m = MSG[i.name];
      else if (i.name === 'telefon' && i.value.replace(/\D/g, '').replace(/^40/, '0').length < 10) m = MSG.telScurt;
      var e = document.getElementById(i.getAttribute('aria-describedby'));
      if (e) { e.textContent = m; e.hidden = !m; }
      if (m) i.setAttribute('aria-invalid', 'true'); else i.removeAttribute('aria-invalid');
      return !m;
    }
    $$('[required]', form).forEach(function (i) {
      i.addEventListener(i.type === 'checkbox' ? 'change' : 'input', function () { if (i.hasAttribute('aria-invalid')) check(i); });
    });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (form.website && form.website.value) return; // capcană anti-spam
      var bad = $$('[required]', form).filter(function (i) { return !check(i); });
      if (bad.length) {
        msg.className = 'form-msg bad';
        msg.textContent = bad.length === 1 ? 'Mai e un câmp de completat, marcat cu roșu.' : 'Mai sunt ' + bad.length + ' câmpuri de completat, marcate cu roșu.';
        bad[0].focus(); return;
      }
      var data = {};
      $$('input,select,textarea', form).forEach(function (i) { if (i.name && i.name !== 'website') data[i.name] = i.type === 'checkbox' ? (i.checked ? 'da' : 'nu') : i.value.trim(); });
      var text = 'Cerere de vizită – Căminul Adina\n\nNume: ' + data.nume + '\nTelefon: ' + data.telefon + (data.email ? '\nE-mail: ' + data.email : '') +
        '\nLocația dorită: ' + data.locatia + '\nPentru: ' + data.pentru + (data.mesaj ? '\nMesaj: ' + data.mesaj : '') + '\nAcord prelucrare date: ' + data.acord;
      if (CFG.formEndpoint) {
        var btn = $('button[type=submit]', form); btn.disabled = true; btn.textContent = 'Se trimite…';
        fetch(CFG.formEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(Object.assign({ subject: 'Cerere de vizită – Căminul Adina' }, data)) })
          .then(function (r) { if (!r.ok) throw new Error(r.status); msg.className = 'form-msg ok'; msg.textContent = 'Cererea de vizită a fost trimisă. Vă sunăm în cel mai scurt timp, în programul 10:00–18:00.'; form.reset(); btn.textContent = 'Cerere trimisă'; })
          .catch(function () { btn.disabled = false; btn.textContent = 'Trimite cererea de vizită'; msg.className = 'form-msg bad'; msg.textContent = 'Cererea nu s-a putut trimite. Sunați-ne la ' + CFG.phone + ' sau scrieți-ne pe WhatsApp.'; });
      } else {
        location.href = 'mailto:' + CFG.email + '?subject=' + encodeURIComponent('Cerere de vizită – Căminul Adina') + '&body=' + encodeURIComponent(text);
        msg.className = 'form-msg ok';
        msg.innerHTML = 'Am deschis aplicația de e-mail cu cererea completată. Dacă nu s-a deschis, trimiteți-o pe <a href="https://wa.me/' + CFG.whatsapp + '?text=' + encodeURIComponent(text) + '">WhatsApp</a> sau sunați la ' + CFG.phone + '.';
      }
    });
  }
})();
