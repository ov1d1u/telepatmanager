from PyQt5 import QtCore
from telepat import TelepatContext, TelepatResponse, TelepatError
from requests.exceptions import ConnectionError
import errors
from models.context import Context
from models.model import Model
from telepat.models import TelepatApplication, TelepatAppSchema, TelepatBaseObject
from telepat.channel import TelepatChannel
from telepat import TelepatTransportNotification

class BaseWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)

    def connection_error(self, e):
        self.log.emit("Connection error: {0}".format(str(e)))
        self.failed.emit(errors.TELEPAT_CONNECTION_ERROR, "Connection error")

class RegisterWorker(BaseWorker):
    success = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(int, str)

    def __init__(self, parent, update=False):
        self.update = update
        super(RegisterWorker, self).__init__(parent)

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        try:
            self.log.emit("Registering device...")
            register_response = telepat.register_device(self.update)
            if not register_response.status_code == 200:
                msg = "Failed to register device"
                if "message" in register_response.json():
                    msg = register_response.json()["message"]
                self.log.emit("Error {0} while registering device: {1}".format(register_response.status_code, msg))
                self.failed.emit(register_response.status_code, msg)
            else:
                self.log.emit("Registered with device id: {0}".format(telepat.device_id))
                self.success.emit()
        except TelepatError as e:
            self.failed.emit(errors.TELEPAT_GENERAL_ERROR, str(e))


class LoginWorker(BaseWorker):
    success = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(int, str)

    def __init__(self, parent, username, password):
        super(LoginWorker, self).__init__(parent)
        self.username = username
        self.password = password

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        try:
            login_response = telepat.login_admin(self.username, self.password)
        except ConnectionError as e:
            self.connection_error(e)
            return
            
        if not login_response.status_code == 200:
            msg = "Failed to login admin"
            if "message" in login_response.json():
                msg = login_response.json()["message"]
            self.log.emit("Error {0} while authenticating user: {1}".format(login_response.status_code, msg))
            self.failed.emit(login_response.status_code, msg)
        else:
            self.log.emit("Successfully authenticated user {0}".format(self.username))
            self.success.emit()


class ContextsWorker(BaseWorker):
    success = QtCore.pyqtSignal(list)
    failed = QtCore.pyqtSignal(int, str)

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        try:
            contexts_response = telepat.get_all()
        except ConnectionError as e:
            self.connection_error(e)
            return
        if not contexts_response.status == 200:
            msg = "Failed to retrieve contexts"
            if contexts_response.message:
                msg = contexts_response.message
            self.log.emit("Error {0} while retrieving contexts: {1}".format(contexts_response.status, msg))
            self.failed.emit(contexts_response.status, msg)
        else:
            contexts_list = contexts_response.getObjectOfType(Context)
            self.log.emit("Successfully retrieved {0} contexts".format(len(contexts_list)))
            self.success.emit(contexts_list)

class SchemaWorker(BaseWorker):
    success = QtCore.pyqtSignal(list)
    failed = QtCore.pyqtSignal(int, str)

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        try:
            schema_response = telepat.get_schema()
        except ConnectionError as e:
            self.connection_error(e)
            return
        if not schema_response.status == 200:
            msg = "Failed to retrieve schema"
            if "message" in schema_response.json():
                msg = schema_response.json()["message"]
            self.log.emit("Error {0} while retrieving schema: {1}".format(schema_response.status_code, msg))
            self.failed.emit(schema_response.status_code, msg)
        else:
            app_schema = schema_response.getObjectOfType(TelepatAppSchema)
            self.log.emit("Successfully retrieved application schema")
            self.success.emit(app_schema)


class ApplicationsWorker(BaseWorker):
    success = QtCore.pyqtSignal(list)
    failed = QtCore.pyqtSignal(int, str)

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        try:
            apps_response = telepat.get_apps()
        except ConnectionError as e:
            self.connection_error(e)
            return
        if not apps_response.status == 200:
            msg = "Failed to retrieve applications"
            if "message" in apps_response.json():
                msg = apps_response.json()["message"]
            self.log.emit("Error {0} while retrieving applications: {1}".format(apps_response.status_code, msg))
            self.failed.emit(apps_response.status_code, msg)
        else:
            apps_list = apps_response.getObjectOfType(TelepatApplication)
            self.log.emit("Successfully retrieved {0} applications".format(len(apps_list)))
            self.success.emit(apps_list)
            
            
class ContextPatchWorker(BaseWorker):
    success = QtCore.pyqtSignal(TelepatResponse)
    failed = QtCore.pyqtSignal(int, str)
    
    def __init__(self, parent, context):
        super(ContextPatchWorker, self).__init__(parent)
        self.context = context
    
    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        try:
            update_response = telepat.update_context(self.context)
        except ConnectionError as e:
            self.connection_error(e)
            return
        if not update_response.status == 200:
            self.log.emit("Error {0} while patching context: {1}".format(update_response.status, update_response.message))
            self.failed.emit(update_response.status, update_response.message)
        else:
            self.log.emit("Object {0} successfully patched".format(self.context.id))
            self.success.emit(update_response)


class SubscribeWorker(BaseWorker):
    success = QtCore.pyqtSignal(TelepatChannel, list)
    failed = QtCore.pyqtSignal(int, str)

    def __init__(self, parent, context, model_name, object_type):
        super(SubscribeWorker, self).__init__(parent)
        self.context = context
        self.model_name = model_name
        self.object_type = object_type

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        channel = None
        subscribe_response = None
        try:
            channel, subscribe_response = telepat.subscribe(self.context, self.model_name, self.object_type)
        except ConnectionError as e:
            self.connection_error(e)
            return
        if not subscribe_response.status == 200:
            self.log.emit("Error {0} while subscribing to {1}".format(subscribe_response.status, self.model_name))
            self.failed.emit(subscribe_response.status, subscribe_response.message)
        else:
            self.log.emit("Successfully subscribed to {0}".format(channel.subscription_identifier()))
            self.success.emit(channel, subscribe_response.getObjectOfType(TelepatBaseObject))

