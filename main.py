#! /usr/bin/env python
import os
import sys
from functools import partial
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from conneditor import ConnectionEditor
from contextitem import ContextItem
from workers import ContextsWorker, SchemaWorker, ApplicationsWorker, RegisterWorker
from settings import tmsettings
import console

class TelepatManagerApplication(QtWidgets.QApplication):
    telepat_instance = None


class TelepatManager(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(TelepatManager, self).__init__(parent)
        self.applications = []

        uic.loadUi('main.ui', self)
        console.set_widget(self.loggerWidget)

        self.actionConnect.triggered.connect(self.openConnection)
        self.actionRefresh.triggered.connect(self.refreshContexts)
        self.actionShowNameId.toggled.connect(self.showNameId)
        self.contextsTreeView.clicked.connect(self.editItem)
        self.filterLineEdit.textChanged.connect(self.filterChanged)

        # Set up the UI
        self.actionRefresh.setEnabled(False)
        self.loggerWidget.setFont(QtGui.QFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)))
        self.setupHistoryMenu()
        self.setupSplitters()
        self.setupAppsCombobox()
        self.treeViewLayout.setContentsMargins(0, 0, 0, 0)

        self.contexts_model = QtGui.QStandardItemModel()
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.contexts_model)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.contextsTreeView.setModel(self.proxy)

        console.log("Application started")

    def setupHistoryMenu(self):
        if tmsettings.value("recentConnections"):
            self.menu_history.setEnabled(True)
            for connection_dict in tmsettings.value("recentConnections"):
                action = QtWidgets.QAction(connection_dict["url"], self.menu_history)
                action.triggered.connect(partial(self.openConnection, connection_dict))
                self.menu_history.addAction(action)
        else:
            self.menu_history.setEnabled(False)

    def setupSplitters(self):
        if tmsettings.value("consoleSplitterSize"):
            self.consoleSplitter.restoreState(tmsettings.value("consoleSplitterSize"))
        else:
            self.consoleSplitter.setSizes([self.height() - 200, 200])

        if tmsettings.value("treeViewSplitterSize"):
            self.treeViewSplitter.restoreState(tmsettings.value("treeViewSplitterSize"))
        else:
            self.treeViewSplitter.setSizes([200, self.width() - 200])

    def setupAppsCombobox(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        self.appsCombobox = QtWidgets.QComboBox(self)
        self.appsCombobox.setEnabled(False)
        self.appsCombobox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.appsCombobox.currentIndexChanged.connect(self.currentAppChanged)
        layout.addWidget(QtWidgets.QLabel("Application:"))
        layout.addWidget(self.appsCombobox)
        self.toolBar.addWidget(widget)

    def openConnection(self, connection_dict=None):
        self.connectionEditor = ConnectionEditor(self, connection_dict)
        self.connectionEditor.success.connect(self.login_success)
        self.connectionEditor.show()

    def refreshContexts(self):
        self.actionRefresh.setEnabled(False)
        self.contexts_model.clear()
        self.contexts_worker = ContextsWorker(self)
        self.contexts_worker.success.connect(self.contexts_success)
        self.contexts_worker.failed.connect(self.contexts_failed)
        self.contexts_worker.log.connect(console.log)
        self.contexts_worker.start()

    def currentAppChanged(self, index):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        app = self.applications[index]
        telepat.app_id = app["id"]
        telepat.api_key = app["keys"][0]
        self.registerDevice()
        self.refreshContexts()

    def filterChanged(self):
        self.proxy.setFilterRegExp(self.filterLineEdit.text())

    def editItem(self, index):
        item = self.contexts_model.itemFromIndex(index.model().mapToSource(index))
        if type(item) == ContextItem:
            self.tableView.editObject(item.context)

    def showNameId(self):
        i = 0
        while self.contexts_model.item(i):
            self.contexts_model.item(i).show_name(self.actionShowNameId.isChecked())
            i += 1
            
    def registerDevice(self):
        def register_success():
            pass
            
        def register_failed(err_code, msg):
            QtWidgets.QMessageBox.critical(self, "Failed to retrieve applications", "Error {0}: {1}".format(err_code, msg))
        
        self.register_worker = RegisterWorker(self)
        self.register_worker.success.connect(register_success)
        self.register_worker.failed.connect(register_failed)
        self.register_worker.log.connect(console.log)
        self.register_worker.start()

    def login_success(self):
        def apps_success(apps_list):
            self.applications = apps_list
            for app in self.applications:
                self.appsCombobox.addItem("{0} ({1})".format(app["name"], app["id"]))
            self.appsCombobox.setEnabled(True)

        def apps_failed(err_code, msg):
            QtWidgets.QMessageBox.critical(self, "Failed to retrieve applications", "Error {0}: {1}".format(err_code, msg))

        self.apps_worker = ApplicationsWorker(self)
        self.apps_worker.success.connect(apps_success)
        self.apps_worker.failed.connect(apps_failed)
        self.apps_worker.log.connect(console.log)
        self.apps_worker.start()

    def contexts_success(self, contexts_list):
        def schema_success(models_dict):
            self.actionRefresh.setEnabled(True)
            self.contexts_cb(contexts_list, models_dict)

        def schema_failed(err_code, msg):
            self.actionRefresh.setEnabled(True)
            QtWidgets.QMessageBox.critical(self, "Schema retrieving error", "Error {0}: {1}".format(err_code, msg))

        self.schema_worker = SchemaWorker(self)
        self.schema_worker.success.connect(schema_success)
        self.schema_worker.failed.connect(schema_failed)
        self.schema_worker.log.connect(console.log)
        self.schema_worker.start()

    def contexts_failed(self, err_code, msg):
        self.actionRefresh.setEnabled(True)
        QtWidgets.QMessageBox.critical(self, "Contexts retrieving error", "Error {0}: {1}".format(err_code, msg))

    def contexts_cb(self, contexts_list, models_dict):
        self.contexts_model.setHorizontalHeaderLabels(["Contexts"])
        self.actionRefresh.setEnabled(True)
        for ctx in contexts_list:
            item = ContextItem(ctx)
            item.setEditable(False)
            for key in models_dict:
                subitem = QtGui.QStandardItem(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon), key)
                subitem.setEditable(False)
                item.appendRow(subitem)
            self.contexts_model.appendRow(item)

    def closeEvent(self, event):
        tmsettings.setValue("consoleSplitterSize", self.consoleSplitter.saveState())
        tmsettings.setValue("treeViewSplitterSize", self.treeViewSplitter.saveState())
        super(TelepatManager, self).closeEvent(event)


if __name__ == "__main__":
    app = TelepatManagerApplication(sys.argv)
    win = TelepatManager()
    win.show()
    os._exit(app.exec_())
