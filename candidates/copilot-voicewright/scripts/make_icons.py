"""Regenerate assets/icon.{png,ico,icns} (requires Pillow)."""
from pathlib import Path
from PIL import Image, ImageDraw

S = 1024
root = Path(__file__).resolve().parents[1] / "src" / "voicewright" / "assets"
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
grad = Image.new("RGBA", (S, S))
gd = ImageDraw.Draw(grad)
for y in range(S):
    t = y / S
    gd.line([(0, y), (S, y)], fill=(int(91 + 40 * t), int(91 - 40 * t), int(240 - 30 * t), 255))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([40, 40, S - 40, S - 40], radius=220, fill=255)
img.paste(grad, (0, 0), mask)
d = ImageDraw.Draw(img)
white = (255, 255, 255, 255)
# microphone
d.rounded_rectangle([392, 190, 632, 590], radius=120, fill=white)
d.arc([300, 330, 724, 720], start=0, end=180, fill=white, width=44)
d.rectangle([490, 715, 534, 820], fill=white)
d.rounded_rectangle([380, 800, 644, 846], radius=22, fill=white)
# sound waves
for i, (x, h) in enumerate([(200, 160), (130, 260), (824, 160), (894, 260)]):
    d.rounded_rectangle([x - 18, 470 - h // 2, x + 18, 470 + h // 2], radius=18, fill=(255, 255, 255, 210))
root.mkdir(exist_ok=True)
img.resize((512, 512), Image.LANCZOS).save(root / "icon.png")
img.save(root / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(root / "icon.icns")
print("icons written to", root)
