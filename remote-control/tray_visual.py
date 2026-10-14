"""Use the supplied YEON artwork with a visible tray sharing-status dot."""
from pathlib import Path
from PIL import Image, ImageDraw
VERSION = '1.3.6'

def make_tray_icon(sharing: bool, size: int=64) -> Image.Image:
    if size < 32:
        raise ValueError('Icon size must be at least 32')
    path = Path(__file__).resolve().parent / 'assets' / 'yeon-managed.png'
    image = Image.open(path).convert('RGBA').resize((size, size), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    c = round(size * .80)
    r = max(4, round(size * .095))
    draw.ellipse((c-r-2,c-r-2,c+r+2,c+r+2),fill='#06112c')
    draw.ellipse((c-r,c-r,c+r,c+r),fill='#22c55e' if sharing else '#94a3b8',outline='white',width=max(1,size//64))
    return image

def status_title(sharing: bool) -> str:
    return 'YEON 관리 대상 - 화면 공유 중' if sharing else 'YEON 관리 대상 - 공유 중지됨'
