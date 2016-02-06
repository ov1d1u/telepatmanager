from PyQt5 import QtWidgets, QtGui, QtCore, uic
from requests.exceptions import ConnectionError
from telepat import TelepatBaseObject
from workers import BaseWorker, SchemaWorker, SubscribeWorker


class ObjectsWorker(BaseWorker):
    success = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(int, str)
    progress = QtCore.pyqtSignal(int, int)

    def __init__(self, parent, context, models_list):
        super(ObjectsWorker, self).__init__(parent)
        self.context = context
        self.models_list = models_list

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        models_map = {}
        try:
            for model in self.models_list:
                channel, subscribe_response = telepat.subscribe(self.context, model, TelepatBaseObject)
                if subscribe_response.status != 200:
                    self.failed.emit(subscribe_response.status, subscribe_response.message)
                    return
                objects = subscribe_response.getObjectOfType(TelepatBaseObject)
                models_map[model] = objects if isinstance(objects, list) else [objects]
                channel.unsubscribe()
                self.progress.emit(self.models_list.index(model)+1, len(self.models_list))
            self.success.emit(models_map)
        except ConnectionError as e:
            self.connection_error(e)
            return

class ObjectEditor(QtWidgets.QDialog):
    saved = QtCore.pyqtSignal(TelepatBaseObject)

    def __init__(self, parent, context, obj):
        super(ObjectEditor, self).__init__(parent)

        uic.loadUi('objecteditor.ui', self)
        self.edited_object = obj
        self.context = context
        self.related_models = {}

        self.schema_worker = SchemaWorker()
        self.schema_worker.success.connect(self.on_schema_success)
        self.schema_worker.failed.connect(self.on_schema_failed)
        self.schema_worker.start()
        self.progressBar.setValue(0)
        self.buttonBox.setEnabled(False)
        self.tableView.setEnabled(False)

    def on_schema_success(self, app_schema):
        self.app_schema = app_schema
        self.progressBar.setValue(50)
        self.buttonBox.setEnabled(True)
        self.tableView.setEnabled(True)

        relations = []
        for model_name in app_schema:
            if "{0}_id".format(model_name) in self.edited_object:
                relations.append("{0}".format(model_name))

        if len(relations) == 0:
            self.progressBar.setValue(0)
            self.progressBar.hide()
            self.tableView.editObject(self.edited_object)
        else:
            self.objects_worker = ObjectsWorker(self, self.context, relations)
            self.objects_worker.success.connect(self.on_related_objects_success)
            self.objects_worker.failed.connect(self.on_related_objects_failed)
            self.objects_worker.progress.connect(self.on_related_objects_progress)
            self.objects_worker.start()

    def on_schema_failed(self, err_code, err_msg):
        QtWidgets.QMessageBox.critical(self, "Schema retrieving error", "Error {0}: {1}".format(err_code, msg))

    def on_related_objects_success(self, objects_map):
        self.progressBar.setValue(0)
        self.progressBar.hide()
        self.tableView.editObject(self.edited_object, objects_map)

    def on_related_objects_failed(self, err_code, err_msg):
        QtWidgets.QMessageBox.critical(self, "Objects retrieval errror", "Error {0}: {1}".format(err_code, err_msg))

    def on_related_objects_progress(self, value, total):
        progress = value/total*50
        self.progressBar.setValue(50+progress)

    def accept(self):
        self.saved.emit(self.edited_object)
        super(ObjectEditor, self).accept()