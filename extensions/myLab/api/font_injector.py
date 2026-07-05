# myLab/api/font_injector.py
"""تبدیل فونت B Nazanin به base64 برای تزریق در HTML"""
import base64
from pathlib import Path

def get_font_base64(font_path: str = None) -> str:
    """دریافت base64 فونت B Nazanin"""
    if font_path is None:
        # مسیر پیش‌فرض - فونت رو بذار کنار همین فایل
        font_path = Path(__file__).parent / "assets" / "BNazanin.ttf"

    with open(font_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_font_css() -> str:
    """دریافت CSS کامل برای تزریق فونت"""
    font_base64 = get_font_base64()
    return f'''@font-face {{
    font-family: 'B Nazanin';
    src: url(data:font/ttf;base64,{font_base64}) format('truetype');
    font-weight: normal;
    font-style: normal;
}}
body, h1, h2, h3, h4, h5, h6, p, span, button, input, div, a, li, td, th, label, .font-bn {{
    font-family: 'B Nazanin', Tahoma, sans-serif !important;
}}'''
