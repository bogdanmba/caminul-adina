#!/usr/bin/env python3
"""
Generatorul site-ului Căminul Adina.

  python build.py                      -> build de previzualizare în dist/ (noindex)
  python build.py --env production     -> build final pentru caminul-adina.ro (indexabil)
  python build.py --site-url https://utilizator.github.io/caminul-adina

Conținutul se editează în content/*.json, pozele stau în media/.
Pillow (pip install pillow) generează variantele responsive ale pozelor; ffmpeg, dacă există,
generează posterele video și comprimă videoclipurile mari. Fără ele, build-ul merge oricum.
"""
import argparse, datetime as dt, hashlib, html, json, os, re, shutil, subprocess, sys
from pathlib import Path
from urllib.parse import quote, quote_plus

ROOT = Path(__file__).resolve().parent
CONTENT, SRC, MEDIA = ROOT / 'content', ROOT / 'src', ROOT / 'media'
CACHE = ROOT / '.cache'

try:
    from PIL import Image
except Exception:  # Pillow lipsește: folosim pozele așa cum sunt
    Image = None

# ------------------------------------------------------------------ utilitare
E = lambda s: html.escape(str(s), quote=True)

def load(name):
    return json.loads((CONTENT / name).read_text(encoding='utf-8'))

def lei(n):
    return f'{n:,}'.replace(',', '.') + ' lei'

def write(out, rel, text):
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')

ICONS = {
 'phone': '<path d="M6.6 10.8a15.5 15.5 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1z" fill="currentColor"/>',
 'whatsapp': '<path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18a8 8 0 0 1-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8 8 0 1 1 12 20Zm4.4-6c-.2-.1-1.4-.7-1.7-.8-.2-.1-.4-.1-.5.1l-.8 1c-.1.2-.3.2-.5.1a6.5 6.5 0 0 1-3.2-2.8c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.5-.4h-.5a.9.9 0 0 0-.6.3 2.7 2.7 0 0 0-.9 2c0 1.2.9 2.4 1 2.5.1.2 1.7 2.7 4.2 3.7 1.6.7 2.2.7 3 .6.5-.1 1.4-.6 1.6-1.1.2-.6.2-1 .1-1.1l-.6-.4Z"/>',
 'facebook': '<path fill="currentColor" d="M14 8.5V6.7c0-.8.5-1 .9-1H17V2.1L14.1 2C10.9 2 10 4.4 10 6v2.5H8V12h2v10h4V12h2.7l.4-3.5H14Z"/>',
 'messenger': '<path fill="currentColor" d="M12 2C6.4 2 2 6.1 2 11.4c0 3 1.5 5.6 3.8 7.3V22l3.4-1.9c.9.3 1.8.4 2.8.4 5.6 0 10-4.1 10-9.4S17.6 2 12 2Zm1 12.6-2.5-2.7-4.9 2.7 5.4-5.7 2.6 2.7 4.8-2.7-5.4 5.7Z"/>',
 'mail': '<path fill="currentColor" d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm9 7.2L4.2 7v10h15.6V7L12 12.2ZM5.4 7 12 11.4 18.6 7H5.4Z"/>',
 'pin': '<path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z"/>',
 'check': '<path fill="currentColor" d="m9.5 16.2-4.2-4.2-1.4 1.4 5.6 5.6L21.5 7l-1.4-1.4z"/>',
 'clock': '<path fill="currentColor" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 10.4 3.5 2.1-.8 1.3L11 13V7h2v5.4Z"/>',
 'instagram': '<path fill="currentColor" d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm0 2a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H7Zm5 3.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9Zm0 2a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5ZM17.5 5.5a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"/>',
 'tiktok': '<path fill="currentColor" d="M16.6 5.8A4.3 4.3 0 0 1 15.5 3h-3.2v12.4a2.6 2.6 0 1 1-2.6-2.6c.3 0 .5 0 .8.1V9.6a5.8 5.8 0 1 0 5 5.8V9.1a7.4 7.4 0 0 0 4.3 1.4V7.3a4.3 4.3 0 0 1-3.2-1.5Z"/>',
 'youtube': '<path fill="currentColor" d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12a26 26 0 0 0 .4 4.8 2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8A26 26 0 0 0 22 12a26 26 0 0 0-.4-4.8ZM10 15V9l5.2 3L10 15Z"/>',
}
def icon(name):
    return f'<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'


# ------------------------------------------------------------------ media
class Media:
    """Găsește pozele în media/, generează variante și ține evidența lor."""
    def __init__(self, out, locs):
        self.out = out
        self.locs = {l['key']: l for l in locs}
        self.excl = set()
        f = CONTENT / 'media-excluse.txt'
        if f.exists():
            self.excl = {ln.strip() for ln in f.read_text(encoding='utf-8').splitlines() if ln.strip() and not ln.startswith('#')}
        self.alts = load('media-alt.json') if (CONTENT / 'media-alt.json').exists() else {}
        self.missing = []
        self._done = {}

    def _src(self, rel):
        p = MEDIA / rel
        return p if p.exists() else None

    def image(self, rel, alt=None, key=None):
        """Întoarce dict cu src, srcset, w, h, alt; dacă poza lipsește, un placeholder."""
        if rel in self._done:
            d = dict(self._done[rel]); d['alt'] = alt or self.alts.get(rel) or d['alt']; return d
        src = self._src(rel) if rel else None
        alt = alt or self.alts.get(rel, '')
        if not src:
            self.missing.append(rel)
            return self.placeholder(key, alt)
        base = 'assets/media/' + re.sub(r'\.[a-z0-9]+$', '', rel, flags=re.I)
        ext = src.suffix.lower()
        widths = [480, 960, 1600]
        variants = {}
        if Image and ext in ('.webp', '.jpg', '.jpeg', '.png'):
            im = Image.open(src)
            w0, h0 = im.size
            for w in widths:
                if w > w0 and w != widths[0] and variants:
                    continue
                tw = min(w, w0)
                th = round(h0 * tw / w0)
                dst = self.out / f'{base}-{tw}.webp'
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    cached = CACHE / f'{hashlib.md5((rel + str(tw) + str(src.stat().st_mtime)).encode()).hexdigest()}.webp'
                    if not cached.exists():
                        CACHE.mkdir(exist_ok=True)
                        im2 = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') and ext == '.png' else 'RGB')
                        im2.resize((tw, th), Image.LANCZOS).save(cached, 'WEBP', quality=78, method=6)
                    shutil.copyfile(cached, dst)
                variants[tw] = (f'{base}-{tw}.webp', tw, th)
            big = max(variants)
            d = {'src': variants[big][0], 'srcset': ', '.join(f'{v[0]} {v[1]}w' for v in variants.values()),
                 'w': variants[big][1], 'h': variants[big][2], 'alt': alt, 'full': variants[big][0]}
        else:
            dst = self.out / f'assets/media/{rel}'
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            d = {'src': f'assets/media/{rel}', 'srcset': '', 'w': 1200, 'h': 900, 'alt': alt, 'full': f'assets/media/{rel}'}
        self._done[rel] = d
        return dict(d)

    def placeholder(self, key, alt):
        color = self.locs.get(key, {}).get('color', '#8FA3B5')
        name = f'assets/media/placeholder-{key or "general"}.svg'
        p = self.out / name
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><rect width="800" height="600" fill="{color}"/><path d="M300 420V300l100-80 100 80v120z" fill="#fff" opacity=".35"/></svg>', encoding='utf-8')
        return {'src': name, 'srcset': '', 'w': 800, 'h': 600, 'alt': alt, 'full': name}

    def gallery(self, key):
        """Toate pozele unei locații: întâi cele de pe Facebook (mai noi), apoi cele de pe site-ul vechi."""
        rels = []
        for folder in (f'facebook/{key}', f'site/{key}'):
            d = MEDIA / folder
            if d.exists():
                rels += sorted(f'{folder}/{p.name}' for p in d.iterdir() if p.suffix.lower() in ('.webp', '.jpg', '.jpeg', '.png'))
        rels = [r for r in rels if r not in self.excl]
        name = self.locs[key]['name']
        out = []
        for i, r in enumerate(rels, 1):
            out.append(self.image(r, self.alts.get(r) or f'Căminul Adina {name} – fotografie {i}', key))
        return out

    def videos(self, key):
        d = MEDIA / f'site/{key}/video'
        if not d.exists():
            return []
        res = []
        for p in sorted(d.glob('*.mp4')):
            rel = f'site/{key}/video/{p.name}'
            if rel in self.excl:
                continue
            dst = self.out / 'assets/media' / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            src = p
            if shutil.which('ffmpeg') and p.stat().st_size > 6 * 1024 * 1024:
                cached = CACHE / f'{hashlib.md5((rel + str(p.stat().st_mtime)).encode()).hexdigest()}.mp4'
                if not cached.exists():
                    CACHE.mkdir(exist_ok=True)
                    tmp = cached.with_suffix('.tmp.mp4')  # scriem întâi temporar, ca o întrerupere să nu lase un fișier stricat
                    r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(p), '-vf', "scale='min(720,iw)':-2", '-c:v', 'libx264', '-crf', '28', '-preset', 'medium', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(tmp)], check=False)
                    if r.returncode == 0 and tmp.exists():
                        tmp.replace(cached)
                if cached.exists() and cached.stat().st_size < p.stat().st_size:
                    src = cached
            shutil.copyfile(src, dst)
            poster = ''
            ready = p.with_suffix('.jpg')  # poster pregătit în media/ (merge și fără ffmpeg, de ex. pe GitHub)
            if ready.exists():
                shutil.copyfile(ready, dst.with_suffix('.jpg'))
                poster = f'assets/media/{rel[:-4]}.jpg'
            elif shutil.which('ffmpeg'):
                pp = dst.with_suffix('.jpg')
                if not pp.exists():
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '1', '-i', str(src), '-frames:v', '1', '-vf', "scale='min(720,iw)':-2", '-q:v', '4', str(pp)], check=False)
                if pp.exists():
                    poster = f'assets/media/{rel[:-4]}.jpg'
            w, h = 9, 16
            if shutil.which('ffprobe'):
                r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:stream_tags=rotate', '-of', 'json', str(src)], capture_output=True, text=True)
                try:
                    s = json.loads(r.stdout)['streams'][0]; w, h = s['width'], s['height']
                    if str(s.get('tags', {}).get('rotate', '0')) in ('90', '270'):
                        w, h = h, w
                except Exception:
                    pass
            res.append({'src': f'assets/media/{rel}', 'poster': poster, 'wide': w > h})
        return res


# ------------------------------------------------------------------ randare
class Site:
    def __init__(self, env, out, site_url):
        self.env, self.out = env, out
        self.s = load('site.json')
        self.locs = load('locatii.json')
        self.faq = load('faq.json')
        self.url = (site_url or self.s['productionUrl']).rstrip('/')
        self.media = Media(out, self.locs)
        self.pages = []
        self.year = dt.date.today().year

    # --- linkuri relative (site-ul merge și pe un subfolder, ex. GitHub Pages)
    def R(self, depth, target=''):
        return ('../' * depth) + target

    def abs(self, target=''):
        return f'{self.url}/{target}'

    def img(self, depth, m, sizes='100vw', cls='', eager=False):
        r = self.R(depth)
        srcset = ', '.join(r + part.strip() for part in m['srcset'].split(',')) if m['srcset'] else ''
        a = [f'src="{r}{m["src"]}"']
        if srcset:
            a.append(f'srcset="{srcset}" sizes="{sizes}"')
        a.append(f'width="{m["w"]}" height="{m["h"]}" alt="{E(m["alt"])}"')
        a.append('fetchpriority="high"' if eager else 'loading="lazy"')
        a.append('decoding="async"')
        if cls:
            a.append(f'class="{cls}"')
        return '<img ' + ' '.join(a) + '>'

    def loc_url(self, l):
        return l['slug'] + '/'

    # --- schelet pagină
    def page(self, path, title, desc, body, *, depth=None, jsonld=None, og_img=None, nav=None, robots=None, preload=None, cta=True):
        depth = path.count('/') if depth is None else depth
        r = self.R(depth)
        canon = self.abs(path)
        og = og_img or self.og_default
        preview = self.env != 'production'
        robots = robots or ('noindex, nofollow' if preview else 'index, follow, max-image-preview:large')
        ld = [self.ld_org()] + (jsonld or [])
        s = self.s
        head = f'''<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ro_RO">
<meta property="og:site_name" content="{E(s['name'])}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#14263A">
<link rel="icon" href="{r}favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="{r}assets/media/site/logo/logo-caminul-adina-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="{r}apple-touch-icon.png">
<link rel="manifest" href="{r}site.webmanifest">
<link rel="preload" href="{r}assets/fonts/bricolage-latin-wght.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{r}assets/fonts/atkinson-latin-400.woff2" as="font" type="font/woff2" crossorigin>
{preload or ''}
<link rel="stylesheet" href="{r}assets/css/site.css?v={self.css_v}">
<script type="application/ld+json">{json.dumps(ld if len(ld) > 1 else ld[0], ensure_ascii=False)}</script>
</head>
<body>
<a class="skip" href="#main">Sari la conținut</a>
'''
        band = '<div class="preview-band">Versiune de previzualizare a noului site Căminul Adina. Nu este încă publicată pe caminul-adina.ro.</div>\n' if preview else ''
        html_ = head + band + self.header(depth, nav) + f'<main id="main">\n{body}\n</main>\n' + (self.cta_band(depth) if cta else '') + self.footer(depth) + self.tail(depth)
        write(self.out, path + 'index.html' if path.endswith('/') or path == '' else path, html_)
        self.pages.append((path, robots))

    def header(self, depth, cur):
        r = self.R(depth)
        locs = ''.join(f'<a href="{r}{self.loc_url(l)}" style="--c:{l["color"]}"><i class="dot"></i><span>{E(l["name"])}<small>{E(l["area"])}{" · deschidere " + E(l["openingLabel"]) if l["status"] == "soon" else ""}</small></span></a>' for l in self.locs)
        def a(path, label):
            cur_ = ' aria-current="page"' if cur == path else ''
            return f'<a href="{r}{path}"{cur_}>{label}</a>'
        loc_cur = ' aria-current="page"' if cur == 'locatii' else ''
        return f'''<header class="site-head">
<div class="wrap head-row">
<a class="brand" href="{r}" aria-label="Căminul Adina – pagina principală">
<img src="{r}assets/media/site/logo/logo-caminul-adina-192.png" width="58" height="58" alt="">
<span><b>Căminul Adina</b><small>Cămine pentru vârstnici</small></span>
</a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav">Meniu</button>
<nav class="nav" id="nav" aria-label="Meniu principal">
<details class="drop"><summary{loc_cur}>Locații</summary><div class="drop-menu">{locs}</div></details>
{a("servicii/", "Servicii")}{a("preturi/", "Prețuri")}{a("galerie/", "Galerie")}{a("despre-noi/", "Despre noi")}{a("intrebari-frecvente/", "Întrebări")}{a("contact/", "Contact")}
</nav>
<a class="btn btn-gold head-cta" href="tel:{self.s["phoneE164"]}">{icon("phone")}{E(self.s["phone"])}</a>
</div>
</header>
'''

    def cta_band(self, depth):
        r = self.R(depth)
        return f'''<section class="cta-band" aria-label="Programare vizită">
<div class="wrap">
<h2>Veniți să vedeți căminul înainte să decideți.</h2>
<div class="btn-row"><a class="btn btn-ink" href="{r}contact/#programare">Programează o vizită</a><a class="btn btn-line" href="tel:{self.s["phoneE164"]}">{icon("phone")}Sună: {E(self.s["phone"])}</a></div>
</div>
</section>
'''

    def footer(self, depth):
        r, s = self.R(depth), self.s
        so = s['social']
        social = ''.join(f'<a href="{E(so[k])}" target="_blank" rel="noopener" aria-label="{lab}">{icon(ic)}</a>'
                         for k, lab, ic in [('facebook', 'Facebook', 'facebook'), ('messenger', 'Messenger', 'messenger'), ('whatsapp', 'WhatsApp', 'whatsapp'), ('instagram', 'Instagram', 'instagram'), ('tiktok', 'TikTok', 'tiktok'), ('youtube', 'YouTube', 'youtube')] if so.get(k))
        locs = ''.join(f'<li><a href="{r}{self.loc_url(l)}">Cămin de bătrâni {E(l["name"])}</a></li>' for l in self.locs)
        c = s['company']
        return f'''<footer class="site-foot">
<div class="wrap">
<div class="foot-grid">
<div>
<h3>Căminul Adina</h3>
<p>Cămine pentru vârstnici în Pipera, Otopeni, Snagov, Ploiești și, din ianuarie 2027, Poiana Brașov. Îngrijire medicală non-stop, cu respect și răbdare.</p>
<div class="social">{social}</div>
</div>
<div><h3>Locații</h3><ul>{locs}</ul></div>
<div><h3>Informații</h3><ul>
<li><a href="{r}servicii/">Servicii și îngrijire</a></li><li><a href="{r}preturi/">Prețuri</a></li><li><a href="{r}galerie/">Galerie foto și video</a></li><li><a href="{r}despre-noi/">Despre noi</a></li><li><a href="{r}intrebari-frecvente/">Întrebări frecvente</a></li><li><a href="{r}contact/">Contact</a></li>
</ul></div>
<div><h3>Contact</h3><ul>
<li><a href="tel:{s["phoneE164"]}">{E(s["phone"])}</a></li>
<li><a href="https://wa.me/{s["whatsapp"]}" target="_blank" rel="noopener">WhatsApp</a></li>
<li><a href="mailto:{E(s["email"])}">{E(s["email"])}</a></li>
<li>Telefon: {E(s["hours"])}</li><li>Îngrijire: non-stop, 24 din 24</li>
</ul></div>
</div>
<div class="foot-bottom">
<span>© {self.year} {E(s["legalName"])} · CUI {E(c["cui"])} · Reg. Com. {E(c["regCom"])}</span>
<span><a href="{r}politica-de-confidentialitate/">Politica de confidențialitate</a> · <a href="{r}politica-cookies/">Politica de cookie-uri</a> · <button class="linkbtn" type="button" data-consent="settings">Setări cookie</button> · <a href="https://anpc.ro/" target="_blank" rel="noopener">ANPC</a></span>
</div>
</div>
</footer>
'''

    def tail(self, depth):
        r, s = self.R(depth), self.s
        cfg = {'phone': s['phone'], 'email': s['email'], 'whatsapp': s['whatsapp'], 'formEndpoint': s['forms'].get('endpoint', ''), 'ga4': s['analytics'].get('ga4Id', '')}
        return f'''<div class="callbar"><a class="btn btn-ink" href="tel:{s["phoneE164"]}">{icon("phone")}Sună acum</a><a class="btn btn-gold" href="https://wa.me/{s["whatsapp"]}" target="_blank" rel="noopener">{icon("whatsapp")}WhatsApp</a></div>
<div class="consent" id="consent" role="region" aria-label="Preferințe cookie" hidden>
<h2>Cookie-uri și conținut extern</h2>
<p>Folosim doar ce e necesar ca site-ul să funcționeze. Videoclipurile de pe Facebook și hărțile Google se încarcă numai dacă sunteți de acord, pentru că acestea pot seta cookie-uri proprii. Detalii în <a href="{r}politica-cookies/">Politica de cookie-uri</a>.</p>
<div class="btn-row"><button class="btn btn-ink" type="button" data-consent="all">Accept tot</button><button class="btn btn-line" type="button" data-consent="none">Doar necesare</button><button class="btn btn-line" type="button" data-consent="settings">Setări</button></div>
</div>
<dialog class="cdlg" id="consent-dialog" aria-labelledby="cdlg-t">
<div class="in">
<h2 id="cdlg-t">Setări cookie</h2>
<p class="muted">Alegeți ce permiteți. Puteți schimba oricând din linkul „Setări cookie” din subsolul paginii.</p>
<div class="cat"><div><h3>Necesare</h3><p>Rețin alegerea dumneavoastră privind cookie-urile. Nu pot fi dezactivate.</p></div><label class="sw"><input type="checkbox" checked disabled aria-label="Necesare, mereu active"><span></span></label></div>
<div class="cat"><div><h3>Conținut extern</h3><p>Videoclipuri de pe Facebook și hărți Google. Facebook și Google pot seta cookie-uri proprii.</p></div><label class="sw"><input type="checkbox" id="c-ext" aria-label="Conținut extern"><span></span></label></div>
<div class="cat"><div><h3>Statistici</h3><p>Ne ajută să vedem ce pagini sunt citite. {"Momentan nu folosim niciun instrument de statistici." if not cfg["ga4"] else "Google Analytics 4, cu IP anonimizat."}</p></div><label class="sw"><input type="checkbox" id="c-stat" aria-label="Statistici"><span></span></label></div>
<div class="btn-row" style="margin-top:18px"><button class="btn btn-ink" type="button" data-consent="save">Salvează alegerea</button><button class="btn btn-line" type="button" data-consent="all">Accept tot</button></div>
</div>
</dialog>
<script>window.ADINA={json.dumps(cfg, ensure_ascii=False)};</script>
<script src="{r}assets/js/site.js?v={self.js_v}" defer></script>
</body>
</html>
'''

    # --- JSON-LD
    def ld_org(self):
        s = self.s
        return {'@context': 'https://schema.org', '@type': 'Organization', '@id': self.abs('#organizatie'), 'name': s['name'], 'legalName': s['legalName'],
                'url': self.abs(), 'logo': self.abs('assets/media/site/logo/logo-caminul-adina-512.png'), 'telephone': s['phoneE164'], 'email': s['email'],
                'taxID': s['company']['cui'], 'sameAs': [v for k, v in s['social'].items() if v and k in ('facebook', 'instagram', 'tiktok', 'youtube')],
                'department': [{'@id': self.abs(self.loc_url(l) + '#camin')} for l in self.locs]}

    def ld_loc(self, l, imgs):
        d = {'@context': 'https://schema.org', '@type': 'LocalBusiness', '@id': self.abs(self.loc_url(l) + '#camin'), 'name': l['fullName'],
             'description': l['seoDescription'], 'url': self.abs(self.loc_url(l)), 'telephone': self.s['phoneE164'], 'email': self.s['email'],
             'image': [self.abs(m['src']) for m in imgs[:6]] or [self.og_default], 'parentOrganization': {'@id': self.abs('#organizatie')},
             'address': {'@type': 'PostalAddress', 'addressLocality': l['locality'], 'addressRegion': l['region'], 'addressCountry': 'RO'},
             'hasMap': 'https://www.google.com/maps/search/?api=1&query=' + quote_plus(l['mapsQuery'])}
        if l['address'] != l['locality'] and l['status'] == 'open':
            d['address']['streetAddress'] = l['address']
        if l.get('priceFrom'):
            d['priceRange'] = f'de la {lei(l["priceFrom"])} / lună'
        return d

    def ld_crumbs(self, items):
        return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': self.abs(p)} for i, (n, p) in enumerate(items)]}

    def crumbs(self, depth, items):
        r = self.R(depth)
        li = ''.join(f'<li><a href="{r}{p}">{E(n)}</a></li>' if i < len(items) - 1 else f'<li aria-current="page">{E(n)}</li>' for i, (n, p) in enumerate(items))
        return f'<nav class="crumbs wrap" aria-label="Sunteți aici"><ol>{li}</ol></nav>'

    # --- componente
    def included(self):
        items = [
            ('Îngrijire medicală non-stop', 'Asistente medicale și infirmiere în fiecare tură, zi și noapte, plus asistent social.'),
            ('Consultații la cămin', 'Medicul de familie, medicul psihiatru și psihologul vin la rezident. Medicii specialiști vin lunar.'),
            ('Cinci mese pe zi', 'Trei mese principale și două gustări, gătite zilnic și adaptate dietei și afecțiunilor fiecăruia.'),
            ('Kinetoterapie', 'Două ședințe pe săptămână, câte 30 de minute, cu fiecare rezident. Recuperare și terapie ocupațională.'),
            ('Activități și socializare', 'Activități de comunicare și relaxare, sărbători împreună, consiliere spirituală, ieșiri în curte.'),
            ('Curățenie și îngrijire personală', 'Menaj zilnic, spălătorie, frizerie, barbierit, manichiură și pedichiură.'),
        ]
        return '<div class="incl">' + ''.join(f'<div><h3>{E(a)}</h3><p>{E(b)}</p></div>' for a, b in items) + '</div>'

    def doctors(self):
        d = ['Medic de familie', 'Geriatru', 'Neurolog', 'Psihiatru', 'Internist', 'Diabetolog', 'Reumatolog', 'Dermatolog', 'Psiholog', 'Kinetoterapeut']
        return '<ul class="doctors">' + ''.join(f'<li>{E(x)}</li>' for x in d) + '</ul>'

    def price_table(self, depth):
        r = self.R(depth)
        rows = ''
        for l in sorted(self.locs, key=lambda l: (l['priceFrom'] is None, l['priceFrom'] or 0)):
            amt = lei(l['priceFrom']) if l['priceFrom'] else 'la cerere'
            note = 'deschidere ' + l['openingLabel'] if l['status'] == 'soon' else E(l['facts'][0][1])
            rows += f'<tr style="--c:{l["color"]}"><td><a class="loc" href="{r}{self.loc_url(l)}"><i></i>{E(l["name"])}</a></td><td class="hide-s">{note}</td><td class="amt">{amt}</td></tr>'
        return f'<table class="price-table"><caption class="sr-only">Prețuri de pornire pe locații</caption><thead><tr><th scope="col">Locația</th><th scope="col" class="hide-s">Camere</th><th scope="col">De la, pe lună</th></tr></thead><tbody>{rows}</tbody></table>'

    def incl_excl(self):
        return '''<div class="two-col">
<div class="box"><h3>Inclus în preț</h3><ul><li>Cazare, menaj zilnic și spălătorie</li><li>Asistență medicală 24 din 24</li><li>Cinci mese pe zi, adaptate dietei</li><li>Consultații la cămin și kinetoterapie</li><li>Activități, frizerie, manichiură, pedichiură</li></ul></div>
<div class="box"><h3>Se plătește separat</h3><ul><li>Scutece și produse de incontinență</li><li>Medicamente</li><li>Alte servicii cerute în plus, discutate dinainte</li></ul></div>
</div>'''

    def faq_html(self, items):
        return '<div class="faq">' + ''.join(f'<details{" open" if i == 0 else ""}><summary>{E(f["q"])}</summary><p>{E(f["a"])}</p></details>' for i, f in enumerate(items)) + '</div>'

    def reel(self, url, label, color, depth=0, poster=None):
        src = 'https://www.facebook.com/plugins/video.php?href=' + quote(url, safe='') + '&show_text=false&width=320'
        pst = f'<img class="ext-poster" src="{self.R(depth)}{(poster["srcset"].split(",")[0].split()[0] if poster["srcset"] else poster["src"])}" alt="" loading="lazy" decoding="async">' if poster and not poster['src'].endswith('.svg') else ''
        return f'''<div class="vid" style="--c:{color}"><div class="ext" data-embed="{E(src)}" data-title="{E(label)}">{pst}
<span class="lbl">{E(label)}</span>
<p>Videoclip găzduit pe Facebook. Dacă îl porniți, Facebook poate seta cookie-uri.</p>
<div class="btn-row"><button class="btn btn-gold" type="button" data-load-once>Pornește videoclipul</button><button class="btn" type="button" data-load-always>Permite mereu</button></div>
<a href="{E(url)}" target="_blank" rel="noopener" style="font-size:15px;color:#fff">Vezi pe Facebook</a>
</div></div>'''

    def map_embed(self, l):
        src = 'https://www.google.com/maps?q=' + quote_plus(l['mapsQuery']) + '&output=embed'
        link = 'https://www.google.com/maps/search/?api=1&query=' + quote_plus(l['mapsQuery'])
        return f'''<div class="map"><div class="ext" data-embed="{E(src)}" data-title="Hartă {E(l['fullName'])}">
<span class="lbl">Hartă: {E(l['address'])}</span>
<p>Harta e oferită de Google. Dacă o încărcați, Google poate seta cookie-uri.</p>
<div class="btn-row"><button class="btn" type="button" data-load-once>Încarcă harta</button><a class="btn" href="{E(link)}" target="_blank" rel="noopener">{icon("pin")}Deschide în Google Maps</a></div>
</div></div>'''

    def gallery_html(self, depth, gid, imgs, visible=12):
        if not imgs:
            return '<p class="muted">Fotografiile vor fi adăugate în curând.</p>'
        btns = ''
        for i, m in enumerate(imgs):
            hid = ' class="more-hidden"' if i >= visible else ''
            btns += f'<button type="button" data-full="{self.R(depth)}{m["full"]}"{hid} aria-label="Mărește: {E(m["alt"])}">{self.img(depth, m, "(max-width:640px) 100vw, (max-width:1100px) 50vw, 400px")}</button>'
        more = f'<button class="btn btn-line g-more" type="button" data-expand="{gid}">Vezi toate cele {len(imgs)} fotografii</button>' if len(imgs) > visible else ''
        return f'<div class="gallery" id="{gid}">{btns}</div>{more}'

    def videos_html(self, depth, vids, reels, l):
        out = ''
        for v in vids:
            r = self.R(depth)
            poster = f' poster="{r}{v["poster"]}"' if v['poster'] else ''
            out += f'<div class="vid{" wide" if v["wide"] else ""}"><video controls preload="none" playsinline{poster}><source src="{r}{v["src"]}" type="video/mp4">Browserul nu poate reda videoclipul.</video></div>'
        g = self.galleries.get(l['key']) or []
        for i, u in enumerate(reels, 1):
            out += self.reel(u, f'{l["fullName"]} – video {i}', l['color'], depth, g[(i * 3) % len(g)] if g else None)
        return f'<div class="videos">{out}</div>' if out else ''

    def loc_cards(self, depth, locs, eager=False):
        r = self.R(depth)
        out = ''
        for l in locs:
            m = self.cover(l)
            price = f'<span class="price">de la <b>{lei(l["priceFrom"])}</b>/lună</span>' if l['priceFrom'] else '<span class="price">Rezervări deschise</span>'
            pill = f'<span class="pill">Din {E(l["openingLabel"])}</span>' if l['status'] == 'soon' else ''
            out += f'''<a class="loc-card" href="{r}{self.loc_url(l)}" style="--c:{l["color"]}">{pill}
<div class="ph">{self.img(depth, m, "(max-width:640px) 50vw, (max-width:1100px) 33vw, 240px")}</div>
<div class="bd"><h3>{E(l["name"])}</h3><span class="area">{E(l["area"])}</span><span>{E(l["tagline"])}</span>{price}</div></a>'''
        return out

    def cover(self, l):
        rel = l.get('cover')
        if rel:
            return self.media.image(rel, self.media.alts.get(rel) or l['fullName'], l['key'])
        g = self.galleries.get(l['key']) or []
        return g[0] if g else self.media.placeholder(l['key'], l['fullName'])

    # ------------------------------------------------------------------ pagini
    def build(self):
        self.css_v = hashlib.md5((SRC / 'assets/css/site.css').read_bytes()).hexdigest()[:8]
        self.js_v = hashlib.md5((SRC / 'assets/js/site.js').read_bytes()).hexdigest()[:8]
        shutil.copytree(SRC / 'assets', self.out / 'assets', dirs_exist_ok=True)
        self.logo()
        self.hero = self.media.image('site/header/header-cuplu-seniori.webp', 'Un cuplu de vârstnici zâmbitori, îmbrățișați')
        og = MEDIA / 'site/header/header-cuplu-seniori-og.jpg'
        if og.exists():
            (self.out / 'assets/media/site/header').mkdir(parents=True, exist_ok=True)
            shutil.copyfile(og, self.out / 'assets/media/site/header/header-cuplu-seniori-og.jpg')
            self.og_default = self.abs('assets/media/site/header/header-cuplu-seniori-og.jpg')
        else:
            self.og_default = self.abs(self.hero['src'])
        self.galleries = {l['key']: self.media.gallery(l['key']) for l in self.locs}
        self.vids = {l['key']: self.media.videos(l['key']) for l in self.locs}
        self.home(); [self.location(l) for l in self.locs]
        self.services(); self.prices(); self.about(); self.galleryp(); self.faqp(); self.contact()
        self.privacy(); self.cookies(); self.notfound(); self.redirects(); self.seo_files()
        return self

    def logo(self):
        d = self.out / 'assets/media/site/logo'
        d.mkdir(parents=True, exist_ok=True)
        srcs = {n: MEDIA / 'site/logo' / n for n in ('logo-caminul-adina-512.png', 'logo-caminul-adina-192.png', 'logo-caminul-adina-512.webp')}
        for n, p in srcs.items():
            if p.exists():
                shutil.copyfile(p, d / n)
            else:
                self.media.missing.append(f'site/logo/{n}')
        if Image and srcs['logo-caminul-adina-512.png'].exists():
            im = Image.open(srcs['logo-caminul-adina-512.png']).convert('RGBA')
            im.resize((32, 32), Image.LANCZOS).save(self.out / 'favicon-32.png')
            bg = Image.new('RGBA', (180, 180), (255, 255, 255, 255)); bg.alpha_composite(im.resize((164, 164), Image.LANCZOS), (8, 8))
            bg.convert('RGB').save(self.out / 'apple-touch-icon.png')
            shutil.copyfile(self.out / 'favicon-32.png', self.out / 'favicon.ico')

    def home(self):
        s, d = self.s, 0
        news_l = next((l for l in self.locs if l['status'] == 'soon'), None)
        news = f'<a class="news" href="{self.loc_url(news_l)}"><b>Nou</b>Poiana Brașov: deschidere pe {E(news_l["openingLabel"])}</a>' if news_l else ''
        general_reels = ['https://www.facebook.com/reel/1082612637977344/', 'https://www.facebook.com/reel/1627799399054419/', 'https://www.facebook.com/reel/1796014958438906/', 'https://www.facebook.com/reel/1240042123313651/']
        reel_labels = ['O zi la Căminul Adina', 'Mesele de zi cu zi', 'Activități recreative', 'Timp pentru mișcare']
        posters = [self.media.image(r, '', 'general') for r in ('site/otopeni/otopeni-08.webp', 'site/pipera/pipera-22.webp', 'site/pipera/pipera-19.webp', 'site/pipera/pipera-16.webp')]
        reels = ''.join(self.reel(u, t, '#2C62A3', 0, p) for u, t, p in zip(general_reels, reel_labels, posters))
        med_img = self.media.image(self.s.get('images', {}).get('home-medical', ''), 'Sala de mese a unui cămin Adina', 'general')
        body = f'''<section class="hero">
<div class="wrap hero-grid">
<div>
{news}
<h1>Cămine de bătrâni în care părinții se simt acasă</h1>
<p class="lead">Cinci locații – Pipera, Otopeni, Snagov, Ploiești și, din ianuarie 2027, Poiana Brașov – cu asistență medicală non-stop, mese gătite în fiecare zi și curți mari în care se poate ieși la soare.</p>
<div class="btn-row" data-hero-cta><a class="btn btn-ink" href="contact/#programare">Programează o vizită</a><a class="btn btn-line" href="tel:{s["phoneE164"]}">{icon("phone")}Sună: {E(s["phone"])}</a></div>
<ul class="trust"><li>{icon("check")}Asistente și infirmiere 24 din 24</li><li>{icon("check")}Medici specialiști la cămin</li><li>{icon("check")}Prețuri de la 5.500 lei/lună</li><li>{icon("check")}Peste {s["experienceYears"]} ani de experiență</li></ul>
</div>
<div class="hero-photo">{self.img(d, self.hero, "(max-width:960px) 92vw, 520px", eager=True)}
<div class="hero-note"><b>Îngrijire 24 din 24</b>Asistente și infirmiere în fiecare tură, la toate locațiile.</div></div>
</div>
</section>

<section id="locatii" aria-labelledby="t-loc">
<div class="wrap">
<div class="sec-head"><h2 id="t-loc">Alegeți locația potrivită</h2><p class="lead">Toate căminele au aceleași servicii medicale și același standard de îngrijire. Diferă curtea, camerele și drumul până la voi.</p></div>
<div class="loc-grid">{self.loc_cards(d, self.locs)}</div>
</div>
</section>

<section class="sec-ink" aria-labelledby="t-incl">
<div class="wrap">
<div class="sec-head"><h2 id="t-incl">Ce primește părintele vostru în fiecare zi</h2><p class="lead">Totul de mai jos e inclus în prețul lunar. Separat se plătesc doar scutecele și medicamentele.</p></div>
{self.included()}
</div>
</section>

<section aria-labelledby="t-med">
<div class="wrap split">
<div class="arch-img">{self.img(d, med_img, "(max-width:960px) 92vw, 560px")}</div>
<div>
<h2 id="t-med">Medicii vin la cămin, nu invers</h2>
<p class="lead" style="margin:18px 0">Echipa de medici colaboratori consultă lunar fiecare rezident. Medicii emit rețetele compensate, iar medicamentele sunt aduse la cămin de farmacia unei clinici partenere, așa că familia nu mai aleargă după ele.</p>
<p>Avem experiență în îngrijirea persoanelor cu demență și boala Alzheimer și a celor care au nevoie de ajutor permanent.</p>
{self.doctors()}
<p style="margin-top:24px"><a class="btn btn-line" href="servicii/">Toate serviciile</a></p>
</div>
</div>
</section>

<section class="sec-mist" aria-labelledby="t-vid">
<div class="wrap">
<div class="sec-head"><h2 id="t-vid">Din viața de la cămin</h2><p class="lead">Câteva clipuri de pe pagina noastră de Facebook, cu mesele, activitățile și zilele obișnuite ale rezidenților.</p></div>
<div class="videos">{reels}</div>
<p style="margin-top:24px"><a class="btn btn-line" href="{E(s["social"]["facebook"])}" target="_blank" rel="noopener">{icon("facebook")}Urmăriți-ne pe Facebook</a></p>
</div>
</section>

<section aria-labelledby="t-pret">
<div class="wrap">
<div class="sec-head"><h2 id="t-pret">Prețuri clare, afișate public</h2><p class="lead">Prețul exact depinde de tipul camerei și de nevoile de îngrijire. Vi-l confirmăm după o discuție cu familia.</p></div>
{self.price_table(d)}
{self.incl_excl()}
</div>
</section>

<section class="sec-mist" aria-labelledby="t-faq">
<div class="wrap">
<div class="sec-head"><h2 id="t-faq">Întrebări pe care ni le pun familiile</h2><p class="lead"><a href="intrebari-frecvente/">Vedeți toate întrebările</a></p></div>
{self.faq_html(self.faq[:4])}
</div>
</section>'''
        ld = [{'@context': 'https://schema.org', '@type': 'WebSite', '@id': self.abs('#site'), 'url': self.abs(), 'name': s['name'], 'inLanguage': 'ro-RO', 'publisher': {'@id': self.abs('#organizatie')}},
              {'@context': 'https://schema.org', '@type': 'ItemList', 'name': 'Locațiile Căminul Adina', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': self.abs(self.loc_url(l)), 'name': l['fullName']} for i, l in enumerate(self.locs)]}]
        pre = f'<link rel="preload" as="image" href="{self.hero["src"]}" imagesrcset="{self.hero["srcset"]}" imagesizes="(max-width:960px) 92vw, 520px">' if self.hero['srcset'] else ''
        self.page('', 'Cămin de bătrâni Pipera, Otopeni, Snagov, Ploiești, Poiana Brașov – Căminul Adina',
                  'Căminul Adina: cămine de bătrâni în Pipera, Otopeni, Snagov, Ploiești și Poiana Brașov. Asistență medicală non-stop, 5 mese pe zi, medici la cămin. De la 5.500 lei/lună.',
                  body, jsonld=ld, nav='', preload=pre)

    def location(self, l):
        s, d = self.s, 1
        imgs = self.galleries[l['key']]
        cover = self.cover(l)
        others = [o for o in self.locs if o['key'] != l['key']]
        link = 'https://www.google.com/maps/search/?api=1&query=' + quote_plus(l['mapsQuery'])
        if l['status'] == 'soon':
            price = f'<div class="soon-box"><b>Deschidere: {E(l["openingLabel"])}</b><br>Rezervările au început. Prețul și disponibilitatea le aflați la {E(s["phone"])}.</div>'
            cta1 = 'Rezervă un loc'
        else:
            price = f'<p class="price-line">de la <b>{lei(l["priceFrom"])}</b> pe lună, cu serviciile incluse</p>'
            cta1 = 'Programează o vizită'
        facts = ''.join(f'<dt>{E(k)}</dt><dd>{E(v)}</dd>' for k, v in l['facts'])
        hl = ''.join(f'<li>{E(h)}</li>' for h in l['highlights'])
        intro = ''.join(f'<p{" class=lead" if i == 0 else ""}>{E(p)}</p>' for i, p in enumerate(l['intro']))
        vids = self.videos_html(d, self.vids[l['key']], l['reels'], l)
        vid_sec = f'''<section class="sec-mist" aria-labelledby="t-v"><div class="wrap"><div class="sec-head"><h2 id="t-v">Video din {E(l["name"])}</h2></div>{vids}</div></section>''' if vids else ''
        name = l['name']
        loc_facts_title = 'Ce găsiți la ' + name if l['status'] == 'open' else 'Ce va avea locația'
        body = f'''{self.crumbs(d, [("Acasă", ""), ("Locații", "#locatii"), (f"Cămin de bătrâni {name}", self.loc_url(l))])}
<section class="loc-hero" style="--c:{l["color"]}">
<div class="wrap hero-grid">
<div>
<span class="pill">{E(l["area"])}</span>
<h1>Cămin de bătrâni {E(name)}</h1>
<p class="lead" style="margin:0 0 18px">{E(l["tagline"])}</p>
<p class="addr-line">{icon("pin")}<a href="{E(link)}" target="_blank" rel="noopener">{E(l["address"])}{", " + E(l["locality"]) if l["address"] != l["locality"] and l["locality"] not in l["address"] else ""}</a></p>
{price}
<div class="btn-row" data-hero-cta><a class="btn btn-c" href="../contact/?locatia={quote(name)}#programare">{cta1}</a><a class="btn btn-line" href="tel:{s["phoneE164"]}">{icon("phone")}{E(s["phone"])}</a><a class="btn btn-line" href="https://wa.me/{s["whatsapp"]}?text={quote("Bună ziua, aș dori informații despre Căminul Adina " + name + ".")}" target="_blank" rel="noopener">{icon("whatsapp")}WhatsApp</a></div>
</div>
<div class="hero-photo">{self.img(d, cover, "(max-width:960px) 92vw, 520px", eager=True)}</div>
</div>
</section>

<section aria-labelledby="t-d" style="--c:{l["color"]}">
<div class="wrap split top">
<div><h2 id="t-d" style="margin-bottom:20px">Despre căminul din {E(name)}</h2>{intro}<ul class="hl">{hl}</ul></div>
<div><h3 style="margin-bottom:14px">{loc_facts_title}</h3><dl class="facts">{facts}</dl><p class="muted" style="margin-top:14px">{E(l["nearby"])}</p></div>
</div>
</section>

<section aria-labelledby="t-g" style="padding-top:0">
<div class="wrap"><div class="sec-head"><h2 id="t-g">Fotografii din {E(name)}</h2>{"<p class=lead>" + str(len(imgs)) + " fotografii din cămin, din camere, din curte și din spațiile comune.</p>" if imgs else ""}</div>
{self.gallery_html(d, "g-" + l["key"], imgs)}
</div>
</section>
{vid_sec}
<section class="sec-ink" aria-labelledby="t-i">
<div class="wrap"><div class="sec-head"><h2 id="t-i">Inclus în prețul lunar</h2><p class="lead">La fel la toate locațiile Căminul Adina. Separat se plătesc doar scutecele și medicamentele.</p></div>{self.included()}</div>
</section>

<section aria-labelledby="t-m">
<div class="wrap split">
<div><h2 id="t-m">Cum ajungeți</h2><p class="lead" style="margin:18px 0">{E(l["address"])}, {E(l["locality"])}, {E(l["region"])}.</p><p>{E(l["nearby"])}</p><p><a class="btn btn-line" href="{E(link)}" target="_blank" rel="noopener">{icon("pin")}Deschide în Google Maps</a></p></div>
{self.map_embed(l)}
</div>
</section>

<section class="sec-mist" aria-labelledby="t-o">
<div class="wrap"><div class="sec-head"><h2 id="t-o">Celelalte locații Căminul Adina</h2></div><div class="loc-grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">{self.loc_cards(d, others)}</div></div>
</section>'''
        ld = [self.ld_loc(l, imgs), self.ld_crumbs([('Acasă', ''), (f'Cămin de bătrâni {name}', self.loc_url(l))])]
        og = self.abs(cover['src']) if not cover['src'].endswith('.svg') else None
        self.page(self.loc_url(l), l['seoTitle'], l['seoDescription'], body, jsonld=ld, og_img=og, nav='locatii')

    def simple(self, path, h1, lead, inner, title, desc, crumb, jsonld=None, cta=True):
        d = path.count('/')
        body = f'''{self.crumbs(d, [("Acasă", ""), (crumb, path)])}
<div class="page-head" style="margin-top:12px"><div class="wrap"><h1>{E(h1)}</h1><p class="lead">{lead}</p></div></div>
{inner}'''
        self.page(path, title, desc, body, jsonld=(jsonld or []) + [self.ld_crumbs([('Acasă', ''), (crumb, path)])], nav=path, cta=cta)

    def services(self):
        d = 1
        img = self.media.image(self.s.get('images', {}).get('services', ''), 'Living cu canapea verde în căminul din Pipera', 'pipera')
        inner = f'''<section><div class="wrap">
<div class="sec-head"><h2>Inclus în prețul lunar</h2></div>{self.included()}
</div></section>
<section class="sec-mist"><div class="wrap split">
<div><h2>Îngrijire medicală</h2><p class="lead" style="margin:18px 0">Asistentele medicale și infirmierele sunt prezente 24 din 24 la toate locațiile. Fiecare cămin are cabinet medical.</p>
<p>Medicul de familie, medicul psihiatru și psihologul consultă rezidenții la cămin. Medicii specialiști colaboratori vin lunar și consultă fiecare rezident. Medicii emit rețetele compensate, iar medicamentele sunt aduse la cămin de farmacia unei clinici partenere.</p>
<p>Kinetoterapeutul lucrează cu fiecare rezident de două ori pe săptămână, câte 30 de minute.</p>{self.doctors()}</div>
<div class="arch-img">{self.img(d, img, "(max-width:960px) 92vw, 560px")}</div>
</div></section>
<section><div class="wrap split top">
<div><h2>Demență și boala Alzheimer</h2><p class="lead" style="margin:18px 0">Mulți dintre rezidenții noștri trăiesc cu demență sau boala Alzheimer.</p>
<p>Echipa știe cum să vorbească cu ei, cum să-i liniștească și cum să păstreze o rutină care îi ajută să se simtă în siguranță. Consilierea și sprijinul emoțional pornesc de la amintirile bune ale fiecăruia, pentru că acestea îi liniștesc și le dau încredere.</p></div>
<div class="box"><h3>Lista completă a serviciilor</h3><ul>
<li>Cazare pe perioadă scurtă sau lungă</li><li>Menaj zilnic și igienă adecvată</li><li>Asistență medicală non-stop (asistente medicale și infirmiere)</li><li>Asistență socială</li><li>Consultații: medic de familie, psihiatru, psiholog</li><li>Alimentație variată, adaptată dietei și afecțiunilor (3 mese și 2 gustări)</li><li>Recuperare medicală și fizio-kinetoterapie</li><li>Terapie ocupațională</li><li>Activități de comunicare, relaxare și socializare</li><li>Activități de informare și consiliere</li><li>Activități festive și consiliere spirituală</li><li>Frizerie, barbierit, manichiură, pedichiură, cosmetică</li><li>Spălătorie pentru haine și lenjerie</li></ul>
<p class="muted" style="margin:14px 0 0">Scutecele și medicamentele se plătesc separat.</p></div>
</div></section>'''
        self.simple('servicii/', 'Servicii și îngrijire', 'Aceleași servicii la toate cele cinci locații: îngrijire medicală non-stop, consultații la cămin, cinci mese pe zi, kinetoterapie și activități zilnice.',
                    inner, 'Servicii și îngrijire pentru vârstnici – Căminul Adina',
                    'Îngrijire medicală non-stop, consultații la cămin, kinetoterapie, 5 mese pe zi și activități. Experiență cu demența și boala Alzheimer. Căminul Adina.', 'Servicii')

    def prices(self):
        inner = f'''<section><div class="wrap">{self.price_table(1)}{self.incl_excl()}
<div class="prose" style="margin-top:40px"><h2>Cum se stabilește prețul</h2>
<p>Prețurile de mai sus sunt prețuri de pornire. Prețul exact depinde de locație, de tipul camerei (single sau dublă, acolo unde există) și de nevoile de îngrijire ale rezidentului.</p>
<p>Vă rugăm să ne sunați la <a href="tel:{self.s["phoneE164"]}">{E(self.s["phone"])}</a> sau să programați o vizită. Vă spunem prețul exact după ce aflăm situația părintelui vostru.</p></div>
</div></section>'''
        self.simple('preturi/', 'Prețuri', 'Prețurile de pornire pe fiecare locație, cu ce e inclus și ce se plătește separat.', inner,
                    'Prețuri cămin de bătrâni – de la 5.500 lei/lună | Căminul Adina',
                    'Prețuri Căminul Adina: Ploiești de la 5.500 lei, Pipera și Otopeni de la 6.500 lei, Snagov de la 7.000 lei pe lună. Cazare, masă și îngrijire medicală incluse.', 'Prețuri')

    def about(self):
        c, s = self.s['company'], self.s
        img = self.media.image(self.s.get('images', {}).get('about', ''), 'Foișorul din grădina căminului din Pipera', 'pipera')
        inner = f'''<section><div class="wrap split top">
<div class="prose">
<h2 style="margin-top:0">Cine suntem</h2>
<p>Căminul Adina îngrijește vârstnici de peste {s["experienceYears"]} ani. Am început cu o singură casă și am crescut, an după an, până la cinci locații: Pipera, Otopeni, Snagov, Ploiești și, din ianuarie 2027, Poiana Brașov.</p>
<p>Coordonatoarea căminelor, {E(s["manager"])}, are o experiență îndelungată în deschiderea și conducerea centrelor pentru vârstnici. Știe din practică ce înseamnă o zi bună pentru un vârstnic și ce o strică.</p>
<h2>Ce ne propunem</h2>
<p>Vrem ca fiecare rezident să trăiască o viață liniștită și demnă, iar familia să știe că părintele ei e în siguranță. De aceea punem pe primul loc lucrurile simple: îngrijire medicală permanentă, mâncare bună, curățenie și oameni care au timp să asculte.</p>
<ul><li>Oferim servicii sociale primare și specializate, în condițiile legii.</li><li>Formăm continuu personalul, prin cursuri și programe de specialitate.</li><li>Informăm familiile despre drepturile și îngrijirea persoanelor vârstnice.</li><li>Respectăm drepturile fiecărui rezident și combatem orice formă de discriminare.</li></ul>
<h2>Date de identificare</h2>
<p>{E(s["legalName"])}, CUI {E(c["cui"])}, Reg. Com. {E(c["regCom"])}, firmă {E(c["vat"])}. Punct de lucru: {E(c["registeredPoint"])}.</p>
</div>
<div class="arch-img">{self.img(1, img, "(max-width:960px) 92vw, 560px")}</div>
</div></section>'''
        self.simple('despre-noi/', 'Despre noi', f'Peste {s["experienceYears"]} ani de îngrijire pentru vârstnici, în cinci locații.', inner,
                    'Despre noi – Căminul Adina, cămine de bătrâni din 2009 încoace'.replace(' din 2009 încoace', ''),
                    f'Căminul Adina îngrijește vârstnici de peste {s["experienceYears"]} ani, în Pipera, Otopeni, Snagov, Ploiești și Poiana Brașov. Aflați cine suntem și ce ne propunem.', 'Despre noi')

    def galleryp(self):
        secs = ''
        for l in self.locs:
            imgs = self.galleries[l['key']]
            if not imgs:
                continue
            secs += f'''<section aria-labelledby="g-{l["key"]}" style="--c:{l["color"]};padding:56px 0 0">
<div class="wrap"><div class="sec-head"><h2 id="g-{l["key"]}">{E(l["fullName"])}</h2><p class="lead"><a href="../{self.loc_url(l)}">Pagina locației {E(l["name"])}</a></p></div>
{self.gallery_html(1, "gp-" + l["key"], imgs, visible=9)}</div></section>'''
        self.simple('galerie/', 'Galerie foto și video', 'Fotografii din toate locațiile Căminul Adina: camere, spații comune, curți și grădini.', secs + '<div style="height:88px"></div>',
                    'Galerie foto – Căminul Adina Pipera, Otopeni, Snagov, Ploiești, Poiana Brașov',
                    'Fotografii din căminele Adina: camere, livinguri, curți și grădini în Pipera, Otopeni, Snagov, Ploiești și Poiana Brașov.', 'Galerie')

    def faqp(self):
        ld = [{'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': f['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}} for f in self.faq]}]
        inner = f'<section><div class="wrap">{self.faq_html(self.faq)}</div></section>'
        self.simple('intrebari-frecvente/', 'Întrebări frecvente', f'Nu găsiți răspunsul? Sunați-ne la {E(self.s["phone"])}, {E(self.s["hours"])}.', inner,
                    'Întrebări frecvente despre căminul de bătrâni – Căminul Adina',
                    'Ce include prețul, ce se plătește separat, vizite, îngrijire medicală, demență și urgențe: răspunsuri la întrebările familiilor despre Căminul Adina.', 'Întrebări frecvente', jsonld=ld)

    def contact(self):
        s = self.s
        opts = ''.join(f'<option value="{E(l["name"])}">{E(l["name"])}{" (deschidere " + E(l["openingLabel"]) + ")" if l["status"] == "soon" else ""}</option>' for l in self.locs)
        addrs = ''.join(f'<li><a href="https://www.google.com/maps/search/?api=1&query={quote_plus(l["mapsQuery"])}" target="_blank" rel="noopener" style="--c:{l["color"]}">{icon("pin")}<span>{E(l["fullName"])}<small>{E(l["address"])}{", " + E(l["locality"]) if l["locality"] not in l["address"] else ""}</small></span></a></li>' for l in self.locs)
        inner = f'''<section><div class="wrap contact-grid">
<div>
<h2>Vorbiți cu noi</h2>
<p class="lead" style="margin-top:14px">Telefon și WhatsApp {E(s["hours"])}, {E(s["hoursNote"])}. Ne puteți scrie oricând și vă răspundem în programul de lucru.</p>
<ul class="reach-list">
<li><a href="tel:{s["phoneE164"]}">{icon("phone")}<span>{E(s["phone"])}<small>Sunați-ne</small></span></a></li>
<li><a href="https://wa.me/{s["whatsapp"]}" target="_blank" rel="noopener">{icon("whatsapp")}<span>WhatsApp<small>{E(s["phone"])}</small></span></a></li>
<li><a href="{E(s["social"]["messenger"])}" target="_blank" rel="noopener">{icon("messenger")}<span>Messenger<small>Pagina Căminul de bătrâni ADINA</small></span></a></li>
<li><a href="mailto:{E(s["email"])}">{icon("mail")}<span>{E(s["email"])}<small>E-mail</small></span></a></li>
</ul>
<h3 style="margin:36px 0 4px">Adresele căminelor</h3>
<ul class="reach-list">{addrs}</ul>
</div>
<form class="cf" id="visit-form" novalidate aria-labelledby="programare">
<h2 id="programare">Programează o vizită</h2>
<p class="muted">Completați câteva rânduri și vă sunăm noi.</p>
<div class="grid">
<label>Numele dumneavoastră<input name="nume" autocomplete="name" required aria-describedby="e-nume"><span class="err" id="e-nume" hidden></span></label>
<label>Telefon<input name="telefon" type="tel" inputmode="tel" autocomplete="tel" required aria-describedby="e-tel"><span class="err" id="e-tel" hidden></span></label>
<label>E-mail <span class="opt">(opțional)</span><input name="email" type="email" autocomplete="email"></label>
<label>Locația dorită<select name="locatia"><option value="Nu știu încă">Nu știu încă</option>{opts}</select></label>
<label class="full">Pentru cine căutați?<select name="pentru"><option>Mama</option><option>Tata</option><option>Ambii părinți</option><option>Altă rudă</option><option>Pentru mine</option></select></label>
<label class="full">Mesaj <span class="opt">(opțional)</span><textarea name="mesaj" placeholder="De exemplu: când ați vrea să veniți în vizită"></textarea></label>
<label class="hp" aria-hidden="true">Nu completați<input name="website" tabindex="-1" autocomplete="off"></label>
<label class="chk full"><input type="checkbox" name="acord" required aria-describedby="e-acord"><span>Sunt de acord ca datele mele să fie folosite pentru a fi contactat(ă) în legătură cu această cerere, conform <a href="../politica-de-confidentialitate/">Politicii de confidențialitate</a>.<span class="err" id="e-acord" hidden></span></span></label>
</div>
<p class="note">Vă rugăm să nu scrieți aici detalii medicale. Le discutăm la telefon sau la vizită.</p>
<button class="btn btn-ink" type="submit" style="margin-top:8px">Trimite cererea de vizită</button>
<div class="form-msg" role="status" aria-live="polite"></div>
</form>
</div></section>'''
        ld = [{'@context': 'https://schema.org', '@type': 'ContactPage', 'url': self.abs('contact/'), 'about': {'@id': self.abs('#organizatie')}}]
        self.simple('contact/', 'Contact', 'Telefon, WhatsApp, e-mail și adresele celor cinci cămine. Programați o vizită din formularul de mai jos.', inner,
                    'Contact – Căminul Adina, 0756 604 755', f'Contactați Căminul Adina la {s["phone"]} (telefon și WhatsApp) sau {s["email"]}. Programați o vizită la una dintre cele cinci locații.', 'Contact', jsonld=ld, cta=False)

    def privacy(self):
        s, c = self.s, self.s['company']
        today = dt.date.today().strftime('%d.%m.%Y')
        inner = f'''<section><div class="wrap prose">
<p><b>Ultima actualizare:</b> {today}</p>
<h2>1. Cine prelucrează datele</h2>
<p>Operatorul datelor este {E(s["legalName"])}, CUI {E(c["cui"])}, Reg. Com. {E(c["regCom"])}, cu punct de lucru în {E(c["registeredPoint"])} („Căminul Adina”, „noi”). Ne puteți contacta pentru orice întrebare legată de datele personale la <a href="mailto:{E(s["email"])}">{E(s["email"])}</a> sau la {E(s["phone"])}.</p>
<h2>2. Ce date colectăm prin acest site</h2>
<ul>
<li><b>Formularul „Programează o vizită”:</b> numele, numărul de telefon, adresa de e-mail (opțional), locația dorită, pentru cine căutați și mesajul, dacă îl scrieți.</li>
<li><b>Când ne contactați telefonic, pe WhatsApp, Messenger sau e-mail:</b> datele pe care alegeți să ni le transmiteți.</li>
<li><b>Preferințele de cookie:</b> alegerea dumneavoastră, păstrată în browser (vezi <a href="../politica-cookies/">Politica de cookie-uri</a>).</li>
</ul>
<p>Vă rugăm să nu ne transmiteți prin formular informații despre starea de sănătate. Dacă alegeți totuși să o faceți, le folosim doar pentru a vă răspunde la cerere, pe baza consimțământului dumneavoastră explicit.</p>
<h2>3. De ce folosim datele și pe ce temei</h2>
<table><thead><tr><th>Scop</th><th>Temei legal (GDPR)</th></tr></thead><tbody>
<tr><td>Să vă răspundem și să programăm vizita</td><td>Demersuri înainte de încheierea unui contract, la cererea dumneavoastră (art. 6 alin. 1 lit. b) și consimțământul dumneavoastră (art. 6 alin. 1 lit. a)</td></tr>
<tr><td>Să păstrăm evidența cererilor</td><td>Interesul nostru legitim de a gestiona solicitările (art. 6 alin. 1 lit. f)</td></tr>
<tr><td>Date de sănătate transmise voluntar</td><td>Consimțământul explicit (art. 9 alin. 2 lit. a)</td></tr>
<tr><td>Statistici despre folosirea site-ului, doar dacă le activăm și sunteți de acord</td><td>Consimțământul dumneavoastră (art. 6 alin. 1 lit. a)</td></tr>
</tbody></table>
<h2>4. Cât timp păstrăm datele</h2>
<p>Datele din cererile care nu se finalizează cu un contract le păstrăm cel mult 12 luni de la ultimul contact, apoi le ștergem. Datele rezidenților și ale aparținătorilor, după încheierea contractului, sunt prelucrate separat, conform contractului și legislației privind serviciile sociale.</p>
<h2>5. Cui transmitem datele</h2>
<p>Nu vindem și nu închiriem datele. Le pot accesa doar furnizorii care ne ajută tehnic: furnizorul de găzduire a site-ului, furnizorul de e-mail și, dacă alegeți să ne scrieți acolo, WhatsApp sau Messenger (Meta). Unii dintre acești furnizori pot transfera date în afara Spațiului Economic European, cu garanțiile prevăzute de GDPR (de exemplu, clauze contractuale standard).</p>
<h2>6. Drepturile dumneavoastră</h2>
<p>Aveți dreptul de acces, de rectificare, de ștergere, de restricționare a prelucrării, de portabilitate și de opoziție, precum și dreptul de a vă retrage oricând consimțământul, fără a afecta prelucrarea făcută înainte. Pentru a vă exercita drepturile, scrieți-ne la <a href="mailto:{E(s["email"])}">{E(s["email"])}</a>. Vă răspundem în cel mult o lună.</p>
<p>Puteți depune o plângere la Autoritatea Națională de Supraveghere a Prelucrării Datelor cu Caracter Personal (ANSPDCP), <a href="https://www.dataprotection.ro/" target="_blank" rel="noopener">www.dataprotection.ro</a>.</p>
<h2>7. Securitate</h2>
<p>Site-ul folosește conexiune criptată (HTTPS). Accesul la cereri îl au doar persoanele din echipă care trebuie să vă răspundă.</p>
<h2>8. Modificări</h2>
<p>Putem actualiza această politică. Data ultimei actualizări apare la începutul paginii.</p>
</div></section>'''
        self.simple('politica-de-confidentialitate/', 'Politica de confidențialitate', 'Cum folosim și cum protejăm datele pe care ni le trimiteți.', inner,
                    'Politica de confidențialitate – Căminul Adina', 'Cum prelucrează Căminul Adina datele personale trimise prin site, telefon sau WhatsApp și ce drepturi aveți conform GDPR.', 'Politica de confidențialitate', cta=False)

    def cookies(self):
        ga = self.s['analytics'].get('ga4Id')
        stat_rows = '<tr><td>_ga, _ga_*</td><td>Google Analytics 4</td><td>Statistici</td><td>până la 2 ani</td></tr>' if ga else '<tr><td colspan="4">Nu folosim momentan niciun instrument de statistici.</td></tr>'
        inner = f'''<section><div class="wrap prose">
<p>Acest site nu folosește cookie-uri de publicitate. Folosim doar ce e necesar ca site-ul să funcționeze și, numai cu acordul dumneavoastră, conținut extern de pe Facebook și Google.</p>
<h2>Ce stocăm și de ce</h2>
<table><thead><tr><th>Nume</th><th>Furnizor</th><th>Categorie</th><th>Durată</th></tr></thead><tbody>
<tr><td>adina-consent (stocare locală)</td><td>Căminul Adina</td><td>Necesare: reține alegerea privind cookie-urile</td><td>12 luni, apoi vă întrebăm din nou</td></tr>
<tr><td>datr, fr, sb și altele</td><td>Meta (Facebook)</td><td>Conținut extern: videoclipurile de pe Facebook</td><td>conform politicii Meta</td></tr>
<tr><td>NID, AEC și altele</td><td>Google</td><td>Conținut extern: hărțile Google</td><td>conform politicii Google</td></tr>
{stat_rows}
</tbody></table>
<h2>Conținut extern</h2>
<p>Videoclipurile de pe Facebook și hărțile Google nu se încarcă automat. În locul lor vedeți un buton. Doar când apăsați „Pornește videoclipul” sau „Încarcă harta”, ori când acceptați conținutul extern, browserul se conectează la Facebook sau Google, care pot seta cookie-uri proprii. Detalii: <a href="https://www.facebook.com/privacy/policies/cookies/" target="_blank" rel="noopener">Politica Meta privind cookie-urile</a> și <a href="https://policies.google.com/technologies/cookies" target="_blank" rel="noopener">Politica Google privind cookie-urile</a>.</p>
<h2>Cum vă schimbați alegerea</h2>
<p>Oricând, din butonul de mai jos sau din linkul „Setări cookie” din subsolul fiecărei pagini.</p>
<p><button class="btn btn-ink" type="button" data-consent="settings">Deschide setările cookie</button></p>
<p>Puteți șterge oricând cookie-urile și datele site-ului din setările browserului.</p>
<p>Pentru întrebări: <a href="mailto:{E(self.s["email"])}">{E(self.s["email"])}</a>. Vedeți și <a href="../politica-de-confidentialitate/">Politica de confidențialitate</a>.</p>
</div></section>'''
        self.simple('politica-cookies/', 'Politica de cookie-uri', 'Ce stocăm în browserul dumneavoastră și cum vă puteți schimba alegerea.', inner,
                    'Politica de cookie-uri – Căminul Adina', 'Ce cookie-uri și ce conținut extern folosește site-ul Căminul Adina și cum vă puteți schimba preferințele.', 'Politica de cookie-uri', cta=False)

    def notfound(self):
        # 404 servit de la rădăcină: folosește linkuri absolute pe baza URL-ului site-ului
        body = f'''<section><div class="wrap prose"><h1>Pagina nu există</h1><p class="lead" style="margin-top:16px">Linkul pe care l-ați urmat e greșit sau pagina a fost mutată.</p>
<p><a class="btn btn-ink" href="{self.abs()}">Mergi la pagina principală</a></p><p>Sau sunați-ne la <a href="tel:{self.s["phoneE164"]}">{E(self.s["phone"])}</a>.</p></div></section>'''
        self.page('404.html', 'Pagina nu există – Căminul Adina', 'Pagina căutată nu există.', body, depth=0, robots='noindex', cta=False)
        # pe 404 linkurile relative nu funcționează din subpagini; le facem absolute
        p = self.out / '404.html'
        t = p.read_text(encoding='utf-8')
        t = re.sub(r'(href|src)="(?!https?:|tel:|mailto:|#)([^"]*)"', lambda m: f'{m.group(1)}="{self.abs(m.group(2))}"', t)
        p.write_text(t, encoding='utf-8')

    def redirects(self):
        for old in ('acasa/', 'situatia-covid-19/'):
            write(self.out, old + 'index.html', f'<!doctype html><html lang="ro"><head><meta charset="utf-8"><title>Căminul Adina</title><meta name="robots" content="noindex"><link rel="canonical" href="{self.abs()}"><meta http-equiv="refresh" content="0; url=../"></head><body><p><a href="../">Mergi la pagina principală</a></p></body></html>')

    def seo_files(self):
        prod = self.env == 'production'
        today = dt.date.today().isoformat()
        urls = [p for p, rob in self.pages if 'noindex' not in rob and p != '404.html']
        prio = lambda p: '1.0' if p == '' else ('0.9' if p.startswith('camin-batrani') else '0.6')
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
            f'<url><loc>{self.abs(p)}</loc><lastmod>{today}</lastmod><priority>{prio(p)}</priority></url>\n' for p in urls) + '</urlset>\n'
        if prod:
            write(self.out, 'sitemap.xml', sm)
            write(self.out, 'robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {self.abs("sitemap.xml")}\n')
        else:
            # previzualizare: sitemap generat pentru verificare, dar motoarele sunt rugate să nu indexeze
            write(self.out, 'sitemap.xml', sm.replace(self.url, self.s['productionUrl']))
            write(self.out, 'robots.txt', 'User-agent: *\nDisallow: /\n')
        write(self.out, 'site.webmanifest', json.dumps({'name': 'Căminul Adina', 'short_name': 'Căminul Adina', 'lang': 'ro', 'start_url': './', 'display': 'browser',
            'background_color': '#ffffff', 'theme_color': '#14263A', 'icons': [{'src': 'assets/media/site/logo/logo-caminul-adina-192.png', 'sizes': '192x192', 'type': 'image/png'},
            {'src': 'assets/media/site/logo/logo-caminul-adina-512.png', 'sizes': '512x512', 'type': 'image/png'}]}, ensure_ascii=False, indent=1))
        write(self.out, '.nojekyll', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', choices=['preview', 'production'], default=os.environ.get('SITE_ENV', 'preview'))
    ap.add_argument('--out', default='dist')
    ap.add_argument('--site-url', default=os.environ.get('SITE_URL', ''))
    ap.add_argument('--file-links', action='store_true', help='linkuri spre index.html, ca site-ul să se deschidă cu dublu-clic, fără server')
    a = ap.parse_args()
    out = (ROOT / a.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    site = Site(a.env, out, a.site_url or ('' if a.env == 'production' else 'https://caminul-adina.ro')).build()
    if a.file_links:
        for f in out.rglob('*.html'):
            t = f.read_text(encoding='utf-8')
            t = re.sub(r'href="((?:\.\./)*)((?:[a-z0-9-]+/)*)(\?[^"#]*)?(#[^"]*)?"', lambda m: f'href="{m.group(1)}{m.group(2)}index.html{m.group(3) or ""}{m.group(4) or ""}"' if (m.group(1) or m.group(2) or m.group(3) or not m.group(4)) else m.group(0), t)
            f.write_text(t, encoding='utf-8')
    n = len(list(out.rglob('*.html')))
    print(f'Gata: {n} pagini HTML în {out} (mediu: {a.env}, URL: {site.url})')
    if site.media.missing:
        miss = sorted(set(site.media.missing))
        print(f'Atenție: {len(miss)} fișiere media lipsesc (s-au folosit înlocuitori), de ex.: {", ".join(miss[:5])}')
    if not Image:
        print('Notă: Pillow nu e instalat, pozele nu au variante responsive (pip install pillow).')


if __name__ == '__main__':
    main()
