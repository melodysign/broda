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

