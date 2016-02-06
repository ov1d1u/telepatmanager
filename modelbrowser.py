from PyQt5 import QtGui, QtWidgets, QtCore
import telepat
from telepat.models import TelepatBaseObject
from models.telepatobject import TelepatObject
from workers import SubscribeWorker, UnsubscribeWorker
from objecteditor import ObjectEditor
import console


class ModelSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow(self, row_num, parent):
        model = self.sourceModel()
        text = self.filterRegExp().pattern()
        if not len(text): 
            return True

        row = [model.item(row_num, column_num) for column_num in range(model.columnCount())]
        tests = []
        for col in range(0, len(row)-1):
            tests.append(text.lower() in row[col].text().lower())

        return True in tests


class BrowserModel(QtGui.QStandardItemModel):
    ignored_colums = ["type", "application_id", "context_id", "model"]

    def __init__(self, parent, objects):
        super(BrowserModel, self).__init__(parent)
        self.objects = objects

        # Create a list of columns
        columns = []
        for obj in objects:
            for key in obj.keys():
                if not key in columns and not key in self.ignored_colums:
                    columns.append(key)

        # Move "id" at the first column
        if "id" in columns:
            columns.insert(0, columns.pop(columns.index("id")))
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        # Populate according to columns
        for obj in objects:
            items_row = []
            for col in columns:
                if col in obj.keys():
                    if isinstance(obj[col], str) or isinstance(obj[col], int):
                        items_row.append(QtGui.QStandardItem(str(obj[col])))
                    elif isinstance(obj[col], dict):
                        items_row.append(QtGui.QStandardItem("[ Object ]"))
                    else:
                        items_row.append(QtGui.QStandardItem(""))
                else:
                    items_row.append(QtGui.QStandardItem(""))
            self.appendRow(items_row)



class ModelBrowser(QtWidgets.QWidget):
    channel = None

    def browseModel(self, telepat_context, telepat_model):
        self.telepat_context = telepat_context
        self.telepat_model = telepat_model

        if self.channel:
            self.unsubscribe()

        def on_subscribe_success(channel, objects):
            self.model = BrowserModel(self.treeView, objects)
            self.proxyModel = ModelSortFilterProxyModel(self)
            self.proxyModel.setSourceModel(self.model)
            self.proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
            self.treeView.setModel(self.proxyModel)
            self.treeView.resizeColumnToContents(0)

            self.channel = channel

        def on_subscribe_failure(self, err_code, err_message):
            print("Error msg: {0}".format(err_message))

        if not hasattr(self, "treeView"):
            self.treeView = self.findChild(QtWidgets.QTreeView, "treeView")
            self.treeView.setSortingEnabled(True)
            self.treeView.setRootIsDecorated(False)
            self.treeView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.treeView.doubleClicked.connect(self.editObject)
        
        if not hasattr(self, "bFilterLineEdit"):
            self.bFilterLineEdit = self.findChild(QtWidgets.QLineEdit, "bFilterLineEdit")
            self.bFilterLineEdit.textChanged.connect(self.filterChanged)

        self.treeView.setModel(None)

        worker = SubscribeWorker(self, telepat_context, telepat_model, TelepatBaseObject)
        worker.success.connect(on_subscribe_success)
        worker.failed.connect(on_subscribe_failure)
        worker.log.connect(console.log)
        worker.start()

    def filterChanged(self):
        if hasattr(self, "proxyModel"):
            self.proxyModel.invalidateFilter()
            self.proxyModel.setFilterFixedString(self.bFilterLineEdit.text())

    def editObject(self, index):
        def object_saved(updated_object):
            row = self.proxyModel.mapToSource(index).row()
            obj = index.model().sourceModel().objects[row]
            telepat_object = TelepatBaseObject(updated_object.to_json())
            patches = obj.patch_against(telepat_object)
            self.channel.patch(updated_object)

        def object_dismissed():
            if hasattr(self, "object_editor"):
                del self.object_editor

        row = self.proxyModel.mapToSource(index).row()
        obj = index.model().sourceModel().objects[row]
        self.object_editor = ObjectEditor(self, self.telepat_context, TelepatObject(obj.to_json()))
        self.object_editor.saved.connect(object_saved)
        self.object_editor.rejected.connect(object_dismissed)
        self.object_editor.show()
        
    def unsubscribe(self):
        def on_unsubscribe_success(self):
            pass

        def on_unsubscribe_failure(self, err_code, err_message):
            print("Error msg: {0}".format(err_message))

        worker = UnsubscribeWorker(self, self.channel)
        worker.success.connect(on_unsubscribe_success)
        worker.failed.connect(on_unsubscribe_failure)
        worker.log.connect(console.log)
        worker.start()