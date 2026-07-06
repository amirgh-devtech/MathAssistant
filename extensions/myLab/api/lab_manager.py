# myLab/api/lab_manager.py
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
            import cefpython3  # type: ignore
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
        self._open_callback = None  # اضافه کردن مقداردهی اولیه

    def _start_server(self):
        """شروع HTTP سرور برای سرو HTML"""
        import socket
        import threading

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            self._port = s.getsockname()[1]

        explorer = self  # ذخیره reference برای استفاده در Handler

        class Handler(SimpleHTTPRequestHandler):
            def do_GET(handler_self):
                try:
                    if handler_self.path == '/' or handler_self.path == '/explorer':
                        handler_self._serve_html()
                    elif handler_self.path.startswith('/api/labs'):
                        handler_self._serve_json()
                    elif handler_self.path.startswith('/open'):
                        handler_self._handle_open()
                    else:
                        handler_self.send_response(404)
                        handler_self.end_headers()
                except Exception as e:
                    logger.error(f"Error handling request: {e}")

            def _serve_html(handler_self):
                handler_self.send_response(200)
                handler_self.send_header('Content-Type', 'text/html; charset=utf-8')
                handler_self.end_headers()
                handler_self.wfile.write(EXPLORER_HTML.encode('utf-8'))

            def _serve_json(handler_self):
                handler_self.send_response(200)
                handler_self.send_header('Content-Type', 'application/json; charset=utf-8')
                handler_self.end_headers()
                handler_self.wfile.write(json.dumps(explorer._labs, ensure_ascii=False).encode('utf-8'))

            def _handle_open(handler_self):
                from urllib.parse import urlparse, parse_qs
                params = parse_qs(urlparse(handler_self.path).query)
                name = params.get('name', [''])[0]
                grade = params.get('grade', [''])[0]
                subject = params.get('subject', [''])[0]

                if name and grade and subject and explorer._open_callback:
                    explorer._open_callback(name, grade, subject)
                    handler_self.send_response(200)
                    handler_self.send_header('Content-Type', 'application/json')
                    handler_self.end_headers()
                    handler_self.wfile.write(b'{"status":"ok"}')
                else:
                    handler_self.send_response(400)
                    handler_self.send_header('Content-Type', 'application/json')
                    handler_self.end_headers()
                    handler_self.wfile.write(b'{"status":"error","message":"Missing parameters"}')

            def log_message(handler_self, format, *args):
                pass

        self._server = HTTPServer(('127.0.0.1', self._port), Handler)
        server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        server_thread.start()

    def show(self, open_callback):
        """نمایش کاوشگر در WebView"""
        self._open_callback = open_callback
        self._start_server()

        backend = _detect_backend()
        url = f'http://127.0.0.1:{self._port}/explorer'

        if backend == "cef":
            import cefpython3 as cef  # type: ignore
            try:
                cef.Initialize()
            except TypeError:
                cef.Initialize(settings={"multi_threaded_message_loop": False})
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

    def __del__(self):
        """پاکسازی سرور هنگام حذف شیء"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()


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
  --board: #223229;
  --board-dark: #17221b;
  --chalk: #f4efe1;
  --chalk-dim: #aab8ac;
  --chalk-faint: rgba(244,239,225,0.5);
  --cork: #9c7748;
  --cork-dark: #7a5c37;
  --cork-light: #b78c56;
  --card: #f2ead6;
  --card-line: rgba(70,90,120,0.16);
  --ink: #33302a;
  --ink-dim: #6b6455;
  --pin-brass: #d9ab5e;
  --pin-shadow: #6e4a1c;
  --tape: rgba(230,210,150,0.55);
  --math: #4f83b0;
  --phys: #bb5136;
  --chem: #4f8f63;
  --bio: #8a5f8c;
  --radius: 3px;
}}

* {{ margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color: transparent; }}

html {{ scroll-behavior: smooth; }}

body {{
  font-family: 'Vazirmatn', Tahoma, sans-serif;
  background:
    repeating-linear-gradient(0deg, transparent 0 38px, rgba(255,255,255,0.025) 39px),
    repeating-linear-gradient(90deg, transparent 0 38px, rgba(255,255,255,0.025) 39px),
    radial-gradient(ellipse at 50% 0%, rgba(255,255,255,0.05), transparent 55%),
    var(--board);
  color: var(--chalk);
  min-height: 100vh;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

/* ---------- hanging sign header ---------- */
.sign-wrap {{
  position: relative;
  padding-top: 34px;
  display: flex;
  justify-content: center;
}}
.sign-wrap::before,
.sign-wrap::after {{
  content:'';
  position:absolute;
  top:0;
  width:1px;
  height:34px;
  background: rgba(244,239,225,0.35);
}}
.sign-wrap::before {{ left: calc(50% - 90px); }}
.sign-wrap::after {{ left: calc(50% + 90px); }}

.header {{
  background: linear-gradient(180deg, var(--cork-light), var(--cork) 40%, var(--cork-dark));
  border: 1px solid rgba(0,0,0,0.25);
  border-radius: 6px;
  padding: 22px 44px 20px;
  text-align: center;
  box-shadow: 0 14px 26px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.15);
  position: sticky;
  top: 14px;
  z-index: 10;
  transform: rotate(-0.4deg);
}}
.header::before, .header::after {{
  content:'';
  position:absolute;
  top: 9px;
  width:9px; height:9px;
  border-radius:50%;
  background: radial-gradient(circle at 35% 30%, #e6c98a, #8a6a30 70%, #5a4118);
  box-shadow: 0 1px 2px rgba(0,0,0,0.6);
}}
.header::before {{ left: 14px; }}
.header::after {{ right: 14px; }}

.header h1 {{
  font-size: clamp(24px, 4.6vw, 36px);
  font-weight: 800;
  color: var(--chalk);
  text-shadow: 0 0 2px rgba(255,255,255,0.35), 0 2px 3px rgba(0,0,0,0.35);
  letter-spacing: 0.5px;
  margin-bottom: 5px;
}}

.header .stats {{
  font-size: clamp(12px, 2vw, 15px);
  color: rgba(244,239,225,0.75);
}}
.header .stats strong {{
  color: var(--chalk);
  font-weight: 800;
  font-size: clamp(16px, 2.6vw, 20px);
}}

/* ---------- filters as chalk tabs ---------- */
.filters {{
  display: flex;
  gap: 22px;
  justify-content: center;
  padding: 26px 24px 0;
  flex-wrap: wrap;
}}

.filter-group {{
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: center;
  border-bottom: 1px dashed rgba(244,239,225,0.2);
  padding-bottom: 10px;
}}

.filter-btn {{
  padding: 7px 14px;
  border: none;
  background: transparent;
  color: var(--chalk-dim);
  cursor: pointer;
  font-size: clamp(12px, 1.9vw, 14.5px);
  font-weight: 600;
  font-family: 'Vazirmatn', Tahoma, sans-serif;
  white-space: nowrap;
  position: relative;
  border-radius: 3px;
  transition: color .2s ease, background .2s ease;
}}
.filter-btn:hover {{ color: var(--chalk); background: rgba(244,239,225,0.06); }}
.filter-btn:active {{ transform: scale(0.96); }}
.filter-btn.active {{
  color: var(--chalk);
}}
.filter-btn.active::after {{
  content:'';
  position:absolute;
  left:12px; right:12px; bottom:-11px;
  height:2px;
  background: var(--chalk);
  box-shadow: 0 0 6px rgba(244,239,225,0.6);
  border-radius: 2px;
}}

/* ---------- search: taped index card ---------- */
.search-box {{
  display:flex;
  justify-content:center;
  padding: 30px 24px 6px;
}}
.search-inner {{
  position: relative;
  width: 100%;
  max-width: 480px;
  transform: rotate(-0.6deg);
}}
.search-inner::before {{
  content:'';
  position:absolute;
  top:-8px; left: 20px;
  width: 46px; height: 16px;
  background: var(--tape);
  border: 1px solid rgba(0,0,0,0.05);
  transform: rotate(-4deg);
  box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}}
.search-inner::after {{
  content:'';
  position:absolute;
  top:-8px; right: 20px;
  width: 46px; height: 16px;
  background: var(--tape);
  border: 1px solid rgba(0,0,0,0.05);
  transform: rotate(3deg);
  box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}}
.search-box input {{
  width: 100%;
  padding: 13px 20px;
  border-radius: 2px;
  border: none;
  background: var(--card);
  background-image: repeating-linear-gradient(to bottom, transparent 0 25px, var(--card-line) 26px);
  color: var(--ink);
  font-size: clamp(13px, 2vw, 15.5px);
  outline: none;
  font-family: 'Vazirmatn', Tahoma, sans-serif;
  box-shadow: 0 8px 16px rgba(0,0,0,0.3);
}}
.search-box input::placeholder {{ color: var(--ink-dim); }}
.search-box input:focus {{ box-shadow: 0 8px 20px rgba(0,0,0,0.35), 0 0 0 2px var(--pin-brass); }}

/* ---------- grid of pinned index cards ---------- */
.labs-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr));
  gap: 34px 22px;
  padding: 42px 26px 60px;
  max-width: 1280px;
  margin: 0 auto;
}}

.lab-card {{
  background: var(--card);
  background-image: repeating-linear-gradient(to bottom, transparent 0 24px, var(--card-line) 25px);
  border-radius: var(--radius);
  padding: 26px 18px 16px;
  cursor: pointer;
  position: relative;
  color: var(--ink);
  border-right: 3px solid rgba(187,81,54,0.25);
  box-shadow: 0 8px 16px rgba(0,0,0,0.35), 0 1px 0 rgba(255,255,255,0.5) inset;
  transform: rotate(var(--tilt, 0deg));
  transition: transform .3s cubic-bezier(.25,.8,.25,1.25), box-shadow .3s ease;
}}

.lab-card:hover {{
  transform: rotate(0deg) translateY(-7px);
  box-shadow: 0 20px 30px rgba(0,0,0,0.45), 0 1px 0 rgba(255,255,255,0.5) inset;
  z-index: 3;
}}
.lab-card:active {{ transform: rotate(0deg) translateY(-3px) scale(0.98); }}

.lab-card::before {{
  content:'';
  position:absolute;
  top:-9px; left:50%;
  transform: translateX(-50%);
  width:15px; height:15px;
  border-radius:50%;
  background: radial-gradient(circle at 34% 30%, #f4dca0, var(--pin-brass) 55%, var(--pin-shadow) 100%);
  box-shadow: 0 3px 4px rgba(0,0,0,0.5);
  z-index: 2;
}}

.lab-card .badge {{
  position: absolute;
  top: -10px;
  right: 10px;
  width: 34px; height: 34px;
  border-radius: 50%;
  display:flex; align-items:center; justify-content:center;
  font-size: 11px;
  font-weight: 800;
  color: #fff;
  text-shadow: 0 1px 1px rgba(0,0,0,0.25);
  box-shadow: 0 3px 6px rgba(0,0,0,0.35), inset 0 1px 1px rgba(255,255,255,0.3);
  border: 2px solid rgba(255,255,255,0.15);
}}

.b-MATH {{ background: radial-gradient(circle at 35% 30%, #7aa9cf, var(--math)); }}
.b-PHYS {{ background: radial-gradient(circle at 35% 30%, #d97b5e, var(--phys)); }}
.b-CHEM {{ background: radial-gradient(circle at 35% 30%, #79b98d, var(--chem)); }}
.b-BIO  {{ background: radial-gradient(circle at 35% 30%, #ac82ad, var(--bio)); }}

.lab-card .grade {{
  display: inline-block;
  margin-top: 2px;
  padding: 2px 9px;
  border: 1px dashed var(--ink-dim);
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-dim);
}}

.lab-card h3 {{
  margin-top: 12px;
  font-size: clamp(14.5px, 2.3vw, 17px);
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 10px;
  line-height: 1.5;
}}

.lab-card .info {{
  font-size: clamp(11px, 1.7vw, 12.5px);
  color: var(--ink-dim);
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}}

.no-results {{
  grid-column: 1 / -1;
  text-align: center;
  padding: 90px 24px;
  color: var(--chalk-dim);
  font-size: clamp(15px, 3vw, 19px);
  font-weight: 600;
}}

@media (max-width: 600px) {{
  .labs-grid {{ grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); gap: 30px 14px; padding: 34px 14px 40px; }}
  .header {{ padding: 18px 26px 16px; }}
  .filters {{ gap: 14px; padding: 18px 10px 0; }}
}}

::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(244,239,225,0.15); border-radius: 2px; }}
</style>
</head>
<body>

<div class="sign-wrap">
  <div class="header">
    <h1>🔬 آزمایشگاه مجازی</h1>
    <div class="stats"><strong id="count">۰</strong> شبیه‌ساز تعاملی — فیزیک · شیمی · ریاضی · زیست</div>
  </div>
</div>

<div class="filters">
<div class="filter-group" id="grade-filters"><button class="filter-btn active" onclick="filter('grade','all',this)">همه مقاطع</button></div>
<div class="filter-group" id="subject-filters"><button class="filter-btn active" onclick="filter('subject','all',this)">همه درس‌ها</button></div>
</div>

<div class="search-box"><div class="search-inner"><input type="text" id="search" placeholder="جستجو به فارسی یا انگلیسی…" oninput="render()"></div></div>
<div class="labs-grid" id="grid"><div class="no-results">در حال بارگذاری…</div></div>

<script>
const PERSIAN=JSON.parse('{json.dumps(PERSIAN_NAMES, ensure_ascii=False)}');
const SL={{'MATH':'ریاضی','PHYS':'فیزیک','CHEM':'شیمی','BIO':'زیست'}};
const GL={{'G7':'هفتم','G8':'هشتم','G9':'نهم','G10':'دهم','G11':'یازدهم','G12':'دوازدهم','ACA':'دانشگاهی'}};
const GO=['G7','G8','G9','G10','G11','G12','ACA'];
const SO=['MATH','PHYS','CHEM','BIO'];
let labs=[];
let g='all',s='all';

function pname(n){{return PERSIAN[n]||n.replace(/-/g,' ')}}

function tilt(name){{
  let h=0; for(let i=0;i<name.length;i++) h=(h*31+name.charCodeAt(i))>>>0;
  return ((h%70)/10-3.5).toFixed(2);
}}

async function loadLabs(){{
  try{{
    const res=await fetch('/api/labs');
    labs=await res.json();
    document.getElementById('count').textContent=labs.length;
    initFilters();
    render();
  }}catch(e){{
    console.error('Error loading labs:',e);
    document.getElementById('grid').innerHTML='<div class="no-results">خطا در بارگذاری شبیه‌سازها</div>';
  }}
}}

function initFilters(){{
  let gf=document.getElementById('grade-filters'),sf=document.getElementById('subject-filters');
  // پاک کردن فیلترهای قبلی (به جز دکمه "همه")
  while(gf.children.length>1) gf.removeChild(gf.lastChild);
  while(sf.children.length>1) sf.removeChild(sf.lastChild);

  GO.forEach(x=>{{
    let c=labs.filter(l=>l.grade===x).length;
    if(c){{
      let b=document.createElement('button');
      b.className='filter-btn';
      b.textContent=GL[x]+' ('+c+')';
      b.onclick=()=>filter('grade',x,b);
      gf.appendChild(b);
    }}
  }});
  SO.forEach(x=>{{
    let c=labs.filter(l=>l.subject===x).length;
    if(c){{
      let b=document.createElement('button');
      b.className='filter-btn';
      b.textContent=SL[x]+' ('+c+')';
      b.onclick=()=>filter('subject',x,b);
      sf.appendChild(b);
    }}
  }});
}}

function filter(type,val,btn){{
  if(type==='grade'){{
    g=val;
    document.querySelectorAll('#grade-filters .filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
  }}else{{
    s=val;
    document.querySelectorAll('#subject-filters .filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
  }}
  render();
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
  if(!f.length){{grid.innerHTML='<div class="no-results">شبیه‌سازی یافت نشد</div>';return}}
  grid.innerHTML=f.map(l=>`<div class="lab-card" style="--tilt:${{tilt(l.name)}}deg" onclick="openLab('${{l.name}}','${{l.grade}}','${{l.subject}}')">
<span class="badge b-${{l.subject}}">${{SL[l.subject]}}</span>
<span class="grade">${{GL[l.grade]||l.grade}}</span>
<h3>${{pname(l.name)}}</h3>
<div class="info"><span>📖 ${{SL[l.subject]}}</span><span>🎓 ${{GL[l.grade]||l.grade}}</span></div>
</div>`).join('');
}}

function openLab(n,g,s){{fetch('/open?name='+encodeURIComponent(n)+'&grade='+encodeURIComponent(g)+'&subject='+encodeURIComponent(s))}}

// شروع برنامه
loadLabs();
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
        self._lab_servers = []  # نگهداری رفرنس سرورهای آزمایشگاه

    def show_explorer(self):
        """نمایش صفحه کاوشگر آزمایشگاه‌ها"""
        self._explorer.show(open_callback=self.open_lab)

    def open_lab(self, sim_name, grade, subject, locale="fa"):
        """باز کردن یک آزمایشگاه"""
        backend = _detect_backend()
        html = self._api.get_lab(sim_name, grade, subject)
        if not html:
            logger.error(f"Failed to get lab: {sim_name}")
            return

        import threading
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]

        class LabHandler(SimpleHTTPRequestHandler):
            def do_GET(handler_self):
                try:
                    handler_self.send_response(200)
                    handler_self.send_header('Content-Type', 'text/html; charset=utf-8')
                    handler_self.end_headers()
                    handler_self.wfile.write(html.encode('utf-8'))
                except Exception as e:
                    logger.error(f"Error serving lab: {e}")

            def log_message(handler_self, f, *a):
                pass

        server = HTTPServer(('127.0.0.1', port), LabHandler)
        self._lab_servers.append(server)  # نگهداری رفرنس سرور

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        url = f'http://127.0.0.1:{port}/?locale={locale}'

        if backend == "cef":
            import cefpython3 as cef  # type: ignore
            try:
                cef.Initialize()
            except TypeError:
                cef.Initialize(settings={"multi_threaded_message_loop": False})
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

    def __del__(self):
        """پاکسازی سرورها"""
        for server in self._lab_servers:
            try:
                server.shutdown()
                server.server_close()
            except:
                pass
