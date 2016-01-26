#! /usr/bin/env python
from PyQt5 import QtGui, QtWidgets, QtCore, uic
from settings import tmsettings
from workers import *
import console
from telepat import Telepat


class ConnectionEditor(QtWidgets.QDialog):
    success = QtCore.pyqtSignal()

    def __init__(self, parent=None, connection_dict=None):
        super(ConnectionEditor, self).__init__(parent)

        self.contexts_list = []

        uic.loadUi('conneditor.ui', self)
        self.serverUrl.textEdited.connect(self.reset_lineedit)
        self.socketsUrl.textEdited.connect(self.reset_lineedit)
        self.adminUsername.textEdited.connect(self.reset_lineedit)
        self.adminPassword.textEdited.connect(self.reset_lineedit)

        if connection_dict:
            self.serverUrl.setText(connection_dict["url"])
            self.socketsUrl.setText(connection_dict["ws_url"])
            self.adminUsername.setText(connection_dict["username"])
            self.adminPassword.setText(connection_dict["password"])

    def reset_lineedit(self):
        self.sender().setStyleSheet("")
        self.sender().setPlaceholderText("")

    def save_connection(self):
        connection_dict = {
            "url" : self.serverUrl.text(),
            "ws_url": self.socketsUrl.text(),
            "username": self.adminUsername.text(),
            "password": self.adminPassword.text() 
        }

        if tmsettings.value("recentConnections"):
            history_list = tmsettings.value("recentConnections")
            if not connection_dict in history_list:
                history_list.append(connection_dict)
                tmsettings.setValue("recentConnections", history_list)
        else:
            tmsettings.setValue("recentConnections", [connection_dict])

    def accept(self):
        error = False
        if len(self.serverUrl.text()) == 0:
            self.serverUrl.setStyleSheet("QLineEdit { background: #FF6666; }");
            self.serverUrl.setPlaceholderText("Please provide a valid URL to a Telepat instance.")
            error = True
        if len(self.socketsUrl.text()) == 0:
            self.socketsUrl.setStyleSheet("QLineEdit { background: #FF6666; }");
            self.socketsUrl.setPlaceholderText("Please provide a valid URL to a Telepat WebSockets instance.")
            error = True
        if len(self.adminUsername.text()) == 0:
            self.adminUsername.setStyleSheet("QLineEdit { background: #FF6666; }");
            self.adminUsername.setPlaceholderText("Please provide an admin account username.")
            error = True
        if len(self.adminPassword.text()) == 0:
            self.adminPassword.setStyleSheet("QLineEdit { background: #FF6666; }");
            self.adminPassword.setPlaceholderText("Please provide an admin account password.")
            error = True
        if error:
            return

        self.status_label.setText("Status: Connecting")
        if QtCore.QCoreApplication.instance().telepat_instance:
            QtCore.QCoreApplication.instance().telepat_instance.disconnect()
        QtCore.QCoreApplication.instance().telepat_instance = Telepat(self.serverUrl.text(), self.socketsUrl.text())
        self.login_worker = LoginWorker(self, self.adminUsername.text(), self.adminPassword.text())
        self.login_worker.success.connect(self.login_success)
        self.login_worker.failed.connect(self.login_failed)
        self.login_worker.log.connect(console.log)
        self.login_worker.start()

    def login_success(self):
        self.save_connection()
        self.success.emit()
        super(ConnectionEditor, self).accept()

    def login_failed(self, err_code, message):
        self.status_label.setText("Status: Authentication error")
        errorDialog = QtWidgets.QMessageBox.critical(self, "Login error", "Error {0}: {1}".format(err_code, message))
