from copy import copy
from PyQt5 import QtWidgets,  QtCore
from workers import ContextPatchWorker
from telepat import TelepatContext
import console

class EditorTableWidget(QtWidgets.QTableWidget):
    edited_object = None
    
    def __init__(self,  parent=None):
        super(EditorTableWidget,  self).__init__(parent)
        
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.verticalHeader().setVisible(False)
        
        self.activated.connect(self.editItem)
        
    def editObject(self, object):
        self.edited_object = object
        if self.receivers(self.itemChanged):
            self.itemChanged.disconnect(self.itemValueChanged)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["key",  "value"])
        self.setRowCount(len(object.keys()))
        for key in object:
            tableitem_key = QtWidgets.QTableWidgetItem(key)
            tableitem_key.setFlags(tableitem_key.flags() ^ QtCore.Qt.ItemIsEditable)
            self.setItem(list(object.keys()).index(key), 0, tableitem_key)
            if isinstance(object[key], dict):
                tableitem_value = QtWidgets.QTableWidgetItem("[ Object ]")
                tableitem_value.setFlags(tableitem_value.flags() ^ QtCore.Qt.ItemIsEditable)
            else:
                tableitem_value = QtWidgets.QTableWidgetItem(str(object[key]))
            self.setItem(list(object.keys()).index(key), 1, tableitem_value)
            
        self.resizeColumnsToContents()
        self.setColumnWidth(1,  self.width() - self.columnWidth(0) - 5)
        self.itemChanged.connect(self.itemValueChanged)
        
    def editItem(self,  item):
        object_copy = copy(self.edited_object)
        
    def itemValueChanged(self,  item):
        def patch_success(response):
            pass
            
        def patch_failed(status,  message):
            QtWidgets.QMessageBox.critical(self, "Patch error", "Error {0}: {1}".format(status, message))
        
        updated_object = copy(self.edited_object)
        setattr(updated_object,  self.item(item.row(), 0).text(),  item.text())
        if isinstance(updated_object,  TelepatContext):
            worker = ContextPatchWorker(self,  updated_object)
            worker.success.connect(patch_success)
            worker.failed.connect(patch_failed)
            worker.log.connect(console.log)
            worker.start()
        
