"""System tray icon using pystray + Pillow."""
import threading
import pystray
from PIL import Image, ImageDraw


def _build_icon_image() -> Image.Image:
    """Generate a 64x64 purple mic icon programmatically."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Purple circle background
    d.ellipse([2, 2, 62, 62], fill="#6e40c9")

    # Mic capsule (rounded rectangle)
    d.rounded_rectangle([24, 10, 40, 34], radius=8, fill="white")

    # Mic stand arc
    d.arc([16, 26, 48, 50], start=0, end=180, fill="white", width=3)

    # Stem + base
    d.line([32, 50, 32, 58], fill="white", width=3)
    d.line([24, 58, 40, 58], fill="white", width=3)

    return img


class TrayIcon:
    """pystray tray icon. Runs in a daemon thread."""

    def __init__(self, on_show, on_quit):
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon = None

    def start(self):
        menu = pystray.Menu(
            pystray.MenuItem("Show Yerrrp", self._handle_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._handle_quit),
        )
        self._icon = pystray.Icon(
            name="Yerrrp",
            icon=_build_icon_image(),
            title="Yerrrp",
            menu=menu,
        )
        t = threading.Thread(target=self._icon.run, daemon=True)
        t.start()

    def stop(self):
        if self._icon:
            self._icon.stop()
            self._icon = None

    def _handle_show(self, icon, item):
        self._on_show()

    def _handle_quit(self, icon, item):
        self._on_quit()
