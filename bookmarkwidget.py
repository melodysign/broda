import json
import os
import warnings

from PySide6 import QtCore
from PySide6.QtCore import QDir, QFileInfo, QStandardPaths, Qt, QUrl
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QMenu, QMessageBox, QTreeView

_url_role = Qt.UserRole + 1

# Default bookmarks as an array of arrays which is the form
# used to read from/write to a .json bookmarks file
_default_bookmarks = [
    ['Tool Bar'],
    ['http://qt.io', 'Qt', ':/qt-project.org/qmessagebox/images/qtlogo-64.png'],
    ['https://download.qt.io/snapshots/ci/pyside/', 'Downloads'],
    ['https://doc.qt.io/qtforpython/', 'Documentation'],
    ['https://bugreports.qt.io/projects/PYSIDE/', 'Bug Reports'],
    ['https://www.python.org/', 'Python', None],
    ['https://wiki.qt.io/PySide6', 'Qt for Python', None],
    ['Other Bookmarks']
]

def _configDir():
    location = QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
    return f'{location}/QtForPythonBrowser'


_bookmark_file = 'bookmarks.json'


def _createFolderItem(title):
    result = QStandardItem(title)
    result.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    return result


def _createItem(url, title, icon):
    result = QStandardItem(title)
    result.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    result.setData(url, _url_role)
    if icon is not None:
        result.setIcon(icon)
    return result


# Create the model from an array of arrays
def _createModel(parent, serialized_bookmarks):
    result = QStandardItemModel(0, 1, parent)
    last_folder_item = None
    for entry in serialized_bookmarks:
        if len(entry) == 1:
            last_folder_item = _createFolderItem(entry[0])
            result.appendRow(last_folder_item)
        else:
            url = QUrl.fromUserInput(entry[0])
            title = entry[1]
            icon = QIcon(entry[2]) if len(entry) > 2 and entry[2] else None
            last_folder_item.appendRow(_createItem(url, title, icon))
    return result


# Serialize model into an array of arrays, writing out the icons
# into .png files under directory in the process
def _serializeModel(model, directory):
    result = []
    folder_count = model.rowCount()
    for f in range(0, folder_count):
        folder_item = model.item(f)
        result.append([folder_item.text()])
        item_count = folder_item.rowCount()
        for i in range(0, item_count):
            item = folder_item.child(i)
            entry = [item.data(_url_role).toString(), item.text()]
            icon = item.icon()
            if not icon.isNull():
                icon_sizes = icon.availableSizes()
                largest_size = icon_sizes[len(icon_sizes) - 1]
                w = largest_size.width()
                icon_file_name = f'{directory}/icon{f:02}_{i:02}_{w}.png'
                icon.pixmap(largest_size).save(icon_file_name, 'PNG')
                entry.append(icon_file_name)
            result.append(entry)
    return result


# Bookmarks as a tree view to be used in a dock widget with
# functionality to persist and populate tool bars and menus.
class BookmarkWidget(QTreeView):
    """Provides a tree view to manage the bookmarks."""

    open_bookmark = QtCore.Signal(QUrl)
    open_bookmark_in_new_tab = QtCore.Signal(QUrl)
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(True)
        self._model = _createModel(self, self._readBookmarks())
        self.setModel(self._model)
        self.expandAll()
        self.activated.connect(self._activated)
        self._model.rowsInserted.connect(self._changed)
        self._model.rowsRemoved.connect(self._changed)
        self._model.dataChanged.connect(self._changed)
        self._modified = False

    def _changed(self):
        self._modified = True
        self.changed.emit()

    def _activated(self, index):
        item = self._model.itemFromIndex(index)
        self.open_bookmark.emit(item.data(_url_role))

    def _actionActivated(self, index):
        action = self.sender()
        self.open_bookmark.emit(action.data())

    def _toolBarItem(self):
        return self._model.item(0, 0)

    def _otherItem(self):
        return self._model.item(1, 0)

    def addBookmark(self, url, title, icon):
        self._otherItem().appendRow(_createItem(url, title, icon))

    def addToolbarBookmark(self, url, title, icon):
        self._toolBarItem().appendRow(_createItem(url, title, icon))

    # Synchronize the bookmarks under parent_item to a target_object
    # like QMenu/QToolBar, which has a list of actions. Update
    # the existing actions, append new ones if needed or hide
    # superfluous ones
    def _populateActions(self, parent_item, target_object, first_action):
        existing_actions = target_object.actions()
        existing_action_count = len(existing_actions)
        a = first_action
        row_count = parent_item.rowCount()
        for r in range(0, row_count):
            item = parent_item.child(r)
            title = item.text()
            icon = item.icon()
            url = item.data(_url_role)
            if a < existing_action_count:
                action = existing_actions[a]
                if (title != action.toolTip()):
                    action.setText(BookmarkWidget.shortTitle(title))
                    action.setIcon(icon)
                    action.setToolTip(title)
                    action.setData(url)
                    action.setVisible(True)
            else:
                short_title = BookmarkWidget.shortTitle(title)
                action = target_object.addAction(icon, short_title)
                action.setToolTip(title)
                action.setData(url)
                action.triggered.connect(self._actionActivated)
            a = a + 1
        while a < existing_action_count:
            existing_actions[a].setVisible(False)
            a = a + 1

    def populateToolbar(self, tool_bar):
        self._populateActions(self._toolBarItem(), tool_bar, 0)

    def populateOther(self, menu, first_action):
        self._populateActions(self._otherItem(), menu, first_action)

    def _currentItem(self):
        index = self.currentIndex()
        if index.isValid():
            item = self._model.itemFromIndex(index)
            if item.parent():  # exclude top level items
                return item
        return None

    def contextMenuEvent(self, event):
        context_menu = QMenu()
        open_in_new_tab_action = context_menu.addAction("Open in New Tab")
        remove_action = context_menu.addAction("Remove...")
        current_item = self._currentItem()
        open_in_new_tab_action.setEnabled(current_item is not None)
        remove_action.setEnabled(current_item is not None)
        chosen_action = context_menu.exec(event.globalPos())
        if chosen_action == open_in_new_tab_action:
            self.open_bookmarkInNewTab.emit(current_item.data(_url_role))
        elif chosen_action == remove_action:
            self._removeItem(current_item)

    def _removeItem(self, item):
        message = f"Would you like to remove \"{item.text()}\"?"
        button = QMessageBox.question(self, "Remove", message,
                                      QMessageBox.Yes | QMessageBox.No)
        if button == QMessageBox.Yes:
            item.parent().removeRow(item.row())

    def writeBookmarks(self):
        if not self._modified:
            return
        dir_path = _configDir()
        native_dir_path = QDir.toNativeSeparators(dir_path)
        directory = QFileInfo(dir_path)
        if not directory.isDir():
            print(f'Creating {native_dir_path}...')
            if not QDir(directory.absolutePath()).mkpath(directory.fileName()):
                warnings.warn(f'Cannot create {native_dir_path}.',
                              RuntimeWarning)
                return
        serialized_model = _serializeModel(self._model, dir_path)
        bookmark_file_name = os.path.join(native_dir_path, _bookmark_file)
        print(f'Writing {bookmark_file_name}...')
        with open(bookmark_file_name, 'w') as bookmark_file:
            json.dump(serialized_model, bookmark_file, indent=4)

    def _readBookmarks(self):
        bookmark_file_name = os.path.join(QDir.toNativeSeparators(_configDir()),
                                          _bookmark_file)
        if os.path.exists(bookmark_file_name):
            print(f'Reading {bookmark_file_name}...')
            return json.load(open(bookmark_file_name))
        return _default_bookmarks

    # Return a short title for a bookmark action,
    # "Qt | Cross Platform.." -> "Qt"
    @staticmethod
    def shortTitle(t):
        i = t.find(' | ')
        if i == -1:
            i = t.find(' - ')
        return t[0:i] if i != -1 else t
        