from copy import copy
from PyQt5 import QtWidgets,  QtCore
from workers import ContextPatchWorker
from telepat import TelepatContext
import console


class EditorTableModel(QtCore.QAbstractTableModel):
    valueChanged = QtCore.pyqtSignal(tuple)
    
    def __init__(self, parent, columns, rows):
        super(EditorTableModel, self).__init__(parent)
        self.columns = columns
        self.rows = rows
        
    def columnCount(self, parent):
        return len(self.columns)
        
    def rowCount(self, parent):
        return len(self.rows)
        
    def data(self, index, role):
        value = self.rows[index.row()][index.column()]
        if not index.isValid(): 
            return QtCore.QVariant() 
        elif role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole: 
            return QtCore.QVariant()
        if isinstance(value,  dict):
            return "[ Object ]"
        return value
        
    def setData(self, index, value, role):
        super(EditorTableModel, self).setData(index, value, role)
        self.rows[index.row()][index.column()] = value
        self.valueChanged.emit((self.rows[index.row()][0], self.rows[index.row()][1]))
        return True
       
    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self.columns[col]
        return QtCore.QVariant()
        
    def flags(self, index):
        value = self.rows[index.row()][index.column()]
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if not isinstance(value, dict):
            flags = flags | QtCore.Qt.ItemIsEditable
        return flags

class EditorTableView(QtWidgets.QTableView):
    edited_object = None
    
    def __init__(self,  parent=None):
        super(EditorTableView,  self).__init__(parent)
        
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.verticalHeader().setVisible(False)
        
    def resizeEvent(self, event):
        width = event.size().width()
        self.setColumnWidth(0, width * 0.25)
        self.setColumnWidth(1, width * 0.75)
        
    def editObject(self, object):
        self.edited_object = object
        cols = ["Key",  "Value"]
        rows = []
        for key in sorted(object):
            if object[key]:
                rows.append([key,  object[key]])
        model = EditorTableModel(self, cols, rows)
        model.valueChanged.connect(self.valueChanged)
        self.setModel(model)
        
    def valueChanged(self, values):
        updated_object = copy(self.edited_object)
        setattr(updated_object, values[0], values[1])
        
        def patch_success(response):
            self.editObject(updated_object)
            
        def patch_failed(status,  message):
            QtWidgets.QMessageBox.critical(self, "Patch error", "Error {0}: {1}".format(status, message))
        
        if updated_object.to_json() == self.edited_object.to_json():
            return
        if isinstance(updated_object,  TelepatContext):
            worker = ContextPatchWorker(self,  updated_object)
            worker.success.connect(patch_success)
            worker.failed.connect(patch_failed)
            worker.log.connect(console.log)
            worker.start()
