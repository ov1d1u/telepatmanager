from PyQt5 import QtGui, QtWidgets 
from PyQt5.QtCore import QCoreApplication
import threading


class ContextItem(QtGui.QStandardItem):
    def __init__(self, context):
        self._context = context
        icon = QCoreApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_DirClosedIcon)
        name = context.name if hasattr(context, "name") and context.name else context.id
        super(ContextItem, self).__init__(icon, name)

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, value):
        self._context = value
        self.setIcon(QCoreApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_DirClosedIcon))
        self.setText(self.context.name if hasattr(self.context, "name") and self.context.name else self.context.id)
        print("threading.current_thread() {0}".format(threading.current_thread()))

    def show_name(self, show):
        if show:
            name = context.name if hasattr(context, "name") and context.name else context.id
            self.setText(name)
        else:
            self.setText(self.context["id"])
