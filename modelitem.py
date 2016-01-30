from PyQt5 import QtGui, QtWidgets 
from PyQt5.QtCore import QCoreApplication


class ModelItem(QtGui.QStandardItem):
    def __init__(self, name, model):
        self.name = name
        self.model = model
        icon = QCoreApplication.instance().style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
        super(ModelItem, self).__init__(icon, name)

    def show_name(self, show):
        pass
