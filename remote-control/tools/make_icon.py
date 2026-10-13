"""Create a Windows shell icon as part of CI/build; no binary icon is required in Git."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tray_visual import make_tray_icon

folder = ROOT / 'assets'
folder.mkdir(exist_ok=True)
png = folder / 'yeon-managed.png'
ico = folder / 'yeon-managed.ico'
image = make_tray_icon(False, 256)
image.save(png)
image.save(ico, format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f"ICON GENERATED: {ico}")
