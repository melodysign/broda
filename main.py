import sys
from bookmarkwidget import BookmarkWidget
from browsertabwidget import BrowserTabWidget
from downloadwidget import DownloadWidget
from findtoolbar import FindToolBar
from webengineview import WebEngineView
from PySide6 import QtCore
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtWidgets import (QApplication, QDockWidget, QLabel,
                               QLineEdit, QMainWindow, QToolBar)
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage

main_windows = []


def createMainWindow():
    """Creates a MainWindow using 75% of the available screen resolution."""
    main_win = MainWindow()
    main_windows.append(main_win)
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() * 3 / 4,
                    available_geometry.height() * 3 / 4)
    main_win.show()
    return main_win


def createMainWindowWithBrowser():
    """Creates a MainWindow with a BrowserTabWidget."""
    main_win = createMainWindow()
    return main_win.addBrowserTab()


class MainWindow(QMainWindow):
    """Provides the parent window that includes the BookmarkWidget,
    BrowserTabWidget, and a DownloadWidget, to offer the complete
    web browsing experience."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle('PySide6 tabbed browser Example')

        self._tab_widget = BrowserTabWidget(createMainWindowWithBrowser)
        self._tab_widget.enabled_changed.connect(self._enabledChanged)
        self._tab_widget.download_requested.connect(self._downloadRequested)
        self.setCentralWidget(self._tab_widget)
        self.connect(self._tab_widget, QtCore.SIGNAL("url_changed(QUrl)"),
                     self.urlChanged)

        self._bookmark_dock = QDockWidget()
        self._bookmark_dock.setWindowTitle('Bookmarks')
        self._bookmark_widget = BookmarkWidget()
        self._bookmark_widget.open_bookmark.connect(self.loadUrl)
        self._bookmark_widget.open_bookmark_in_new_tab.connect(self.loadUrlInNewTab)
        self._bookmark_dock.setWidget(self._bookmark_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._bookmark_dock)

        self._find_tool_bar = None

        self._actions = {}
        self._createMenu()

        self._tool_bar = QToolBar()
        self.addToolBar(self._tool_bar)
        for action in self._actions.values():
            if not action.icon().isNull():
                self._tool_bar.addAction(action)

        self._addres_line_edit = QLineEdit()
        self._addres_line_edit.setClearButtonEnabled(True)
        self._addres_line_edit.returnPressed.connect(self.load)
        self._tool_bar.addWidget(self._addres_line_edit)
        self._zoom_label = QLabel()
        self.statusBar().addPermanentWidget(self._zoom_label)
        self._updateZoomLabel()

        self._bookmarksToolBar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self._bookmarksToolBar)
        self.insertToolBarBreak(self._bookmarksToolBar)
        self._bookmark_widget.changed.connect(self._updateBookmarks)
        self._updateBookmarks()

    def _updateBookmarks(self):
        self._bookmark_widget.populateToolbar(self._bookmarksToolBar)
        self._bookmark_widget.populateOther(self._bookmark_menu, 3)

    def _createMenu(self):
        file_menu = self.menuBar().addMenu("&File")
        exit_action = QAction(QIcon.fromTheme("application-exit"), "E&xit",
                              self, shortcut="Ctrl+Q", triggered=app.quit)
        file_menu.addAction(exit_action)

        navigation_menu = self.menuBar().addMenu("&Navigation")

        style_icons = ':/qt-project.org/styles/commonstyle/images/'
        back_action = QAction(QIcon.fromTheme("go-previous",
                                              QIcon(style_icons + 'left-32.png')),
                              "Back", self,
                              shortcut=QKeySequence(QKeySequence.Back),
                              triggered=self._tab_widget.back)
        self._actions[QWebEnginePage.Back] = back_action
        back_action.setEnabled(False)
        navigation_menu.addAction(back_action)
        forward_action = QAction(QIcon.fromTheme("go-next",
                                                 QIcon(style_icons + 'right-32.png')),
                                 "Forward", self,
                                 shortcut=QKeySequence(QKeySequence.Forward),
                                 triggered=self._tab_widget.forward)
        forward_action.setEnabled(False)
        self._actions[QWebEnginePage.Forward] = forward_action

        navigation_menu.addAction(forward_action)
        reload_action = QAction(QIcon(style_icons + 'refresh-32.png'),
                                "Reload", self,
                                shortcut=QKeySequence(QKeySequence.Refresh),
                                triggered=self._tab_widget.reload)
        self._actions[QWebEnginePage.Reload] = reload_action
        reload_action.setEnabled(False)
        navigation_menu.addAction(reload_action)

        navigation_menu.addSeparator()

        new_tab_action = QAction("New Tab", self,
                                 shortcut='Ctrl+T',
                                 triggered=self.addBrowserTab)
        navigation_menu.addAction(new_tab_action)

        close_tab_action = QAction("Close Current Tab", self,
                                   shortcut="Ctrl+W",
                                   triggered=self._closeCurrentTab)
        navigation_menu.addAction(close_tab_action)

        navigation_menu.addSeparator()

        history_action = QAction("History...", self,
                                 triggered=self._tab_widget.showHistory)
        navigation_menu.addAction(history_action)

        edit_menu = self.menuBar().addMenu("&Edit")

        find_action = QAction("Find", self,
                              shortcut=QKeySequence(QKeySequence.Find),
                              triggered=self._showFind)
        edit_menu.addAction(find_action)

        edit_menu.addSeparator()
        undo_action = QAction("Undo", self,
                              shortcut=QKeySequence(QKeySequence.Undo),
                              triggered=self._tab_widget.undo)
        self._actions[QWebEnginePage.Undo] = undo_action
        undo_action.setEnabled(False)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self,
                              shortcut=QKeySequence(QKeySequence.Redo),
                              triggered=self._tab_widget.redo)
        self._actions[QWebEnginePage.Redo] = redo_action
        redo_action.setEnabled(False)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cut", self,
                             shortcut=QKeySequence(QKeySequence.Cut),
                             triggered=self._tab_widget.cut)
        self._actions[QWebEnginePage.Cut] = cut_action
        cut_action.setEnabled(False)
        edit_menu.addAction(cut_action)

        copy_action = QAction("Copy", self,
                              shortcut=QKeySequence(QKeySequence.Copy),
                              triggered=self._tab_widget.copy)
        self._actions[QWebEnginePage.Copy] = copy_action
        copy_action.setEnabled(False)
        edit_menu.addAction(copy_action)

        paste_action = QAction("Paste", self,
                               shortcut=QKeySequence(QKeySequence.Paste),
                               triggered=self._tab_widget.paste)
        self._actions[QWebEnginePage.Paste] = paste_action
        paste_action.setEnabled(False)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        select_all_action = QAction("Select All", self,
                                    shortcut=QKeySequence(QKeySequence.SelectAll),
                                    triggered=self._tab_widget.selectAll)
        self._actions[QWebEnginePage.SelectAll] = select_all_action
        select_all_action.setEnabled(False)
        edit_menu.addAction(select_all_action)

        self._bookmark_menu = self.menuBar().addMenu("&Bookmarks")
        add_bookmark_action = QAction("&Add Bookmark", self,
                                      triggered=self._addBookmark)
        self._bookmark_menu.addAction(add_bookmark_action)
        add_tool_bar_bookmark_action = QAction("&Add Bookmark to Tool Bar", self,
                                               triggered=self._addToolbarBookmark)
        self._bookmark_menu.addAction(add_tool_bar_bookmark_action)
        self._bookmark_menu.addSeparator()

        tools_menu = self.menuBar().addMenu("&Tools")
        download_action = QAction("Open Downloads", self,
                                  triggered=DownloadWidget.openDownloadDirectory)
        tools_menu.addAction(download_action)

        window_menu = self.menuBar().addMenu("&Window")

        window_menu.addAction(self._bookmark_dock.toggleViewAction())

        window_menu.addSeparator()

        zoom_in_action = QAction(QIcon.fromTheme("zoom-in"),
                                 "Zoom In", self,
                                 shortcut=QKeySequence(QKeySequence.ZoomIn),
                                 triggered=self._zoomIn)
        window_menu.addAction(zoom_in_action)
        zoom_out_action = QAction(QIcon.fromTheme("zoom-out"),
                                  "Zoom Out", self,
                                  shortcut=QKeySequence(QKeySequence.ZoomOut),
                                  triggered=self._zoomOut)
        window_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction(QIcon.fromTheme("zoom-original"),
                                    "Reset Zoom", self,
                                    shortcut="Ctrl+0",
                                    triggered=self._resetZoom)
        window_menu.addAction(reset_zoom_action)

        about_menu = self.menuBar().addMenu("&About")
        about_action = QAction("About Qt", self,
                               shortcut=QKeySequence(QKeySequence.HelpContents),
                               triggered=app.aboutQt)
        about_menu.addAction(about_action)

    def addBrowserTab(self):
        return self._tab_widget.addBrowserTab()

    def _closeCurrentTab(self):
        if self._tab_widget.count() > 1:
            self._tab_widget.closeCurrentTab()
        else:
            self.close()

    def closeEvent(self, event):
        main_windows.remove(self)
        event.accept()

    def load(self):
        url_string = self._addres_line_edit.text().strip()
        if url_string:
            self.loadUrlString(url_string)

    def loadUrlString(self, url_s):
        url = QUrl.fromUserInput(url_s)
        if (url.isValid()):
            self.loadUrl(url)

    def loadUrl(self, url):
        self._tab_widget.load(url)

    def loadUrlInNewTab(self, url):
        self.addBrowserTab().load(url)

    def urlChanged(self, url):
        self._addres_line_edit.setText(url.toString())

    def _enabledChanged(self, web_action, enabled):
        action = self._actions[web_action]
        if action:
            action.setEnabled(enabled)

    def _addBookmark(self):
        index = self._tab_widget.currentIndex()
        if index >= 0:
            url = self._tab_widget.url()
            title = self._tab_widget.tabText(index)
            icon = self._tab_widget.tabIcon(index)
            self._bookmark_widget.add_bookmark(url, title, icon)

    def _addToolbarBookmark(self):
        index = self._tab_widget.currentIndex()
        if index >= 0:
            url = self._tab_widget.url()
            title = self._tab_widget.tabText(index)
            icon = self._tab_widget.tabIcon(index)
            self._bookmark_widget.add_tool_bar_bookmark(url, title, icon)

    def _zoomIn(self):
        new_zoom = self._tab_widget.zoomFactor() * 1.5
        if (new_zoom <= WebEngineView.maximumZoomFactor()):
            self._tab_widget.setZoomFactor(new_zoom)
            self._updateZoomLabel()

    def _zoomOut(self):
        new_zoom = self._tab_widget.zoomFactor() / 1.5
        if (new_zoom >= WebEngineView.minimumZoomFactor()):
            self._tab_widget.setZoomFactor(new_zoom)
            self._updateZoomLabel()

    def _resetZoom(self):
        self._tab_widget.setZoomFactor(1)
        self._updateZoomLabel()

    def _updateZoomLabel(self):
        percent = int(self._tab_widget.zoomFactor() * 100)
        self._zoom_label.setText(f"{percent}%")

    def _downloadRequested(self, item):
        # Remove old downloads before opening a new one
        for old_download in self.statusBar().children():
            if (type(old_download).__name__ == 'DownloadWidget' and
                old_download.state() != QWebEngineDownloadRequest.DownloadInProgress):
                self.statusBar().removeWidget(old_download)
                del old_download

        item.accept()
        download_widget = DownloadWidget(item)
        download_widget.remove_requested.connect(self._removeDownloadRequested,
                                                 Qt.QueuedConnection)
        self.statusBar().addWidget(download_widget)

    def _removeDownloadRequested(self):
            download_widget = self.sender()
            self.statusBar().removeWidget(download_widget)
            del download_widget

    def _showFind(self):
        if self._find_tool_bar is None:
            self._find_tool_bar = FindToolBar()
            self._find_tool_bar.find.connect(self._tab_widget.find)
            self.addToolBar(Qt.BottomToolBarArea, self._find_tool_bar)
        else:
            self._find_tool_bar.show()
        self._find_tool_bar.focusFind()

    def writeBookmarks(self):
        self._bookmark_widget.writeBookmarks()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = createMainWindow()
    initial_urls = sys.argv[1:]
    if not initial_urls:
        initial_urls.append('http://qt.io')
    for url in initial_urls:
        main_win.loadUrlInNewTab(QUrl.fromUserInput(url))
    exit_code = app.exec()
    main_win.writeBookmarks()
    sys.exit(exit_code)
