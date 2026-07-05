# myLab/api/lab_manager.py - با صفحه کاوشگر داخلی
import sys
import logging
import tempfile
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from .font_injector import get_font_css

_myLab_dir = Path(__file__).resolve().parent.parent
if str(_myLab_dir) not in sys.path:
    sys.path.insert(0, str(_myLab_dir))

from module.smart_lab_loader import Grade, Subject
from api import PhETLabAPI

# ===== نام‌های فارسی شبیه‌سازها =====

PERSIAN_NAMES = {
    "acid-base-solutions": "محلول اسید و باز",
    "area-builder": "مساحت‌ساز",
    "area-model-algebra": "مدل جبری مساحت",
    "area-model-decimals": "مدل اعشاری مساحت",
    "area-model-introduction": "مقدمات مدل مساحت",
    "area-model-multiplication": "مدل ضربی مساحت",
    "atomic-interactions": "برهم‌کنش اتمی",
    "balancing-act": "ترازو",
    "balancing-chemical-equations": "موازنه معادلات شیمیایی",
    "balloons-and-static-electricity": "بادکنک و الکتریسیته ساکن",
    "beers-law-lab": "قانون بیر-لامبرت",
    "bending-light": "شکست نور",
    "blackbody-spectrum": "طیف تابش جسم سیاه",
    "build-a-fraction": "کسر بساز",
    "build-a-nucleus": "هسته اتم بساز",
    "build-an-atom": "اتم بساز",
    "buoyancy": "شناوری و غوطه‌وری",
    "calculus-grapher": "نمودارگر حسابان",
    "capacitor-lab-basics": "مبانی خازن",
    "center-and-variability": "مرکزیت و پراکندگی",
    "charges-and-fields": "بار و میدان الکتریکی",
    "circuit-construction-kit-ac": "مدار جریان متناوب",
    "circuit-construction-kit-ac-virtual-lab": "آزمایشگاه مجازی مدار AC",
    "circuit-construction-kit-dc": "مدار جریان مستقیم",
    "circuit-construction-kit-dc-virtual-lab": "آزمایشگاه مجازی مدار DC",
    "collision-lab": "برخورد و تکانه",
    "color-vision": "بینایی رنگ‌ها",
    "concentration": "غلظت محلول",
    "coulombs-law": "قانون کولن",
    "curve-fitting": "برازش منحنی",
    "density": "چگالی",
    "diffusion": "نفوذ و پخش",
    "energy-forms-and-changes": "انواع انرژی و تبدیل آن",
    "energy-skate-park": "پارک اسکیت و انرژی",
    "energy-skate-park-basics": "مبانی پارک اسکیت و انرژی",
    "equality-explorer": "کاوش در تساوی",
    "equality-explorer-basics": "مبانی کاوش در تساوی",
    "equality-explorer-two-variables": "کاوش تساوی دو متغیره",
    "expression-exchange": "تبادل عبارات جبری",
    "faradays-law": "قانون القای فارادی",
    "forces-and-motion-basics": "نیرو و حرکت",
    "fourier-making-waves": "ساخت موج با سری فوریه",
    "fraction-matcher": "تطبیق کسرها",
    "fractions-equality": "تساوی کسرها",
    "fractions-intro": "مقدمات کسرها",
    "fractions-mixed-numbers": "اعداد مخلوط کسری",
    "friction": "اصطکاک",
    "function-builder": "سازنده توابع",
    "function-builder-basics": "مبانی سازنده توابع",
    "gas-properties": "خواص گازها",
    "gene-expression-essentials": "مبانی بیان ژن",
    "geometric-optics": "نور هندسی",
    "geometric-optics-basics": "مبانی نور هندسی",
    "graphing-lines": "نمودار خط",
    "graphing-quadratics": "نمودار سهمی",
    "graphing-slope-intercept": "نمودار شیب-عرض",
    "gravity-and-orbits": "گرانش و مدار",
    "gravity-force-lab": "نیروی گرانش",
    "gravity-force-lab-basics": "مبانی نیروی گرانش",
    "hookes-law": "قانون هوک",
    "isotopes-and-atomic-mass": "ایزوتوپ و جرم اتمی",
    "john-travoltage": "الکتریسیته ساکن و تخلیه",
    "keplers-laws": "قوانین کپلر",
    "least-squares-regression": "رگرسیون حداقل مربعات",
    "make-a-ten": "ده‌سازی",
    "masses-and-springs": "جرم و فنر",
    "masses-and-springs-basics": "مبانی جرم و فنر",
    "mean-share-and-balance": "میانگین، تسهیم و تراز",
    "membrane-transport": "انتقال از غشا",
    "molarity": "مولاریته",
    "molecule-polarity": "قطبیت مولکول‌ها",
    "molecule-shapes": "اشکال مولکولی",
    "molecule-shapes-basics": "مبانی اشکال مولکولی",
    "my-solar-system": "منظومه شمسی من",
    "natural-selection": "انتخاب طبیعی",
    "neuron": "نورون و پیام عصبی",
    "number-compare": "مقایسه اعداد",
    "number-line-distance": "فاصله روی محور اعداد",
    "number-line-integers": "اعداد صحیح روی محور",
    "number-line-operations": "عملیات روی محور اعداد",
    "number-play": "بازی اعداد",
    "ohms-law": "قانون اهم",
    "pendulum-lab": "آونگ ساده",
    "ph-scale": "مقیاس pH",
    "ph-scale-basics": "مبانی مقیاس pH",
    "photoelectric-effect": "اثر فوتوالکتریک",
    "plinko-probability": "احتمال و پلینکو",
    "projectile-motion": "حرکت پرتابه",
    "proportion-playground": "بازی با تناسب",
    "quadrilateral": "چهارضلعی‌ها",
    "reactants-products-and-leftovers": "واکنش‌دهنده و فرآورده",
    "resistance-in-a-wire": "مقاومت الکتریکی سیم",
    "rutherford-scattering": "پراکندگی رادرفورد",
    "states-of-matter": "حالت‌های ماده",
    "states-of-matter-basics": "مبانی حالت‌های ماده",
    "trig-tour": "گشت مثلثاتی",
    "under-pressure": "تحت فشار",
    "unit-rates": "نرخ یکه",
    "vector-addition": "جمع بردارها",
    "vector-addition-equations": "معادلات جمع برداری",
    "wave-interference": "تداخل امواج",
    "wave-on-a-string": "موج در ریسمان",
    "waves-intro": "مقدمات امواج",
}


logger = logging.getLogger(__name__)


def _detect_backend():
    py_ver = sys.version_info[:2]
    if py_ver <= (3, 9):
        try:
            import cefpython3 # type: ignore
            return "cef"
        except ImportError:
            pass
    try:
        import webview
        return "webview"
    except ImportError:
        pass
    return "browser"


class LabExplorer:
    """کاوشگر آزمایشگاه مجازی - صفحه اصلی با فیلتر و جستجو"""

    def __init__(self, api: PhETLabAPI):
        self.api = api
        self._server = None
        self._port = 0
        self._labs = api.list_labs()

    def _start_server(self):
        """شروع HTTP سرور برای سرو HTML"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            self._port = s.getsockname()[1]

        class Handler(SimpleHTTPRequestHandler):
            def do_GET(self):
                try:
                    if self.path == '/' or self.path == '/explorer':
                        self._serve_html()
                    elif self.path.startswith('/api/labs'):
                        self._serve_json()
                    elif self.path.startswith('/open'):
                        self._handle_open()
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception:
                    pass

            def _serve_html(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(EXPLORER_HTML.encode('utf-8'))

            def _serve_json(self):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(explorer._labs, ensure_ascii=False).encode('utf-8'))

            def _handle_open(self):
                from urllib.parse import urlparse, parse_qs
                params = parse_qs(urlparse(self.path).query)
                name = params.get('name', [''])[0]
                grade = params.get('grade', [''])[0]
                subject = params.get('subject', [''])[0]

                if name and grade and subject:
                    explorer._open_callback(name, grade, subject)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')

            def log_message(self, format, *args):
                pass

        explorer = self
        self._server = HTTPServer(('127.0.0.1', self._port), Handler)
        import threading
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def show(self, open_callback):
        """نمایش کاوشگر در WebView"""
        self._open_callback = open_callback
        self._start_server()

        backend = _detect_backend()
        url = f'http://127.0.0.1:{self._port}/explorer'

        if backend == "cef":
            import cefpython3 as cef # type: ignore
            try: cef.Initialize()
            except TypeError: cef.Initialize(settings={"multi_threaded_message_loop": False})
            cef.CreateBrowserSync(url=url, window_title="آزمایشگاه مجازی")
            cef.MessageLoop()
            cef.Shutdown()

        elif backend == "webview":
            import webview
            webview.create_window("آزمایشگاه مجازی", url=url, width=1200, height=800)
            webview.start()

        else:
            import webbrowser
            webbrowser.open(url)


# ===== HTML صفحه اصلی =====
FONT_CSS = get_font_css()


EXPLORER_HTML = f'''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, maximum-scale=1.0">
<title>آزمایشگاه مجازی</title>
<style>
{FONT_CSS}

:root {{
  --bg: #06060f;
  --surface: rgba(255,255,255,0.025);
  --surface-hover: rgba(233,69,96,0.06);
  --border: rgba(255,255,255,0.05);
  --text: #e6e6ef;
  --text-secondary: #7e7e9a;
  --accent: #e94560;
  --accent-light: #ff6b81;
  --accent-glow: rgba(233,69,96,0.2);
  --math: #5dade2;
  --phys: #e74c3c;
  --chem: #2ecc71;
  --bio: #af7ac5;
  --radius: 16px;
  --radius-sm: 10px;
  --padding: 28px;
  --transition: 0.3s cubic-bezier(0.25, 0.8, 0.25, 1.2);
}}

* {{ margin:0; padding:0; box-sizing:border-box }}

body {{
  font-family: 'B Nazanin', Tahoma, sans-serif;
  background: var(--bg);
  background-image:
    radial-gradient(ellipse at 15% 50%, rgba(233,69,96,0.04) 0%, transparent 60%),
    radial-gradient(ellipse at 85% 30%, rgba(15,52,96,0.06) 0%, transparent 60%),
    radial-gradient(ellipse at 50% 100%, rgba(46,204,113,0.03) 0%, transparent 50%);
  color: var(--text);
  min-height: 100vh;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

.header {{
  background: rgba(6,6,15,0.85);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  padding: 32px var(--padding) 28px;
  text-align: center;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}}

.header h1 {{
  font-size: clamp(26px, 5vw, 40px);
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent), var(--accent-light), #ff8fa3);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 6px;
  letter-spacing: -0.5px;
}}

.header .stats {{
  font-size: clamp(13px, 2.2vw, 16px);
  color: var(--text-secondary);
}}

.header .stats strong {{
  color: var(--accent-light);
  font-weight: 800;
  font-size: clamp(18px, 3vw, 24px);
}}

.filters {{
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 20px var(--padding) 0;
  flex-wrap: wrap;
}}

.filter-group {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
}}

.filter-btn {{
  padding: 9px 18px;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
  border-radius: 50px;
  cursor: pointer;
  font-size: clamp(12px, 2vw, 15px);
  font-weight: 500;
  transition: all var(--transition);
  font-family: 'B Nazanin', Tahoma, sans-serif;
  white-space: nowrap;
  backdrop-filter: blur(8px);
  -webkit-tap-highlight-color: transparent;
}}

.filter-btn:hover {{
  background: rgba(255,255,255,0.05);
  color: var(--text);
  transform: translateY(-1px);
  border-color: rgba(255,255,255,0.12);
}}

.filter-btn:active {{
  transform: scale(0.96);
}}

.filter-btn.active {{
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  box-shadow: 0 4px 16px var(--accent-glow);
  font-weight: 700;
}}

.search-box {{
  text-align: center;
  padding: 18px var(--padding) 0;
}}

.search-box input {{
  width: 100%;
  max-width: 520px;
  padding: 14px 26px;
  border-radius: 50px;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: clamp(14px, 2.2vw, 17px);
  outline: none;
  transition: all 0.3s ease;
  font-family: 'B Nazanin', Tahoma, sans-serif;
  backdrop-filter: blur(8px);
}}

.search-box input::placeholder {{ color: #4a4a5e; font-size: clamp(13px, 2vw, 15px); }}

.search-box input:focus {{
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
  background: rgba(255,255,255,0.04);
}}

.labs-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
  gap: 20px;
  padding: 24px var(--padding) var(--padding);
}}

.lab-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  cursor: pointer;
  transition: all var(--transition);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(8px);
  -webkit-tap-highlight-color: transparent;
}}

.lab-card::after {{
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at var(--mx, 50%) var(--my, 50%), rgba(255,255,255,0.06) 0%, transparent 60%);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}}

.lab-card:hover::after {{
  opacity: 1;
}}

.lab-card:hover {{
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(233,69,96,0.15);
  border-color: rgba(233,69,96,0.25);
  background: var(--surface-hover);
}}

.lab-card:active {{
  transform: scale(0.98);
}}

.lab-card .badge {{
  position: absolute;
  top: 16px;
  right: 16px;
  padding: 6px 14px;
  border-radius: 50px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.3px;
  backdrop-filter: blur(4px);
}}

.b-MATH {{ background: var(--math); box-shadow: 0 2px 8px rgba(93,173,226,0.3); }}
.b-PHYS {{ background: var(--phys); box-shadow: 0 2px 8px rgba(231,76,60,0.3); }}
.b-CHEM {{ background: var(--chem); box-shadow: 0 2px 8px rgba(46,204,113,0.3); }}
.b-BIO  {{ background: var(--bio); box-shadow: 0 2px 8px rgba(175,122,197,0.3); }}

.lab-card .grade {{
  position: absolute;
  top: 16px;
  left: 16px;
  padding: 6px 10px;
  border-radius: 50px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary);
}}

.lab-card h3 {{
  margin-top: 34px;
  font-size: clamp(15px, 2.5vw, 18px);
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
  line-height: 1.5;
}}

.lab-card .info {{
  font-size: clamp(11px, 1.8vw, 13px);
  color: var(--text-secondary);
  display: flex;
  gap: 12px;
  align-items: center;
}}

.no-results {{
  text-align: center;
  padding: 80px var(--padding);
  color: #4a4a5e;
  font-size: clamp(16px, 3vw, 20px);
  font-weight: 500;
}}

@media (max-width: 600px) {{
  .labs-grid {{ grid-template-columns: 1fr; padding: 16px; }}
  .header {{ padding: 20px 16px; }}
  .filters {{ padding: 12px 8px; gap: 6px; }}
  .filter-btn {{ padding: 7px 12px; }}
  .lab-card {{ padding: 18px; }}
}}

::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.08); border-radius: 2px; }}
::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.15); }}
</style>
</head>
<body>

<div class="header">
<h1>🔬 آزمایشگاه مجازی</h1>
<div class="stats"><strong id="count">۰</strong> شبیه‌ساز تعاملی - فیزیک · شیمی · ریاضی · زیست</div>
</div>

<div class="filters">
<div class="filter-group" id="grade-filters"><button class="filter-btn active" onclick="filter('grade','all',this)">📚 همه مقاطع</button></div>
<div class="filter-group" id="subject-filters"><button class="filter-btn active" onclick="filter('subject','all',this)">📖 همه درس‌ها</button></div>
</div>

<div class="search-box"><input type="text" id="search" placeholder="🔍 جستجو به فارسی یا انگلیسی..." oninput="render()"></div>
<div class="labs-grid" id="grid"><div class="no-results">⏳ در حال بارگذاری...</div></div>

<script>
const PERSIAN={json.dumps(PERSIAN_NAMES, ensure_ascii=False)};
const SL={{'MATH':'ریاضی','PHYS':'فیزیک','CHEM':'شیمی','BIO':'زیست'}};
const GL={{'G7':'هفتم','G8':'هشتم','G9':'نهم','G10':'دهم','G11':'یازدهم','G12':'دوازدهم','ACA':'دانشگاهی'}};
const GO=['G7','G8','G9','G10','G11','G12','ACA'];
const SO=['MATH','PHYS','CHEM','BIO'];
let labs=[],g='all',s='all';

function pname(n){{return PERSIAN[n]||n.replace(/-/g,' ')}}

async function init(){{
try{{
let r=await fetch('/api/labs');labs=await r.json();
document.getElementById('count').textContent=labs.length;
let gf=document.getElementById('grade-filters'),sf=document.getElementById('subject-filters');
GO.forEach(x=>{{let c=labs.filter(l=>l.grade===x).length;if(c){{let b=document.createElement('button');b.className='filter-btn';b.textContent=GL[x]+' ('+c+')';b.onclick=()=>filter('grade',x,b);gf.appendChild(b)}}}});
SO.forEach(x=>{{let c=labs.filter(l=>l.subject===x).length;if(c){{let b=document.createElement('button');b.className='filter-btn';b.textContent=SL[x]+' ('+c+')';b.onclick=()=>filter('subject',x,b);sf.appendChild(b)}}}});
render();
}}catch(e){{document.getElementById('grid').innerHTML='<div class="no-results">⚠️ خطا در بارگذاری</div>'}}
}}

function filter(type,val,btn){{
if(type==='grade'){{g=val;document.querySelectorAll('#grade-filters .filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active')}}
else{{s=val;document.querySelectorAll('#subject-filters .filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active')}}
render()
}}

function render(){{
let q=document.getElementById('search').value.toLowerCase();
let f=labs.filter(l=>{{
  if(g!=='all'&&l.grade!==g) return false;
  if(s!=='all'&&l.subject!==s) return false;
  if(!q) return true;
  let pn=pname(l.name).toLowerCase();
  let en=l.name.replace(/-/g,' ').toLowerCase();
  return pn.includes(q) || en.includes(q) || l.name.toLowerCase().includes(q);
}});
let grid=document.getElementById('grid');
if(!f.length){{grid.innerHTML='<div class="no-results">😔 شبیه‌سازی یافت نشد</div>';return}}
grid.innerHTML=f.map(l=>`<div class="lab-card" onclick="openLab('${{l.name}}','${{l.grade}}','${{l.subject}}')" onmousemove="this.style.setProperty('--mx','${{event.offsetX}}px');this.style.setProperty('--my','${{event.offsetY}}px')">
<span class="badge b-${{l.subject}}">${{SL[l.subject]}}</span>
<span class="grade">${{GL[l.grade]||l.grade}}</span>
<h3>${{pname(l.name)}}</h3>
<div class="info"><span>📖 ${{SL[l.subject]}}</span><span>🎓 ${{GL[l.grade]||l.grade}}</span></div>
</div>`).join('')
}}

function openLab(n,g,s){{fetch('/open?name='+n+'&grade='+g+'&subject='+s)}}

init();
</script>
</body>
</html>'''


# ===== LabManager (ساده شده) =====

class LabManager:
    def __init__(self, build_dir=None):
        if build_dir is None:
            build_dir = Path(__file__).resolve().parent.parent / "build"
        self._api = PhETLabAPI(build_dir)
        self._explorer = LabExplorer(self._api)

    def show_explorer(self):
        """نمایش صفحه کاوشگر آزمایشگاه‌ها"""
        self._explorer.show(open_callback=self.open_lab)

    def open_lab(self, sim_name, grade, subject, locale="fa"):
        """باز کردن یک آزمایشگاه"""
        backend = _detect_backend()
        html = self._api.get_lab(sim_name, grade, subject)
        if not html: return

        import threading, socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]

        class LabHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(html.encode('utf-8'))
                except: pass
            def log_message(self, f, *a): pass

        server = HTTPServer(('127.0.0.1', port), LabHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        url = f'http://127.0.0.1:{port}/?locale={locale}'

        if backend == "cef":
            import cefpython3 as cef # type: ignore
            try: cef.Initialize()
            except TypeError: cef.Initialize(settings={"multi_threaded_message_loop": False})
            cef.CreateBrowserSync(url=url, window_title=sim_name)
            cef.MessageLoop()
            cef.Shutdown()

        elif backend == "webview":
            import webview
            webview.create_window(sim_name, url=url, width=1024, height=768)
            webview.start()

        else:
            import webbrowser
            webbrowser.open(url)

    def run(self):
        """اجرای کاوشگر (blocking)"""
        self.show_explorer()
