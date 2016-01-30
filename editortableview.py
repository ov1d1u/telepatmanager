from copy import copy
from PyQt5 import QtWidgets,  QtCore
from workers import ContextPatchWorker
from telepat import TelepatContext
from models.basemodel import BaseModel
import console


class EditorTableModel(QtCore.QAbstractTableModel):
    valueChanged = QtCore.pyqtSignal(BaseModel)
    basemodel = None
    
    def __init__(self, parent, basemodel):
        super(EditorTableModel, self).__init__(parent)
        self.basemodel = basemodel
        rows = []
        for key in sorted(basemodel.properties().keys()):
            if not basemodel.isIgnored(key):
                rows.append([key, basemodel[key]])
        self.columns = ["Key", "Value"]
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
        setattr(self.basemodel, self.rows[index.row()][0], self.rows[index.row()][1])  # Update the object
        self.valueChanged.emit(self.basemodel)
        return True
       
    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self.columns[col]
        return QtCore.QVariant()
        
    def flags(self, index):
        value = self.rows[index.row()][index.column()]
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if not isinstance(value, dict) and not index.column() == 0 and not self.basemodel.isReadOnly(self.rows[index.row()][0]):
            flags = flags | QtCore.Qt.ItemIsEditable
        return flags

class EditorTableView(QtWidgets.QTableView):
    original_object = None
    
    def __init__(self, parent=None):
        super(EditorTableView,  self).__init__(parent)
        
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.verticalHeader().setVisible(False)
        
    def resizeEvent(self, event):
        width = event.size().width()
        self.setColumnWidth(0, width * 0.25)
        self.setColumnWidth(1, width * 0.75)
        
    def editObject(self, basemodel):
        self.original_object = copy(basemodel)
        model = EditorTableModel(self, basemodel)
        model.valueChanged.connect(self.valueChanged)
        self.setModel(model)
        
    def valueChanged(self, updated_object):
        def patch_success(response):
            self.editObject(updated_object)
            
        def patch_failed(status,  message):
            QtWidgets.QMessageBox.critical(self, "Patch error", "Error {0}: {1}".format(status, message))
        
        if updated_object == self.original_object:
            return

        if isinstance(updated_object, TelepatContext):
            worker = ContextPatchWorker(self, updated_object)
            worker.success.connect(patch_success)
            worker.failed.connect(patch_failed)
            worker.log.connect(console.log)
            worker.start()
