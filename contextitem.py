from PyQt5 import QtGui, QtWidgets 
from PyQt5.QtCore import QCoreApplication


class ContextItem(QtGui.QStandardItem):
    def __init__(self, context):
        self.context = context
        icon = QCoreApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_DirClosedIcon)
        name = context.name if hasattr(context, "name") and context.name else context.id
        super(ContextItem, self).__init__(icon, name)

    def show_name(self, show):
        if show:
            name = context.name if hasattr(context, "name") and context.name else context.id
            self.setText(name)
        else:
            self.setText(self.context["id"])
