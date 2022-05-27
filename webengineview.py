from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

from PySide6 import QtCore

_web_actions = [QWebEnginePage.Back, QWebEnginePage.Forward,
                QWebEnginePage.Reload,
                QWebEnginePage.Undo, QWebEnginePage.Redo,
                QWebEnginePage.Cut, QWebEnginePage.Copy,
                QWebEnginePage.Paste, QWebEnginePage.SelectAll]


class WebEngineView(QWebEngineView):

    enabled_changed = QtCore.Signal(QWebEnginePage.WebAction, bool)

    @staticmethod
    def webActions():
        return _web_actions

    @staticmethod
    def minimumZoomFactor():
        return 0.25

    @staticmethod
    def maximumZoomFactor():
        return 5

    def __init__(self, tab_factory_func, window_factory_func):
        super().__init__()
        self._tab_factory_func = tab_factory_func
        self._window_factory_func = window_factory_func
        page = self.page()
        self._actions = {}
        for web_action in WebEngineView.webActions():
            action = page.action(web_action)
            action.changed.connect(self._enabledChanged)
            self._actions[action] = web_action

    def isWebActionEnabled(self, web_action):
        return self.page().action(web_action).isEnabled()

    def createWindow(self, window_type):
        if (window_type == QWebEnginePage.WebBrowserTab or
            window_type == QWebEnginePage.WebBrowserBackgroundTab):
            return self._tab_factory_func()
        return self._window_factory_func()

    def _enabledChanged(self):
        action = self.sender()
        web_action = self._actions[action]
        self.enabled_changed.emit(web_action, action.isEnabled())
        