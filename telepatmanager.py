import traceback
import time
import io
from copy import copy
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from settings import tmsettings
from functools import partial
from const import *
from event import TelepatContextAddEvent, TelepatContextUpdateEvent, ExceptionEvent
from conneditor import ConnectionEditor
from contextitem import ContextItem
from models.context import Context
from models.model import Model
from modelitem import ModelItem
from workers import ContextsWorker, SchemaWorker, ApplicationsWorker, RegisterWorker, UsersWorker
from telepat.transportnotification import NOTIFICATION_TYPE_ADDED, NOTIFICATION_TYPE_DELETED, NOTIFICATION_TYPE_UPDATED
import console


class TelepatManager(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(TelepatManager, self).__init__(parent)
        self.applications = []

        uic.loadUi('telepatmanager.ui', self)
        console.set_widget(self.loggerWidget)

        self.actionConnect.triggered.connect(self.openConnection)
        self.actionRefresh.triggered.connect(self.refreshContexts)
        self.actionEditApp.triggered.connect(self.editApplication)
        self.actionShowNameId.toggled.connect(self.showNameId)
        self.contextsTreeView.clicked.connect(self.itemSelected)
        self.filterLineEdit.textChanged.connect(self.filterChanged)

        # Set up the UI
        self.actionRefresh.setEnabled(False)
        self.loggerWidget.setFont(QtGui.QFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)))
        self.setupHistoryMenu()
        self.setupSplitters()
        self.setupAppsCombobox()
        self.treeViewLayout.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget.setContentsMargins(0, 0, 0, 0)
        self.setUnifiedTitleAndToolBarOnMac(True)

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
        self.appsCombobox.setDisabled(True)
        self.actionEditApp.setDisabled(True)
        self.appsCombobox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.appsCombobox.currentIndexChanged.connect(self.currentAppChanged)
        layout.addWidget(QtWidgets.QLabel("Application:"))
        layout.addWidget(self.appsCombobox)
        self.applicationToolbar.insertWidget(self.actionEditApp, widget)

    def openConnection(self, connection_dict=None):
        self.connectionEditor = ConnectionEditor(self, connection_dict)
        self.connectionEditor.success.connect(self.login_success)
        self.connectionEditor.show()

    def refreshContexts(self):
        def contexts_success(contexts_list):
            telepat = QtCore.QCoreApplication.instance().telepat_instance
            telepat.on_update_context = self.on_update_context
            telepat.on_add_context = self.on_add_context
            application = self.applications[self.appsCombobox.currentIndex()]

            self.contexts_model.setHorizontalHeaderLabels(["Contexts"])
            self.actionRefresh.setEnabled(True)
            for ctx in contexts_list:
                item = ContextItem(ctx)
                item.setEditable(False)
                for key in application.schema:
                    subitem = ModelItem(key, Model(application.schema[key].to_json()))
                    subitem.setEditable(False)
                    item.appendRow(subitem)
                self.contexts_model.appendRow(item)

        def contexts_failed(err_code, msg):
            self.actionRefresh.setEnabled(True)
            QtWidgets.QMessageBox.critical(self, "Contexts retrieving error", "Error {0}: {1}".format(err_code, msg))

        self.actionRefresh.setEnabled(False)
        self.contexts_model.clear()
        self.contexts_worker = ContextsWorker(self)
        self.contexts_worker.success.connect(contexts_success)
        self.contexts_worker.failed.connect(contexts_failed)
        self.contexts_worker.log.connect(console.log)
        self.contexts_worker.start()

    def getUsers(self):
        def users_success(users_list):
            self.app_users = users_list

        def users_failed(err_code, err_msg):
            QtWidgets.QMessageBox.critical(self, "Cannot get application's users list", "Error {0}: {1}".format(err_code, err_msg))

        self.users_worker = UsersWorker()
        self.users_worker.success.connect(users_success)
        self.users_worker.failed.connect(users_failed)
        self.users_worker.log.connect(console.log)
        self.users_worker.start()

    def editApplication(self):
        def schema_success(app_schema):
            import json
            print(json.dumps(app_schema.to_json()))

        def schema_failed(err_code, err_msg):
            QtWidgets.QMessageBox.critical(self, "Schema retrieving error", "Error {0}: {1}".format(err_code, msg))

        self.schema_worker = SchemaWorker()
        self.schema_worker.success.connect(schema_success)
        self.schema_worker.failed.connect(schema_failed)
        self.schema_worker.log.connect(console.log)
        self.schema_worker.start()

    def on_update_context(self, context, notification):
        event = TelepatContextUpdateEvent(context, notification)
        QtWidgets.QApplication.postEvent(self, event)

    def on_add_context(self, context, notification):
        event = TelepatContextAddEvent(context, notification)
        QtWidgets.QApplication.postEvent(self, event)

    def currentAppChanged(self, index):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        app = self.applications[index]
        telepat.app_id = app["id"]
        telepat.api_key = app["keys"][0]
        self.registerDevice()
        self.getUsers()
        self.refreshContexts()

    def filterChanged(self):
        self.proxy.setFilterRegExp(self.filterLineEdit.text())

    def itemSelected(self, index):
        item = self.contexts_model.itemFromIndex(index.model().mapToSource(index))
        if type(item) == ContextItem:
            self.stackedWidget.setCurrentIndex(0)
            self.tableView.editObject(item.context)
        elif type(item) == ModelItem:
            self.stackedWidget.setCurrentIndex(1)
            self.modelBrowser.browseModel(item.parent().context, item.text(), self.app_users)

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
                self.appsCombobox.addItem("{0} ({1})".format(app.name, app.id))
            self.appsCombobox.setDisabled(False)
            self.actionEditApp.setDisabled(False)

        def apps_failed(err_code, msg):
            QtWidgets.QMessageBox.critical(self, "Failed to retrieve applications", "Error {0}: {1}".format(err_code, msg))

        self.apps_worker = ApplicationsWorker(self)
        self.apps_worker.success.connect(apps_success)
        self.apps_worker.failed.connect(apps_failed)
        self.apps_worker.log.connect(console.log)
        self.apps_worker.start()

    def process_context_add_event(self, event):
        application = self.applications[self.appsCombobox.currentIndex()]
        context = event.obj
        if not context.application_id == application["id"]:
            return

        item = ContextItem(Context(context.to_json()))
        item.setEditable(False)
        for key in application:
            subitem = ModelItem(key, Model(application.schema[key].to_json()))
            subitem.setEditable(False)
            item.appendRow(subitem)
        self.contexts_model.appendRow(item)

    def process_context_update_event(self, event):
        context = event.obj
        i = 0
        while self.contexts_model.item(i):
            if context.id == self.contexts_model.item(i).context.id:
                if event.notification.notification_type == NOTIFICATION_TYPE_UPDATED:
                    self.contexts_model.item(i).context = Context(event.obj.to_json())
                    self.tableView.editObject(self.contexts_model.item(i).context)
                    break
            i += 1
            
    def event(self, event):
        if isinstance(event, ExceptionEvent):
            event.callback()
        elif isinstance(event, TelepatContextUpdateEvent):
            self.process_context_update_event(event)
        elif isinstance(event, TelepatContextAddEvent):
            self.process_context_add_event(event)
        return super(TelepatManager, self).event(event)
        
    def excepthook(self, excType, excValue, tracebackobj):
        def show_message():
            notice = \
                """A fatal error occured. Please report this issue on the\n"""\
                """project's GitHub page or via email at nitanovidiu@gmail.com\n"""
            separator = '-' * 80
            errmsg = '%s: \n%s' % (str(excType), str(excValue))
            timeString = time.strftime("%Y-%m-%d, %H:%M:%S")
            tbinfofile = io.StringIO()
            traceback.print_tb(tracebackobj, None, tbinfofile)
            tbinfofile.seek(0)
            tbinfo = tbinfofile.read()
            sections = [separator, timeString, separator, errmsg, separator, tbinfo]
            msg = '\n'.join(sections)
            QtWidgets.QMessageBox.critical(None, "Fatal error", str(notice)+str(msg))
        
        event = ExceptionEvent(TM_EVENT_EXCEPTION)
        event.callback = show_message
        QtWidgets.QApplication.postEvent(self, event)

    def closeEvent(self, event):
        tmsettings.setValue("consoleSplitterSize", self.consoleSplitter.saveState())
        tmsettings.setValue("treeViewSplitterSize", self.treeViewSplitter.saveState())
        super(TelepatManager, self).closeEvent(event)
