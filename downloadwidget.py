import sys
from PySide6 import QtCore
from PySide6.QtCore import QDir, QFileInfo, QStandardPaths, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMenu, QProgressBar, QStyleFactory
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest


# A QProgressBar with context menu for displaying downloads in a QStatusBar.
class DownloadWidget(QProgressBar):
    """Lets you track progress of a QWebEngineDownloadRequest."""
    finished = QtCore.Signal()
    remove_requested = QtCore.Signal()

    def __init__(self, download_item):
        super().__init__()
        self._download_item = download_item
        download_item.finished.connect(self._finished)
        download_item.downloadProgress.connect(self._downloadProgress)
        download_item.stateChanged.connect(self._updateToolTip())
        path = download_item.path()
        self.setMaximumWidth(300)
        # Shorten 'PySide6-5.11.0a1-5.11.0-cp36-cp36m-linux_x86_64.whl'...
        description = QFileInfo(path).fileName()
        description_length = len(description)
        if description_length > 30:
            description_ini = description[0:10]
            description_end = description[description_length - 10:]
            description = f'{description_ini}...{description_end}'
        self.setFormat(f'{description} %p%')
        self.setOrientation(Qt.Horizontal)
        self.setMinimum(0)
        self.setValue(0)
        self.setMaximum(100)
        self._updateToolTip()
        # Force progress bar text to be shown on macoS by using 'fusion' style
        if sys.platform == 'darwin':
            self.setStyle(QStyleFactory.create('fusion'))

    @staticmethod
    def openFile(file):
        QDesktopServices.openUrl(QUrl.fromLocalFile(file))

    @staticmethod
    def openDownloadDirectory():
        path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        DownloadWidget.openFile(path)

    def state(self):
        return self._download_item.state()

    def _updateToolTip(self):
        path = self._download_item.path()
        url_str = self._download_item.url().toString()
        native_sep = QDir.toNativeSeparators(path)
        tool_tip = f"{url_str}\n{native_sep}"
        total_bytes = self._download_item.totalBytes()
        if total_bytes > 0:
            tool_tip += f"\n{total_bytes / 1024}K"
        state = self.state()
        if state == QWebEngineDownloadRequest.DownloadRequested:
            tool_tip += "\n(requested)"
        elif state == QWebEngineDownloadRequest.DownloadInProgress:
            tool_tip += "\n(downloading)"
        elif state == QWebEngineDownloadRequest.DownloadCompleted:
            tool_tip += "\n(completed)"
        elif state == QWebEngineDownloadRequest.DownloadCancelled:
            tool_tip += "\n(cancelled)"
        else:
            tool_tip += "\n(interrupted)"
        self.setToolTip(tool_tip)

    def _downloadProgress(self, bytes_received, bytes_total):
        self.setValue(int(100 * bytes_received / bytes_total))

    def _finished(self):
        self._updateToolTip()
        self.finished.emit()

    def _launch(self):
        DownloadWidget.openFile(self._download_item.path())

    def mouseDoubleClickEvent(self, event):
        if self.state() == QWebEngineDownloadRequest.DownloadCompleted:
            self._launch()

    def contextMenuEvent(self, event):
        state = self.state()
        context_menu = QMenu()
        launch_action = context_menu.addAction("Launch")
        launch_action.setEnabled(state == QWebEngineDownloadRequest.DownloadCompleted)
        show_in_folder_action = context_menu.addAction("Show in Folder")
        show_in_folder_action.setEnabled(state == QWebEngineDownloadRequest.DownloadCompleted)
        cancel_action = context_menu.addAction("Cancel")
        cancel_action.setEnabled(state == QWebEngineDownloadRequest.DownloadInProgress)
        remove_action = context_menu.addAction("Remove")
        remove_action.setEnabled(state != QWebEngineDownloadRequest.DownloadInProgress)

        chosen_action = context_menu.exec(event.globalPos())
        if chosen_action == launch_action:
            self._launch()
        elif chosen_action == show_in_folder_action:
            path = QFileInfo(self._download_item.path()).absolutePath()
            DownloadWidget.openFile(path)
        elif chosen_action == cancel_action:
            self._download_item.cancel()
        elif chosen_action == remove_action:
            self.remove_requested.emit()