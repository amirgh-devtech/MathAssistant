# myLab/api/font_injector.py
"""تبدیل فونت Vazirmatn به base64 برای تزریق در HTML"""
import base64
from pathlib import Path

def get_font_base64() -> str:
    """دریافت base64 فونت Vazirmatn"""
    base_dir = Path(__file__).parent.parent
    font_path = base_dir / "assets" / "fonts" / "Vazirmatn-Regular.ttf"

    with open(font_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_font_css() -> str:
    """دریافت CSS کامل برای تزریق فونت"""
    font_base64 = get_font_base64()

    return f'''@font-face {{
    font-family: 'Vazirmatn';
    src: url(data:font/truetype;base64,{font_base64}) format('truetype');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}}

@font-face {{
    font-family: 'Vazirmatn';
    src: url(data:font/truetype;base64,{font_base64}) format('truetype');
    font-weight: 700;
    font-style: normal;
    font-display: swap;
}}

body, h1, h2, h3, h4, h5, h6, p, span, button, input, div, a, li, td, th, label,
.font-bn, .font-vazir, .filter-btn, .search-box input, .header, .lab-card,
.header h1, .header .stats, .lab-card h3, .filter-btn, .search-box input,
.header .stats strong, .badge, .grade {{
    font-family: 'Vazirmatn', Tahoma, sans-serif !important;
}}
'''
