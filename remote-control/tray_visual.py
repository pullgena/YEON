"""Draw a visible YEON managed-PC badge for the Windows tray and executable."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


VERSION = "1.2.0"


def make_tray_icon(sharing: bool, size: int = 64) -> Image.Image:
    """Green status marker means sharing; gray means not sharing."""
    if size < 32:
        raise ValueError("Icon size must be at least 32")
    scale = size / 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    def rect(coords, color, radius=0, outline=None, width=1):
        draw.rounded_rectangle(tuple(round(c*scale) for c in coords),
                               radius=round(radius*scale), fill=color,
                               outline=outline, width=max(1,round(width*scale)))
    # Recognizable Y mark on a rounded indigo computer monitor.
    rect((4, 6, 60, 52), "#3730A3", 13, "#C7D2FE", 2)
    rect((11, 13, 53, 44), "#111A39", 7)
    stroke = max(3, round(6*scale))
    draw.line([(round(19*scale),round(21*scale)),(round(32*scale),round(33*scale)),(round(45*scale),round(21*scale))],fill="#E0E7FF",width=stroke,joint="curve")
    draw.line([(round(32*scale),round(32*scale)),(round(32*scale),round(39*scale))],fill="#E0E7FF",width=stroke)
    rect((25, 51, 39, 56), "#C7D2FE", 2)
    rect((18, 56, 46, 60), "#C7D2FE", 2)
    c = round(51*scale); d = round(51*scale); radius = round(11*scale)
    draw.ellipse((c-radius-2,d-radius-2,c+radius+2,d+radius+2),fill="#101528")
    draw.ellipse((c-radius,d-radius,c+radius,d+radius),fill="#22C55E" if sharing else "#94A3B8",outline="#FFFFFF",width=max(1,round(2*scale)))
    return image


def status_title(sharing: bool) -> str:
    return "YEON 관리 대상 - 화면 공유 중" if sharing else "YEON 관리 대상 - 공유 중지됨"
