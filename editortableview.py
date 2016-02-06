from copy import copy
from PyQt5 import QtWidgets, QtCore, QtGui
from workers import ContextPatchWorker
from objecteditor import ObjectEditor
from telepat import TelepatContext
from models.basemodel import BaseModel
from models.metaobject import MetaObject
import console


class ComboBoxDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent, basemodel, objects_map):
        super(ComboBoxDelegate, self).__init__(parent)
        self.basemodel = basemodel
        self.objects_map = objects_map
        
        rows = []
        for key in sorted(basemodel.keys()):
            if not basemodel.isIgnored(key):
                rows.append([key, basemodel[key]])
        self.rows = rows

    def createEditor(self, parent, option, index):
        key = self.rows[index.row()][0][:-3]
        if not key in self.objects_map:
            return super(ComboBoxDelegate, self).createEditor(parent, option, index)

        ids = []
        for obj in self.objects_map[key]:
            ids.append(obj.id)

        editor = QtWidgets.QComboBox(parent)
        editor.addItems(ids)
        editor.setCurrentIndex(0)
        editor.installEventFilter(self)
        return editor
 
    def setEditorData(self, editor, index):
        key = self.rows[index.row()][0][:-3]
        if not key in self.objects_map:
            return super(ComboBoxDelegate, self).setEditorData(editor, index)

        value = index.data(QtCore.Qt.DisplayRole)
        ids = []
        for obj in self.objects_map[key]:
            ids.append(obj.id)

        editor.setCurrentIndex(ids.index(value))
 
    def setModelData(self, editor, model, index):
        key = self.rows[index.row()][0]
        if not key in self.objects_map:
            return super(ComboBoxDelegate, self).setModelData(editor, model, index)
        value = editor.currentIndex()
        model.setData(index, value, QtCore.Qt.DisplayRole)
 
    def updateEditorGeometry(self, editor, option, index):
        key = self.rows[index.row()][0]
        if not key in self.objects_map:
            return super(ComboBoxDelegate, self).updateEditorGeometry(editor, option, index)
        editor.setGeometry(option.rect)


class EditorTableModel(QtCore.QAbstractTableModel):
    valueChanged = QtCore.pyqtSignal(BaseModel)
    basemodel = None
    
    def __init__(self, parent, basemodel):
        super(EditorTableModel, self).__init__(parent)
        self._basemodel = basemodel
        rows = []
        for key in sorted(basemodel.keys()):
            if not basemodel.isIgnored(key):
                rows.append([key, basemodel[key]])
        self.columns = ["Key", "Value"]
        self.rows = rows

    @property
    def basemodel(self):
        return self._basemodel

    @basemodel.setter
    def basemodel(self, basemodel):
        value_dict = basemodel.to_json()

        # check for updated rows
        for row in self.rows:
            key = row[0]
            value = row[1]
            if key in value_dict and value_dict[key] != value:
                QtCore.pyqtRemoveInputHook()
                row[1] = value_dict[key]
                self.dataChanged.emit(self.index(self.rows.index(row), 1), self.index(self.rows.index(row), 1))
        self._basemodel = basemodel
        
    def columnCount(self, parent):
        return len(self.columns)
        
    def rowCount(self, parent):
        return len(self.rows)
        
    def data(self, index, role=QtCore.Qt.DisplayRole):
        value = self.rows[index.row()][index.column()]
        if not index.isValid(): 
            return QtCore.QVariant() 
        elif role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole: 
            return QtCore.QVariant()
        if isinstance(value, dict):
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
    updated_object = None
    
    def __init__(self, parent=None):
        super(EditorTableView,  self).__init__(parent)
        
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.verticalHeader().setVisible(False)
        self.doubleClicked.connect(self.openObject)
        
    def resizeEvent(self, event):
        width = event.size().width()
        self.setColumnWidth(0, width * 0.25)
        self.setColumnWidth(1, width * 0.75)
        
    def editObject(self, basemodel, objects_map=None):
        if self.original_object and self.original_object.id == basemodel.id:  # If it's the same object just look for updates
            self.model().basemodel = basemodel
            return
        self.original_object = copy(basemodel)
        self.objects_map = objects_map if objects_map else {}
        model = EditorTableModel(self, basemodel)
        model.valueChanged.connect(self.valueChanged)
        self.setModel(model)
        self.setItemDelegateForColumn(1, ComboBoxDelegate(self, basemodel, self.objects_map))

        for row in range(0, model.rowCount(None)):
            key = model.rows[row][0][:-3]
            if key in self.objects_map:
                self.openPersistentEditor(model.index(row, 1))

    def openObject(self, index):
        def object_saved(key, updated_object):
            parent_object = copy(self.original_object)
            setattr(parent_object, key, updated_object.to_json())
            self.valueChanged(parent_object)

        def object_dismissed():
            del self.object_editor

        key = index.model().data(index.model().index(index.row(), 0))
        if isinstance(self.original_object[key], dict) and \
            not index.model().flags(index) & QtCore.Qt.ItemIsEditable:
            self.object_editor = ObjectEditor(self, key, MetaObject(dict(self.model().basemodel[key])))
            self.object_editor.saved.connect(object_saved)
            self.object_editor.rejected.connect(object_dismissed)
            self.object_editor.show()
        
    def valueChanged(self, updated_object):
        def patch_success(response):
            self.editObject(self.updated_object)
            self.updated_object = None
            
        def patch_failed(status,  message):
            QtWidgets.QMessageBox.critical(self, "Patch error", "Error {0}: {1}".format(status, message))
            self.updated_object = None

        self.updated_object = updated_object
        if self.updated_object == self.original_object:
            return

        if isinstance(self.updated_object, TelepatContext):
            worker = ContextPatchWorker(self, self.updated_object)
            worker.success.connect(patch_success)
            worker.failed.connect(patch_failed)
            worker.log.connect(console.log)
            worker.start()
