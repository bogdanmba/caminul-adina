# Căminul Adina – site nou

Site static, generat cu un script Python fără dependențe obligatorii. Are 17 pagini: acasă, câte o pagină pentru fiecare dintre cele 5 locații, servicii, prețuri, galerie, despre noi, întrebări frecvente, contact și politicile GDPR.

## Structura

| Folder / fișier | Ce conține |
| --- | --- |
| `content/site.json` | Telefon, e-mail, date firmă, rețele sociale, Google Analytics, formular |
| `content/locatii.json` | Cele 5 locații: adresă, preț, texte, dotări, poza de copertă, reels de pe Facebook |
| `content/faq.json` | Întrebările frecvente (apar și în Google ca rezultate FAQ) |
| `content/media-excluse.txt` | Pozele care nu apar pe site |
| `content/media-alt.json` | Descrieri (text alternativ) pentru poze, bune pentru SEO și accesibilitate |
| `media/` | Pozele și videoclipurile originale (de pe Facebook și de pe site-ul vechi) |
| `src/assets/` | CSS, JavaScript și fonturile (găzduite local, fără Google Fonts) |
| `build.py` | Generatorul: produce site-ul în `dist/` |

## Cum construiești site-ul

```
pip install pillow          # o singură dată; generează pozele responsive
python build.py             # previzualizare (noindex) în dist/
python build.py --env production   # varianta finală pentru caminul-adina.ro
```

Deschide `dist/index.html` în browser sau rulează `python -m http.server --directory dist` și intră pe http://localhost:8000.

## Adaugi poze noi

Pune fișierul în `media/facebook/<locatie>/` sau `media/site/<locatie>/` (locații: `pipera`, `otopeni`, `snagov`, `ploiesti`, `poiana-brasov`) și reconstruiește. Pozele apar automat în galeria locației. Videoclipurile `.mp4` merg în `media/site/<locatie>/video/`.

## Publicare pe GitHub Pages (previzualizare pentru client)

1. Creează un repository nou și gol pe github.com, de exemplu `caminul-adina`. **Public**, ca Pages să fie gratuit.
2. Urcă folderul (cu GitHub Desktop: *Add existing repository* → *Publish repository*, sau din linia de comandă):
   ```
   git remote add origin https://github.com/UTILIZATOR/caminul-adina.git
   git push -u origin main
   ```
3. Pe GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. La primul push, workflow-ul `Publicare GitHub Pages` construiește și publică site-ul în 1–2 minute.
   Adresa: `https://UTILIZATOR.github.io/caminul-adina/`. Linkul se poate trimite clientului.

Previzualizarea are `noindex` și `robots.txt` cu `Disallow`, ca Google să nu o indexeze și să nu dubleze conținutul de pe caminul-adina.ro.

## Mutarea pe caminul-adina.ro

1. `python build.py --env production` și urcă conținutul din `dist/` pe hosting (sau păstrează GitHub Pages cu domeniu propriu).
2. Redirecționări 301 de pe adresele vechi: `/acasa/` → `/`, `/situatia-covid-19/` → `/`, `/galerie/`, `/servicii/`, `/despre-noi/`, `/contact/` rămân la fel.
3. Trimite `https://caminul-adina.ro/sitemap.xml` în Google Search Console.
4. Actualizează profilurile Google Business ale locațiilor cu linkul paginii fiecărei locații.

## Formular

Fără configurare, formularul deschide aplicația de e-mail cu cererea completată (și oferă WhatsApp ca alternativă). Ca mesajele să ajungă direct pe e-mail, creează un formular gratuit pe Formspree sau Web3Forms și pune adresa endpoint-ului în `content/site.json` → `forms.endpoint`.

## GDPR

- Bannerul de cookie-uri are trei categorii: necesare, conținut extern (Facebook, Google Maps), statistici.
- Videoclipurile de pe Facebook și hărțile Google nu se încarcă până nu le permite vizitatorul. Site-ul nu face nicio cerere către terți înainte de acord.
- Fonturile sunt găzduite local, deci nu se fac cereri către Google Fonts.
- Google Analytics se activează doar dacă pui un ID în `content/site.json` → `analytics.ga4Id`, și doar după acordul vizitatorului (Consent Mode v2).
- Alegerea se reține 12 luni, apoi vizitatorul e întrebat din nou.
- Textele politicilor sunt un model. Recomandăm verificarea lor de către un jurist înainte de lansare.
