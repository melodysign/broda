from functools import partial

from bookmarkwidget import BookmarkWidget
from webengineview import WebEngineView
from historywindow import HistoryWindow
from PySide6 import QtCore
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QMenu, QTabBar, QTabWidget
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage


class BrowserTabWidget(QTabWidget):
    """Enables having several tabs with QWebEngineView."""

    url_changed = QtCore.Signal(QUrl)
    enabled_changed = QtCore.Signal(QWebEnginePage.WebAction, bool)
    download_requested = QtCore.Signal(QWebEngineDownloadRequest)

    def __init__(self, window_factory_function):
        super().__init__()
        self.setTabsClosable(True)
        self._window_factory_function = window_factory_function
        self._webengineviews = []
        self._history_windows = {}  # map WebengineView to HistoryWindow
        self.currentChanged.connect(self._currentChanged)
        self.tabCloseRequested.connect(self.handleTabCloseRequest)
        self._actions_enabled = {}
        for web_action in WebEngineView.webActions():
            self._actions_enabled[web_action] = False

        tab_bar = self.tabBar()
        tab_bar.setSelectionBehaviorOnRemove(QTabBar.SelectPreviousTab)
        tab_bar.setContextMenuPolicy(Qt.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self._handleTabContextMenu)

    def addBrowserTab(self):
        factory_func = partial(BrowserTabWidget.addBrowserTab, self)
        web_engine_view = WebEngineView(factory_func,
                                        self._window_factory_function)
        index = self.count()
        self._webengineviews.append(web_engine_view)
        title = f'Tab {index + 1}'
        self.addTab(web_engine_view, title)
        page = web_engine_view.page()
        page.titleChanged.connect(self._titleChanged)
        page.iconChanged.connect(self._iconChanged)
        page.profile().downloadRequested.connect(self._downloadRequested)
        web_engine_view.urlChanged.connect(self._urlChanged)
        web_engine_view.enabled_changed.connect(self._enabledChanged)
        self.setCurrentIndex(index)
        return web_engine_view

    def load(self, url):
        index = self.currentIndex()
        if index >= 0 and url.isValid():
            self._webengineviews[index].setUrl(url)

    def find(self, needle, flags):
        index = self.currentIndex()
        if index >= 0:
            self._webengineviews[index].page().findText(needle, flags)

    def url(self):
        index = self.currentIndex()
        return self._webengineviews[index].url() if index >= 0 else QUrl()

    def _urlChanged(self, url):
        index = self.currentIndex()
        if index >= 0 and self._webengineviews[index] == self.sender():
                self.url_changed.emit(url)

    def _titleChanged(self, title):
        index = self._indexOfPage(self.sender())
        if (index >= 0):
            self.setTabText(index, BookmarkWidget.short_title(title))

    def _iconChanged(self, icon):
        index = self._indexOfPage(self.sender())
        if (index >= 0):
            self.setTabIcon(index, icon)

    def _enabledChanged(self, web_action, enabled):
        index = self.currentIndex()
        if index >= 0 and self._webengineviews[index] == self.sender():
            self._checkEmitEnabledChanged(web_action, enabled)

    def _checkEmitEnabledChanged(self, web_action, enabled):
        if enabled != self._actions_enabled[web_action]:
            self._actions_enabled[web_action] = enabled
            self.enabled_changed.emit(web_action, enabled)

    def _currentChanged(self, index):
        self._updateActions(index)
        self.url_changed.emit(self.url())

    def _updateActions(self, index):
        if index >= 0 and index < len(self._webengineviews):
            view = self._webengineviews[index]
            for web_action in WebEngineView.webActions():
                enabled = view.is_web_action_enabled(web_action)
                self._checkEmitEnabledChanged(web_action, enabled)

    def back(self):
        self._triggerAction(QWebEnginePage.Back)

    def forward(self):
        self._triggerAction(QWebEnginePage.Forward)

    def reload(self):
        self._triggerAction(QWebEnginePage.Reload)

    def undo(self):
        self._triggerAction(QWebEnginePage.Undo)

    def redo(self):
        self._triggerAction(QWebEnginePage.Redo)

    def cut(self):
        self._triggerAction(QWebEnginePage.Cut)

    def copy(self):
        self._triggerAction(QWebEnginePage.Copy)

    def paste(self):
        self._triggerAction(QWebEnginePage.Paste)

    def selectAll(self):
        self._triggerAction(QWebEnginePage.SelectAll)

    def showHistory(self):
        index = self.currentIndex()
        if index >= 0:
            webengineview = self._webengineviews[index]
            history_window = self._history_windows.get(webengineview)
            if not history_window:
                history = webengineview.page().history()
                history_window = HistoryWindow(history, self)
                history_window.open_url.connect(self.load)
                history_window.setWindowFlags(history_window.windowFlags()
                                              | Qt.Window)
                history_window.setWindowTitle('History')
                self._history_windows[webengineview] = history_window
            else:
                history_window.refresh()
            history_window.show()
            history_window.raise_()

    def zoomFactor(self):
        return self._webengineviews[0].zoomFactor() if self._webengineviews else 1.0

    def setZoomFactor(self, z):
        for w in self._webengineviews:
            w.setZoomFactor(z)

    def _handleTabContextMenu(self, point):
        index = self.tabBar().tabAt(point)
        if index < 0:
            return
        tab_count = len(self._webengineviews)
        context_menu = QMenu()
        duplicate_tab_action = context_menu.addAction("Duplicate Tab")
        close_other_tabs_action = context_menu.addAction("Close Other Tabs")
        close_other_tabs_action.setEnabled(tab_count > 1)
        close_tabs_to_the_right_action = context_menu.addAction("Close Tabs to the Right")
        close_tabs_to_the_right_action.setEnabled(index < tab_count - 1)
        close_tab_action = context_menu.addAction("&Close Tab")
        chosen_action = context_menu.exec(self.tabBar().mapToGlobal(point))
        if chosen_action == duplicate_tab_action:
            current_url = self.url()
            self.addBrowserTab().load(current_url)
        elif chosen_action == close_other_tabs_action:
            for t in range(tab_count - 1, -1, -1):
                if t != index:
                    self.handleTabCloseRequest(t)
        elif chosen_action == close_tabs_to_the_right_action:
            for t in range(tab_count - 1, index, -1):
                self.handleTabCloseRequest(t)
        elif chosen_action == close_tab_action:
            self.handleTabCloseRequest(index)

    def handleTabCloseRequest(self, index):
        if (index >= 0 and self.count() > 1):
            webengineview = self._webengineviews[index]
            if self._history_windows.get(webengineview):
                del self._history_windows[webengineview]
            self._webengineviews.remove(webengineview)
            self.removeTab(index)

    def closeCurrentTab(self):
        self.handleTabCloseRequest(self.currentIndex())

    def _triggerAction(self, action):
        index = self.currentIndex()
        if index >= 0:
            self._webengineviews[index].page().triggerAction(action)

    def _indexOfPage(self, web_page):
        for p in range(0, len(self._webengineviews)):
            if (self._webengineviews[p].page() == web_page):
                return p
        return -1

    def _downloadRequested(self, item):
        self.download_requested.emit(item)
