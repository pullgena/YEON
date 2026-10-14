"""Preserve the user-provided YEON icon; generate a Windows multi-resolution ICO."""
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'assets'
folder.mkdir(exist_ok=True)
png = folder / 'yeon-managed.png'
ico = folder / 'yeon-managed.ico'
image = Image.open(png).convert('RGBA')
image.save(ico, format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f'YEON icon from artwork: {ico}')
