from PyQt5 import QtWidgets, QtGui, QtCore, uic
from telepat import TelepatBaseObject


class ObjectEditor(QtWidgets.QDialog):
    saved = QtCore.pyqtSignal(str, TelepatBaseObject)

    def __init__(self, parent, key, obj):
        super(ObjectEditor, self).__init__(parent)

        self.edited_object = obj
        self.key = key
        uic.loadUi('objecteditor.ui', self)
        self.tableView.editObject(obj)

    def accept(self):
        self.saved.emit(self.key, self.edited_object)
        super(ObjectEditor, self).accept()