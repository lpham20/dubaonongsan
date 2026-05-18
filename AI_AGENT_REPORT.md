# AI Agent Execution Report - AI_CRAWLABLE_PLAN

**Started**: 2026-05-18T09:43:18+07:00
**Completed**: 2026-05-18T11:34:32+07:00
**Agent**: Codex
**Branch**: main

## Rule Notes

- User override on 2026-05-18: deploy to VPS after completion and verify live stability.
- Plan rule still followed otherwise: execute tasks sequentially, verify each task, and record raw outputs.
- Because this workspace runs on Windows PowerShell, bash-only verification commands are run as PowerShell equivalents when necessary; the actual command used is recorded.

## Summary

| Status | Count |
|---|---:|
| DONE | 25 |
| SKIPPED | 0 |
| BLOCKED | 0 |
| FAILED (verify) | 0 |

## Task L0.1 - Verify environment

**Status**: DONE
**Commits**: none

**Verification output**:

```powershell
Command 1:
Get-ChildItem -Force scripts\prerender_seo.py | Format-Table -AutoSize Mode,Length,LastWriteTime,Name

Mode   Length LastWriteTime        Name
----   ------ -------------        ----
-a----  23495 5/15/2026 9:23:12 PM prerender_seo.py

Command 2:
Get-ChildItem -Force deploy\Caddyfile | Format-Table -AutoSize Mode,Length,LastWriteTime,Name

Mode   Length LastWriteTime        Name
----   ------ -------------        ----
-a----   5068 5/15/2026 4:10:50 PM Caddyfile

Command 3:
Get-ChildItem -Force frontend\public | Format-Table -AutoSize Mode,Length,LastWriteTime,Name

Mode   Length LastWriteTime         Name
----   ------ -------------         ----
-a----     33 5/10/2026 12:03:24 AM 0467849412e6407086407e8a184407c8.txt
-a----     33 5/7/2026 11:48:02 AM  2f2c0e1a3d9b4f6c8a7e5d1c0b9a8342.txt
-a----  36864 5/7/2026 11:58:41 AM  apple-touch-icon.png
-a---- 198978 4/29/2026 12:11:48 PM coffee-hero-photo.jpg
-a----  30424 5/6/2026 8:25:55 PM   coffee-hero-photo.webp
-a---- 468625 4/29/2026 12:11:46 PM durian-hero-photo.jpg
-a---- 146240 5/6/2026 8:25:55 PM   durian-hero-photo.webp
-a----    456 4/30/2026 11:11:20 PM favicon.svg
-a----  66852 5/5/2026 2:34:34 PM   guide-food-crop-optimized.jpg
-a----  57150 5/5/2026 2:34:34 PM   guide-fruit-optimized.jpg
-a---- 103818 5/5/2026 2:34:34 PM   guide-industrial-optimized.jpg
-a----  86610 5/5/2026 2:34:34 PM   guide-other-optimized.jpg
-a----  41323 5/7/2026 11:58:34 AM  icon-192.png
-a---- 240361 5/7/2026 11:58:36 AM  icon-512.png
-a---- 245226 5/7/2026 11:58:39 AM  icon-maskable-512.png
-a----   1053 5/7/2026 11:59:27 AM  manifest.webmanifest
-a----  48072 5/5/2026 2:34:38 PM   og-cover.jpg
-a----  24790 5/7/2026 9:45:46 AM   og-cover.webp
-a----    260 5/15/2026 3:50:32 PM  robots.txt
-a----    953 5/7/2026 3:18:35 PM   _headers
-a----    897 5/8/2026 10:53:04 AM  _redirects

Command 4:
Get-ChildItem -Force backend\app\api | Format-Table -AutoSize Mode,Length,LastWriteTime,Name

Mode   Length LastWriteTime        Name
----   ------ -------------        ----
d-----        5/18/2026 9:20:59 AM __pycache__
-a---- 13796  5/15/2026 9:46:28 PM analytics.py
-a---- 4614   5/15/2026 9:20:49 PM auth.py
-a---- 15976  5/18/2026 9:20:40 AM content.py
-a---- 5121   5/5/2026 7:18:42 PM  fertilizer.py
-a---- 2616   5/9/2026 12:14:04 AM metadata.py
-a---- 4286   5/8/2026 2:55:32 PM  ops.py
-a---- 3414   5/15/2026 9:19:04 PM public.py
-a---- 44     5/1/2026 3:58:44 PM  __init__.py

Command 5:
python --version

Python 3.11.9

Command 6:
curl.exe -fsS -m 10 https://api.dubaonongsan.com/health

First attempt:
curl: (28) Connection timed out after 10004 milliseconds

Retry allowed by rule 0.4:
{"status":"ok","service":"Dự báo nông sản"}

Command 7:
Get-Content frontend\package.json | Select-String -Pattern '"build"|"build:seo"' | Select-Object -First 3

    "build": "tsc && vite build && python ../scripts/prerender_seo.py",
    "build:seo": "npm run build",
```

**Acceptance criteria**:

- [x] All required files/folders exist.
- [x] Python version is >= 3.11.
- [x] API health check returned 200 on the single allowed retry.
- [x] Build scripts include `build` and `build:seo`.

## Task L1.0 - Read `scripts/prerender_seo.py`

**Status**: DONE
**Commits**: none

**Read confirmation**:

Read full file `scripts/prerender_seo.py`. The file has 556 lines. Structure reviewed:

- `_page()`
- `_json()`
- `_breadcrumb()`
- `_schema_block()`
- `render_news()`
- `render_guides()`
- `render_static_pages()`
- `write_sitemap()`
- `ping_indexnow()`

**Verification output**:

```powershell
Command:
(Get-Content scripts\prerender_seo.py | Measure-Object -Line).Lines

556
```

**Acceptance criteria**:

- [x] Full file read.
- [x] Line count is greater than 400.

## Task L1.1 - Add `_fetch_*` helpers

**Status**: DONE
**Commit**: `d186b2b feat(seo): L1.1 - add fetch helpers`

**Verification output**:

```powershell
Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '^def _fetch_').Count

4

Command:
python -c "import ast; ast.parse(open('scripts/prerender_seo.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK
```

**Acceptance criteria**:

- [x] Exactly 4 `_fetch_*` helper functions added.
- [x] Python syntax check passed.

## Task L1.2 - Prerender homepage with movers and news

**Status**: DONE
**Commit**: `e01c2b8 feat(seo): L1.2 - prerender homepage with movers and news`

**Verification output**:

```powershell
Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '^def _build_home_body').Count

1

Command:
(Select-String -Path scripts\prerender_seo.py -Pattern 'filename == "home.html"').Count

1

Command:
python -c "import ast; ast.parse(open('scripts/prerender_seo.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK

Command:
@'
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'scripts')
from prerender_seo import _build_home_body
result = _build_home_body('Test', 'Test desc')
print(f'Length: {len(result)} chars')
print(result[:300])
'@ | python -

Length: 4047 chars
<main><h1>Test</h1>
<p>Test desc</p>
<h2>Dự báo giá theo nông sản</h2>
<ul>
<li><a href="https://dubaonongsan.com/du-bao-gia/sau_rieng">Giá sầu riêng hôm nay và dự báo 30 ngày</a></li>
<li><a href="https://dubaonongsan.com/du-bao-gia/ca_phe">Giá cà phê hôm nay và dự báo 30 ngày</a></li>
<li><a href=
```

**Acceptance criteria**:

- [x] `_build_home_body` appears exactly once as a function definition.
- [x] `filename == "home.html"` appears exactly once.
- [x] Syntax check passed.
- [x] Dry-run output length is >= 500 chars.

**Notes**:

- The first dry-run attempt failed only while printing Unicode to the Windows cp1252 console. It was retried once with UTF-8 stdout and passed.

## Task L1.3 - Prerender `/huong-dan` index with 30 guides

**Status**: DONE
**Commit**: `cb76ea1 feat(seo): L1.3 - prerender huong-dan index with 30 guides`

**Verification output**:

```powershell
Initial dry-run observation:
Length: 637 chars
PASS

The initial implementation matched the mock assertions but did not satisfy the expected length note (>= 800 chars).
The body copy was expanded with one additional descriptive paragraph, then verification was rerun.

Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '^def _build_guides_index_body').Count

1

Command:
python -c "import ast; ast.parse(open('scripts/prerender_seo.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK

Command:
@'
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'scripts')
import prerender_seo

def mock_fetch_guides(limit=30):
    return [
        {'slug': 'test-guide-1', 'title': 'Test 1', 'summary': 'Summary 1', 'category': 'Cẩm nang sầu riêng'},
        {'slug': 'test-guide-2', 'title': 'Test 2', 'summary': 'Summary 2', 'category': 'Chăm sóc cà phê'},
    ]
prerender_seo._fetch_guides_for_index = mock_fetch_guides

result = prerender_seo._build_guides_index_body('Cẩm nang', 'Mô tả')
print(f'Length: {len(result)} chars')
assert 'test-guide-1' in result, 'Missing slug 1'
assert 'test-guide-2' in result, 'Missing slug 2'
assert 'Cẩm nang sầu riêng' in result, 'Missing category'
assert len(result) >= 800, 'Length below 800 chars'
print('PASS')
'@ | python -

Length: 935 chars
PASS
```

**Acceptance criteria**:

- [x] `_build_guides_index_body` appears exactly once as a function definition.
- [x] Syntax check passed.
- [x] Dry-run output `PASS`.
- [x] Dry-run length is >= 800 chars.

## Task L1.5 - Prerender fertilizer index static content

**Status**: DONE
**Commit**: `53907c0 feat(seo): L1.5 - prerender fertilizer index static content`

**Verification output**:

```powershell
Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '^def _build_fertilizer_index_body').Count

1

Command:
python -c "import ast; ast.parse(open('scripts/prerender_seo.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK

Initial dry-run:
Length: 1825 chars
Traceback (most recent call last):
  File "<stdin>", line 7, in <module>
AssertionError

Debug retry showed PowerShell literal encoding mismatch:
Length: 1825 chars
has coffee: False
has WASI: True
len>=1500: True
<main>
<h1>Khuy?n ngh?</h1>
<p>desc</p>

<h2>Cây trồng được hỗ trợ</h2>
<ul>
<li><strong>Cà phê vối Robusta</strong>: phù hợp đất bazan đỏ Tây Nguyên, granite xám, gneiss. Tham chiếu WASI 2016, IPI 2015.</li>

Command:
@'
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'scripts')
from prerender_seo import _build_fertilizer_index_body
result = _build_fertilizer_index_body('Khuyến nghị', 'desc')
print(f'Length: {len(result)} chars')
assert 'C\u00e0 ph\u00ea v\u1ed1i Robusta' in result
assert 'WASI' in result
assert len(result) >= 1500
print('PASS')
'@ | python -

Length: 1825 chars
PASS
```

**Acceptance criteria**:

- [x] `_build_fertilizer_index_body` appears exactly once.
- [x] Syntax check passed.
- [x] Dry-run output `PASS`.
- [x] Dry-run length is >= 1500 chars.

## Task L1.6 - Prerender forecast pages with price table and forecast preview

**Status**: DONE
**Commit**: `b15c442 feat(seo): L1.6 - prerender forecast pages with price table and forecast preview`

**Verification output**:

```powershell
Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '^def _build_forecast_body').Count

1

Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '_build_forecast_body\(crop, label').Count

1

Command:
python -c "import ast; ast.parse(open('scripts/prerender_seo.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK
```

**Acceptance criteria**:

- [x] `_build_forecast_body` appears exactly once.
- [x] Forecast writer calls `_build_forecast_body(crop, label, title, desc)`.
- [x] Syntax check passed.

## Task L1.7 - Prerender methodology pages with detailed content

**Status**: DONE
**Commit**: `60020fc feat(seo): L1.7 - prerender methodology pages with detailed content`

**Verification output**:

```powershell
Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '^def _build_methodology_body|^def _build_fertilizer_methodology_body').Count

2

Command:
(Select-String -Path scripts\prerender_seo.py -Pattern 'filename == "methodology.html"').Count

1

Command:
python -c "import ast; ast.parse(open('scripts/prerender_seo.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK

Command:
@'
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'scripts')
from prerender_seo import _build_methodology_body, _build_fertilizer_methodology_body
r1 = _build_methodology_body('T', 'D')
r2 = _build_fertilizer_methodology_body('T', 'D')
print(f'methodology: {len(r1)} chars')
print(f'fertilizer-method: {len(r2)} chars')
assert len(r1) > 2000 and len(r2) > 2000, 'Content too short'
print('PASS')
'@ | python -

methodology: 2945 chars
fertilizer-method: 2584 chars
PASS
```

**Acceptance criteria**:

- [x] Two methodology builders exist.
- [x] Static page dispatcher handles `methodology.html`.
- [x] Syntax check passed.
- [x] Both methodology bodies are > 2000 chars and satisfy expected >= 2500 chars.

## Task L1.8 - Full prerender verification

**Status**: DONE
**Commit**: `c335f74 feat(seo): L1.8 - full prerender verification pass`

**Verification output**:

```powershell
Command:
python prerender_seo.py

First run output:
SEO warning: fetch prices for ho_tieu failed: <urlopen error timed out>
SEO HTML generated in C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\seo

First measurement:
home.html: 2545 chars visible
guides.html: 5288 chars visible
news.html: 6779 chars visible
fertilizer.html: 1667 chars visible
methodology.html: 2638 chars visible
fertilizer-methodology.html: 2280 chars visible
forecast/sau_rieng.html: 2228 chars visible
forecast/ca_phe.html: 2145 chars visible
forecast/ho_tieu.html: 1504 chars visible
forecast/lua.html: 2252 chars visible

Fix applied before final DONE:
- Added more visible methodology text to fertilizer methodology.
- Added more fallback forecast text for API timeout cases.
- Added stronger news fallback text for API timeout cases.

Command:
python prerender_seo.py

Final run output:
SEO prerender warning: cannot fetch /api/v1/content/news from https://api.dubaonongsan.com: <urlopen error timed out>
SEO prerender warning: cannot fetch /api/v1/content/guides from https://api.dubaonongsan.com: <urlopen error timed out>
SEO HTML generated in C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\seo

Command:
Get-ChildItem -Force frontend\dist\seo | Format-Table -AutoSize Mode,Length,LastWriteTime,Name

Mode   Length LastWriteTime         Name
----   ------ -------------         ----
d-----        5/14/2026 11:02:30 PM forecast
d-----        5/15/2026 4:04:26 PM  guides
d-----        5/18/2026 10:11:57 AM news
d-----        5/14/2026 11:02:30 PM news-views
-a---- 7250   5/18/2026 10:19:26 AM fertilizer-methodology.html
-a---- 5660   5/18/2026 10:18:17 AM fertilizer.html
-a---- 14002  5/18/2026 10:18:17 AM guides.html
-a---- 7998   5/18/2026 10:18:15 AM home.html
-a---- 7084   5/18/2026 10:19:26 AM methodology.html
-a---- 16422  5/18/2026 10:18:16 AM news.html

Command:
Get-ChildItem frontend\dist\seo\forecast | Format-Table -AutoSize Name,Length,LastWriteTime

Name           Length LastWriteTime
----           ------ -------------
ca_phe.html      9089 5/18/2026 10:18:39 AM
ho_tieu.html    10167 5/18/2026 10:19:24 AM
lua.html         9198 5/18/2026 10:19:26 AM
sau_rieng.html   9347 5/18/2026 10:18:18 AM

Command:
visible text measurement helper

home.html: 2545 chars visible
guides.html: 5288 chars visible
news.html: 6779 chars visible
fertilizer.html: 1667 chars visible
methodology.html: 2638 chars visible
fertilizer-methodology.html: 2680 chars visible
forecast/sau_rieng.html: 2497 chars visible
forecast/ca_phe.html: 2411 chars visible
forecast/ho_tieu.html: 3172 chars visible
forecast/lua.html: 2515 chars visible
```

**Acceptance criteria**:

- [x] Prerender script ran without Python error.
- [x] All 10 target files exist.
- [x] All 10 target files have visible text >= required threshold.
- [x] No target file is MISSING.
- [x] No target file has visible text < 1000.

## Task L2.1 - Replace hidden attribute with visually-hidden class

**Status**: DONE
**Commit**: `7665bfa refactor(seo): L2.1 - replace hidden attribute with visually-hidden class`

**Verification output**:

```powershell
Command:
(Select-String -Path scripts\prerender_seo.py -Pattern 'id="seo-prerender" hidden').Count

0

Command:
(Select-String -Path scripts\prerender_seo.py -Pattern 'id="seo-prerender" class="visually-hidden"').Count

1
```

**Acceptance criteria**:

- [x] Hidden attribute pattern count is 0.
- [x] `visually-hidden` class pattern count is 1.

## Task L2.2 - Add CSS rule for `.visually-hidden`

**Status**: DONE
**Commit**: `b6a3177 feat(seo): L2.2 - add visually-hidden CSS for SEO prerender content`

**CSS file selected**: `frontend/src/styles/base.css`

`base.css` is the global base stylesheet imported by `frontend/src/main.tsx`, so it is the correct shared place for the generic SEO helper rule.

**Verification output**:

```powershell
Command:
(Select-String -Path frontend\src\styles\base.css -Pattern '^\.visually-hidden').Count

1

Command:
@'
from pathlib import Path
import re
css = Path('frontend/src/styles/base.css').read_text(encoding='utf-8')
match = re.search(r'\.visually-hidden\s*\{([^}]*)\}', css, re.S)
if not match:
    raise SystemExit('RULE_MISSING')
props = re.findall(r'([a-z-]+)\s*:', match.group(1))
print('properties=' + ','.join(props))
print('property_count=' + str(len(props)))
required = ['position','width','height','padding','margin','overflow','clip','white-space','border','left','top']
missing = [p for p in required if p not in props]
print('missing=' + ','.join(missing))
assert len(props) == 11
assert not missing
print('PASS')
'@ | python -

properties=position,width,height,padding,margin,overflow,clip,white-space,border,left,top
property_count=11
missing=
PASS

Command:
npm run build:app

First run: timed out after 120s with no compiler error output.
Retry with 360s timeout:
> marketai-durian-dashboard@0.1.0 build:app
> tsc && vite build

vite v6.4.2 building for production...
5243 modules transformed.
dist/index.html                                  5.63 kB
dist/assets/index-C2zQyCW8.css                   319.39 kB
dist/assets/index-pymC8vAP.js                    52.91 kB
built in 31.86s
PWA v1.3.0
mode generateSW
precache 812 entries (16563.10 KiB)
files generated
  dist/sw.js
  dist/workbox-7334f08a.js
```

**Acceptance criteria**:

- [x] CSS file identified and modified.
- [x] `.visually-hidden` rule has all 11 required properties.
- [x] Grep count is 1.
- [x] Frontend build passed on retry with extended timeout.

## Task L2.3 - Verify CSS bundle keeps `.visually-hidden`

**Status**: DONE

**Verification output**:

```powershell
Command:
Get-ChildItem frontend\dist\assets\*.css | Select-Object -ExpandProperty FullName

C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-B-jh8zYM.css
C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-B6oUw7fd.css
C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-BaohpWgH.css
C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-BaYcb9vP.css
C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-Bgjx309m.css
C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-BoSeqVz5.css
C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-C2zQyCW8.css
... older historical build CSS files also present in dist/assets

Command:
$matches = Select-String -Path frontend\dist\assets\*.css -Pattern 'visually-hidden'
$matches.Count
$matches | Select-Object -First 5 | ForEach-Object { $_.Path + ':' + $_.LineNumber + ':' + $_.Line.Substring(0, [Math]::Min(200, $_.Line.Length)) }

1
C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\assets\index-C2zQyCW8.css:1::root{--accent: #167052;--accent-deep: #0d4b38;--accent-darker: #08321f;--accent-soft: #d9efe4;--accent-50: #f0f8f3;--harvest: #d7a93b;--harvest-soft: #fff1d6;--sky: #a9d6df;--soil: #
```

**Acceptance criteria**:

- [x] CSS bundle exists in `frontend/dist/assets`.
- [x] `visually-hidden` appears in a built CSS bundle.

## Task L3a.1 - Add `frontend/public/llms.txt`

**Status**: DONE
**Commit**: `d08dcf8 feat(seo): L3a.1 - add llms.txt for AI agent discovery`

**Verification output**:

```powershell
Command:
Get-Item frontend\public\llms.txt | Format-List FullName,Length,LastWriteTime

FullName      : C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\public\llms.txt
Length        : 3627
LastWriteTime : 5/18/2026 10:35:37 AM

Command:
@'
from pathlib import Path
p=Path('frontend/public/llms.txt')
text=p.read_text(encoding='utf-8')
print('bytes=' + str(len(p.read_bytes())))
print('h1=' + str(sum(1 for line in text.splitlines() if line.startswith('# '))))
print('h2=' + str(sum(1 for line in text.splitlines() if line.startswith('## '))))
print('urls=' + str(text.count('https://')))
assert len(p.read_bytes()) > 1500
assert sum(1 for line in text.splitlines() if line.startswith('# ')) >= 1
assert sum(1 for line in text.splitlines() if line.startswith('## ')) >= 6
assert text.count('https://') >= 15
print('PASS')
'@ | python -

bytes=3627
h1=1
h2=8
urls=26
PASS
```

**Acceptance criteria**:

- [x] File exists in `frontend/public/`.
- [x] Size is > 1500 bytes.
- [x] Has >= 1 H1 and >= 6 H2 sections.
- [x] Has >= 15 `https://` URLs.

## Task L3a.2 - Verify `llms.txt` is served as a static frontend file

**Status**: DONE

**Verification output**:

```powershell
Command:
Select-String -Path deploy\Caddyfile -Pattern 'handle \{' -Context 0,30 | Select-Object -First 1 | ForEach-Object { $_.Line; $_.Context.PostContext }

handle {
  root * /var/www/frontend
  @seoHome { path / }
  rewrite @seoHome /seo/home.html
  ...

Command:
Select-String -Path deploy\Caddyfile -Pattern 'llms' -CaseSensitive:$false

# no output

Command:
if (Test-Path frontend\vite.config.ts) { Select-String -Path frontend\vite.config.ts -Pattern 'publicDir|publicPath' } else { 'vite.config.ts missing' }

# no output, so Vite uses the default publicDir and copies frontend/public into dist

Command:
npm run build:app

> marketai-durian-dashboard@0.1.0 build:app
> tsc && vite build

vite v6.4.2 building for production...
5243 modules transformed.
dist/index.html                                  5.63 kB
dist/assets/index-C2zQyCW8.css                   319.39 kB
dist/assets/index-pymC8vAP.js                    52.91 kB
built in 32.79s

Command:
Get-Item frontend\dist\llms.txt | Format-List FullName,Length,LastWriteTime

FullName      : C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\llms.txt
Length        : 3627
LastWriteTime : 5/18/2026 10:35:37 AM

Command:
python verify snippet

exists=True
bytes=3627
h1=1
urls=26
```

**Acceptance criteria**:

- [x] Caddyfile has no block/rewrite rule for `llms.txt`.
- [x] Frontend build copies `frontend/public/llms.txt` to `frontend/dist/llms.txt`.

## Task L3b.0 - Read existing API structure

**Status**: DONE

**Router pattern observed**:

- API files create `router = APIRouter(prefix=settings.api_prefix, tags=[...])`.
- `backend/app/main.py` imports each router and calls `app.include_router(...)`.
- Existing routers: `auth_router`, `content_router`, `fertilizer_router`, `metadata_router`, `analytics_router`, `public_router`, `ops_router`.

**Verification output**:

```powershell
Command:
Select-String -Path backend\app\main.py -Pattern 'include_router|from app.api' -Context 0,1

16: from app.api.analytics import router as analytics_router
17: from app.api.auth import router as auth_router
18: from app.api.content import router as content_router
19: from app.api.fertilizer import router as fertilizer_router
20: from app.api.metadata import router as metadata_router
21: from app.api.ops import router as ops_router
22: from app.api.public import router as public_router
122: app.include_router(auth_router)
123: app.include_router(content_router)
124: app.include_router(fertilizer_router)
125: app.include_router(metadata_router)
126: app.include_router(analytics_router)
127: app.include_router(public_router)
128: app.include_router(ops_router)

Command:
Get-ChildItem backend\app\api | Select-Object Name,Length

analytics.py  13796
auth.py       4614
content.py    15976
fertilizer.py 5121
metadata.py   2616
ops.py        4286
public.py     3414
__init__.py   44
```

**Acceptance criteria**:

- [x] Existing API router pattern read and understood.
- [x] Registration location in `backend/app/main.py` identified.

## Task L3b.1 - Add `backend/app/api/llm_content.py`

**Status**: DONE
**Commit**: `a16c0fc feat(api): L3b.1 - add llm_content router with 5 markdown endpoints`

**Verification output**:

```powershell
Command:
Get-Item backend\app\api\llm_content.py | Format-List FullName,Length,LastWriteTime

FullName      : C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\backend\app\api\llm_content.py
Length        : 11390
LastWriteTime : 5/18/2026 10:43:00 AM

Command:
python -c "import ast; ast.parse(open('backend/app/api/llm_content.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK

Command:
(Select-String -Path backend\app\api\llm_content.py -Pattern '^@router').Count

5
```

**Acceptance criteria**:

- [x] File exists.
- [x] Syntax check passed.
- [x] Exactly 5 router decorators are present.

## Task L3b.2 - Register `llm_content` router in `main.py`

**Status**: DONE
**Commit**: `f6bfee1 feat(api): L3b.2 - register llm_content router in main.py`

**Verification output**:

```powershell
Command:
(Select-String -Path backend\app\main.py -Pattern 'from app.api.llm_content import router').Count
(Select-String -Path backend\app\main.py -Pattern 'app.include_router\(llm_content_router\)').Count
python -c "import ast; ast.parse(open('backend/app/main.py', encoding='utf-8').read()); print('SYNTAX_OK')"

1
1
SYNTAX_OK
```

**Acceptance criteria**:

- [x] Import exists exactly once.
- [x] `include_router` call exists exactly once.
- [x] Syntax check passed.

## Task L3b.3 - Local smoke test LLM markdown endpoints

**Status**: DONE

**Local backend setup**:

- First local startup using default SQLite file failed because a temporary `marketai.db` from the smoke run had partial migrations (`user_price_reports already exists`).
- Retried with `MARKETAI_DATABASE_URL=sqlite:///:memory:`, `MARKETAI_SEED_ON_STARTUP=true`, `MARKETAI_START_SCHEDULER_IN_API=false`.
- Backend started successfully on `127.0.0.1:8010`.
- Smoke artifacts (`backend/uvicorn-llm.*`, local `marketai.db`) were cleaned and the local process was stopped.

**Verification output**:

```powershell
Command:
Invoke-WebRequest http://127.0.0.1:8010/health

{"status":"ok","service":"Dá»± bÃ¡o nÃ´ng sáº£n"}

Command:
curl.exe -fsS "http://localhost:8010/api/v1/llm-content/forecast/sau_rieng" | Select-Object -First 30

# Giá sầu riêng Việt Nam — cập nhật 2026-05-18

Nguồn: dubaonongsan.com — dự báo giá nông sản Việt Nam.
URL gốc: https://dubaonongsan.com/du-bao-gia/sau_rieng

## Bảng giá hiện tại theo vùng và giống

| Tỉnh | Vùng | Giống | Loại | Giá min (VND/kg) | Giá max (VND/kg) | Ngày |
|---|---|---|---|---|---|---|
| Đắk Lắk | Tây Nguyên | Sầu Thái Dona | Hàng xô | 48,590 | 52,631 | 2026-04-12 |
...

Command:
curl.exe -fsS "http://localhost:8010/api/v1/llm-content/guides?limit=5" | Select-Object -First 20

# Thư viện hướng dẫn kỹ thuật canh tác — dubaonongsan.com

Tổng cộng 5 hướng dẫn gần nhất. URL gốc: https://dubaonongsan.com/huong-dan

## Chăm sóc hoa giấy

- [Chăm sóc hoa giấy ban công: cắt tỉa, tưới nước và kích hoa tự nhiên](https://dubaonongsan.com/huong-dan/do-thi-cham-soc-hoa-giay-ban-cong): Quy trình chăm hoa giấy trong chậu đô thị...

Command:
curl.exe -fsS "http://localhost:8010/api/v1/llm-content/news?limit=5" | Select-Object -First 20

# Tin tức nông sản — dubaonongsan.com

Tổng cộng 3 bản tin gần nhất. URL gốc: https://dubaonongsan.com/tin-tuc

## Phân bón - vật tư

- [Theo dõi giá phân bón và vật tư đầu vào trong mùa vụ](https://dubaonongsan.com/tin-tuc/3) (Vinanet): Biến động phân bón...

Command:
curl.exe -fsS -D - -o NUL "http://localhost:8010/api/v1/llm-content/forecast/sau_rieng" | Select-String -Pattern 'HTTP/|content-type|cache-control|x-robots-tag'

HTTP/1.1 200 OK
cache-control: public, max-age=300
x-robots-tag: index, follow
content-type: text/markdown; charset=utf-8

Command:
curl.exe -fsS "http://localhost:8010/api/v1/llm-content/guide/do-thi-cam-nang-sen-da" | Select-Object -First 16

# Cẩm nang trồng sen đá ở ban công và bệ cửa sổ
...

Command:
curl.exe -fsS "http://localhost:8010/api/v1/llm-content/news/1" | Select-Object -First 16

# Số liệu biến động thị trường, giá cả nông sản
...

Command:
Stop-Process -Id 38052
Remove-Item backend\uvicorn-llm.pid, backend\uvicorn-llm.out.log, backend\uvicorn-llm.err.log, marketai.db

STOPPED pid=38052
CLEANED local smoke artifacts
```

**Note**: `curl -I` returned 405 because FastAPI does not auto-map `HEAD` for these custom routes. The equivalent GET-header check passed and confirmed `text/markdown; charset=utf-8`.

**Acceptance criteria**:

- [x] Forecast, guides index, and news index returned 200 markdown.
- [x] Guide detail and news detail returned markdown in smoke checks.
- [x] Response body is markdown text, not JSON.
- [x] GET response headers include `content-type: text/markdown; charset=utf-8`.

## Task L3c.1 - Add Caddy `Link` headers for alternate markdown endpoints

**Status**: DONE
**Commit**: `1688025 feat(caddy): L3c.1 - add Link header for alternate markdown endpoints`

**Verification output**:

```powershell
Command:
(Select-String -Path deploy\Caddyfile -Pattern 'rel=\\\"alternate\\\"').Count
Select-String -Path deploy\Caddyfile -Pattern 'llm-content'

5
124: header @forecastPaths Link "</api/v1/llm-content/forecast/{re.forecastPaths.1}>; rel=\"alternate\"; type=\"text/markdown\""
127: header @guideDetailPaths Link "</api/v1/llm-content/guide/{re.guideDetailPaths.1}>; rel=\"alternate\"; type=\"text/markdown\""
130: header @newsDetailPaths Link "</api/v1/llm-content/news/{re.newsDetailPaths.1}>; rel=\"alternate\"; type=\"text/markdown\""
133: header @guidesIndex Link "</api/v1/llm-content/guides>; rel=\"alternate\"; type=\"text/markdown\""
136: header @newsIndex Link "</api/v1/llm-content/news>; rel=\"alternate\"; type=\"text/markdown\""

Command:
$caddy = (Get-Command caddy -ErrorAction SilentlyContinue)
if ($caddy) { caddy validate --config deploy\Caddyfile 2>&1 | Select-Object -Last 5 } else { 'caddy_not_local_skip_validate' }

caddy_not_local_skip_validate
```

**Acceptance criteria**:

- [x] Five Link header rules exist.
- [x] Local Caddy binary is unavailable, so local syntax validation is skipped per plan.

## Task L4.1 - Build frontend and run full prerender

**Status**: DONE

**Verification output**:

```powershell
Command:
npm run build:app

> marketai-durian-dashboard@0.1.0 build:app
> tsc && vite build

vite v6.4.2 building for production...
5243 modules transformed.
dist/index.html                                  5.63 kB
dist/assets/index-C2zQyCW8.css                   319.39 kB
dist/assets/index-pymC8vAP.js                    52.91 kB
built in 21.09s
PWA v1.3.0
mode generateSW
precache 812 entries (16563.10 KiB)
files generated
  dist/sw.js
  dist/workbox-7334f08a.js

Command:
python prerender_seo.py

First run: timed out at 180s.
Retry with 360s timeout:
SEO HTML generated in C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\seo

Command:
Get-ChildItem frontend\dist\seo | Select-Object Name,Length

forecast
guides
news
news-views
fertilizer-methodology.html 7286
fertilizer.html             5696
guides.html                 14038
home.html                   8034
methodology.html            7120
news.html                   16458

Command:
Get-ChildItem frontend\dist\seo\forecast | Select-Object Name,Length

ca_phe.html      9125
ho_tieu.html    10203
lua.html         9233
sau_rieng.html   9383

Command:
Get-Item frontend\dist\llms.txt | Format-List FullName,Length,LastWriteTime

FullName      : C:\Users\ptlinh\Documents\Codex\2026-04-28\files-mentioned-by-the-user-nghi\marketai\frontend\dist\llms.txt
Length        : 3627
```

**Acceptance criteria**:

- [x] Frontend build passed.
- [x] Full prerender completed.
- [x] `frontend/dist/seo`, `frontend/dist/seo/forecast`, and `frontend/dist/llms.txt` exist.

## Task L4.2 - Measure visible text for prerendered pages

**Status**: DONE

**Verification output**:

```powershell
PASS home.html: 2545 chars (min 1200)
PASS guides.html: 5288 chars (min 1500)
PASS news.html: 6779 chars (min 1500)
PASS fertilizer.html: 1667 chars (min 1500)
PASS methodology.html: 2638 chars (min 2500)
PASS fertilizer-methodology.html: 2680 chars (min 2500)
PASS forecast/sau_rieng.html: 2497 chars (min 1500)
PASS forecast/ca_phe.html: 2411 chars (min 1500)
PASS forecast/ho_tieu.html: 3172 chars (min 1500)
PASS forecast/lua.html: 2514 chars (min 1500)

=== ALL PAGES PASS ===
```

**Acceptance criteria**:

- [x] All target pages pass minimum visible-text thresholds.
- [x] Exit code was 0.

## Task L4.3 - Verify `llms.txt` and Caddy `Link` headers

**Status**: DONE

**Verification output**:

```powershell
Command:
python UTF-8 head of frontend/dist/llms.txt

# Dự báo nông sản (dubaonongsan.com)

> Nền tảng dự báo giá nông sản Việt Nam — sầu riêng, cà phê, hồ tiêu, lúa. Cập nhật giá hàng ngày từ các nguồn báo nông nghiệp và sở công thương, dự báo 30 ngày dùng mô hình machine learning.

Trang web phục vụ nông dân, thương lái, doanh nghiệp xuất khẩu nông sản. Dữ liệu được scrape công khai và mở qua API. Người dùng AI có thể fetch các URL dưới đây để có content text gốc (markdown / JSON) thay vì parse HTML SPA.

## Dữ liệu giá

- [API giá lịch sử công khai (JSON)](https://api.dubaonongsan.com/api/v1/public/prices?crop=sau_rieng): cần X-API-Key
- [Bảng giá hàng ngày (sầu riêng)](https://dubaonongsan.com/du-bao-gia/sau_rieng): HTML có bảng giá hiện tại + dự báo 30 ngày
- [Bảng giá hàng ngày (cà phê)](https://dubaonongsan.com/du-bao-gia/ca_phe)
- [Bảng giá hàng ngày (hồ tiêu)](https://dubaonongsan.com/du-bao-gia/ho_tieu)
- [Bảng giá hàng ngày (lúa)](https://dubaonongsan.com/du-bao-gia/lua)
- [Endpoint LLM markdown — giá sầu riêng](https://api.dubaonongsan.com/api/v1/llm-content/forecast/sau_rieng): text/markdown gọn cho AI
- [Endpoint LLM markdown — giá cà phê](https://api.dubaonongsan.com/api/v1/llm-content/forecast/ca_phe)
- [Endpoint LLM markdown — giá hồ tiêu](https://api.dubaonongsan.com/api/v1/llm-content/forecast/ho_tieu)
- [Endpoint LLM markdown — giá lúa](https://api.dubaonongsan.com/api/v1/llm-content/forecast/lua)

## Hướng dẫn kỹ thuật canh tác

- [Index hướng dẫn](https://dubaonongsan.com/huong-dan): list ~30 bài hướng dẫn kỹ thuật mới nhất
- [API guides (JSON)](https://api.dubaonongsan.com/api/v1/content/guides?limit=100): toàn bộ guide
- [Endpoint LLM markdown — guides index](https://api.dubaonongsan.com/api/v1/llm-content/guides): danh sách + summary
- [Endpoint LLM markdown — guide detail theo slug](https://api.dubaonongsan.com/api/v1/llm-content/guide/{slug}): nội dung đầy đủ

## Tin tức thị trường

- [Bản tin thị trường](https://dubaonongsan.com/tin-tuc): list ~30 tin mới nhất
- [RSS feed](https://dubaonongsan.com/rss/news.xml): cập nhật 50 tin gần nhất
- [API news (JSON)](https://api.dubaonongsan.com/api/v1/content/news?limit=100)
line_count=57

Command:
Select-String -Path deploy\Caddyfile -Pattern 'rel=\\\"alternate\\\"' -Context 0,1

124: header @forecastPaths Link "</api/v1/llm-content/forecast/{re.forecastPaths.1}>; rel=\"alternate\"; type=\"text/markdown\""
127: header @guideDetailPaths Link "</api/v1/llm-content/guide/{re.guideDetailPaths.1}>; rel=\"alternate\"; type=\"text/markdown\""
130: header @newsDetailPaths Link "</api/v1/llm-content/news/{re.newsDetailPaths.1}>; rel=\"alternate\"; type=\"text/markdown\""
133: header @guidesIndex Link "</api/v1/llm-content/guides>; rel=\"alternate\"; type=\"text/markdown\""
136: header @newsIndex Link "</api/v1/llm-content/news>; rel=\"alternate\"; type=\"text/markdown\""

Command:
(Select-String -Path deploy\Caddyfile -Pattern 'rel=\\\"alternate\\\"').Count

5
```

**Acceptance criteria**:

- [x] `llms.txt` has > 50 lines and visible sections.
- [x] Caddyfile has 5 Link header rules.

## Task L4.4 - Verify backend Python code compiles

**Status**: DONE

**Verification output**:

```powershell
Command:
python AST parse for all backend/app .py files

All backend .py files SYNTAX_OK
```

**Acceptance criteria**:

- [x] All backend Python files are syntactically valid.

## Task L4.5 - Write final report

**Status**: DONE
**Commit**: pending until this report is committed.

**Verification output**:

```powershell
Command:
python report completeness check

L0.1 1
L1.0 1
L1.1 1
L1.2 1
L1.3 1
L1.4 1
L1.5 1
L1.6 1
L1.7 1
L1.8 1
L2.1 1
L2.2 1
L2.3 1
L3a.1 1
L3a.2 1
L3b.0 1
L3b.1 1
L3b.2 1
L3b.3 1
L3c.1 1
L4.1 1
L4.2 1
L4.3 1
L4.4 1
```

**Acceptance criteria**:

- [x] `AI_AGENT_REPORT.md` exists.
- [x] Report has sections for tasks L0.1 through L4.4.
- [x] Report has Summary with pass/fail/blocker counts.
- [x] Report has "Next steps for user" section below.

## Files modified

- `scripts/prerender_seo.py`: +505 / -4
- `frontend/src/styles/base.css`: +17
- `frontend/public/llms.txt`: new, 3627 bytes
- `backend/app/api/llm_content.py`: new, 301 lines
- `backend/app/main.py`: +2
- `deploy/Caddyfile`: +16
- `AI_AGENT_REPORT.md`: new report file

## Acceptance criteria summary

- [x] L0.1 — environment verified; live API health retry passed.
- [x] L1 — prerender index/detail pages expanded and final visible text thresholds pass for all 10 target pages.
- [x] L2 — `hidden` attribute removed; `.visually-hidden` CSS applied and present in built CSS.
- [x] L3a — `llms.txt` created, sized > 1500 bytes, copied to `dist/llms.txt`.
- [x] L3b — 5 markdown endpoints added under `/api/v1/llm-content/` and smoke-tested locally.
- [x] L3c — 5 Caddy `Link` header rules added for alternate markdown discovery.
- [x] L4 — frontend build, prerender, visible-text gate, llms/Link gate, and backend syntax gate all passed.

## Next steps for user

The user overrode the original "do not deploy" rule and requested agent deployment to VPS. Deployment will be performed after this report commit:

1. Push `main` to the public repo.
2. SSH to VPS and pull latest code.
3. Rebuild frontend/API as required by the production compose workflow.
4. Reload/restart production services.
5. Smoke test:
   - `https://dubaonongsan.com/health` or frontend root returns 200.
   - `https://dubaonongsan.com/llms.txt` returns markdown text.
   - `https://api.dubaonongsan.com/api/v1/llm-content/forecast/sau_rieng` returns markdown.
   - `https://dubaonongsan.com/du-bao-gia/sau_rieng` includes `Link` header for markdown alternate.

## Blockers

None.

## Notes / observations

- Local `curl -I` on the new markdown endpoints returned 405 because FastAPI did not auto-map `HEAD`; equivalent GET-header smoke check passed with `content-type: text/markdown; charset=utf-8`.
- Local Caddy binary is not installed, so Caddy syntax validation was skipped locally per plan. Production reload will validate the live Caddyfile.
- PowerShell `Get-Content` displays UTF-8 Vietnamese as mojibake in some outputs; Python UTF-8 reads confirmed `frontend/dist/llms.txt` content is correct.

## Task L1.4 - Prerender `/tin-tuc` index with 30 news

**Status**: DONE
**Commit**: `0063731 feat(seo): L1.4 - prerender tin-tuc index with 30 news`

**Verification output**:

```powershell
Command:
(Select-String -Path scripts\prerender_seo.py -Pattern '^def _build_news_index_body').Count

1

Command:
python -c "import ast; ast.parse(open('scripts/prerender_seo.py', encoding='utf-8').read()); print('SYNTAX_OK')"

SYNTAX_OK

Command:
@'
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'scripts')
import prerender_seo

def mock_fetch_news(limit=30):
    return [
        {'article_id': 1, 'source_url': 'https://example.com/a', 'title': 'Tin A', 'summary': 'Sum A', 'category': 'Giá nông sản', 'source_name': 'Nguồn A'},
        {'article_id': 2, 'source_url': 'https://example.com/b', 'title': 'Tin B', 'summary': 'Sum B', 'category': 'Xuất khẩu', 'source_name': 'Nguồn B'},
    ]
prerender_seo._fetch_news_for_index = mock_fetch_news

result = prerender_seo._build_news_index_body('Tin', 'Desc')
print(f'Length: {len(result)} chars')
assert 'Tin A' in result and 'Tin B' in result, 'Missing news'
assert 'Giá nông sản' in result, 'Missing category'
assert len(result) >= 800, 'Length below 800 chars'
print('PASS')
'@ | python -

Length: 902 chars
PASS
```

**Acceptance criteria**:

- [x] `_build_news_index_body` appears exactly once as a function definition.
- [x] Syntax check passed.
- [x] Dry-run output `PASS`.
- [x] Dry-run length is >= 800 chars.
