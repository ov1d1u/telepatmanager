from PyQt5 import QtCore
from telepat import TelepatContext, TelepatResponse

class BaseWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)


class RegisterWorker(BaseWorker):
    success = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(int, str)

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        try:
            self.log.emit("Registering device...")
            register_response = telepat.register_device()
            if not register_response.status_code == 200:
                msg = "Failed to register device"
                if "message" in register_response.json():
                    msg = register_response.json()["message"]
                self.log.emit("Error {0} while registering device: {1}".format(register_response.status_code, msg))
                self.failed.emit(register_response.status_code, msg)
            else:
                self.log.emit("Registered with device id: {0}".format(telepat.device_id))
                self.success.emit()
        except telepat.TelepatError as e:
            self.failed.emit(900, str(e))


class LoginWorker(BaseWorker):
    success = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(int, str)

    def __init__(self, parent, username, password):
        super(LoginWorker, self).__init__(parent)
        self.username = username
        self.password = password

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        login_response = telepat.login_admin(self.username, self.password)
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
        contexts_response = telepat.get_all()
        if not contexts_response.status == 200:
            msg = "Failed to retrieve contexts"
            if contexts_response.message:
                msg = contexts_response.message
            self.log.emit("Error {0} while retrieving contexts: {1}".format(contexts_response.status, msg))
            self.failed.emit(contexts_response.status, msg)
        else:
            contexts_list = contexts_response.getObjectOfType(TelepatContext)
            self.log.emit("Successfully retrieved {0} contexts".format(len(contexts_list)))
            self.success.emit(contexts_list)

class SchemaWorker(BaseWorker):
    success = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(int, str)

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        schema_response = telepat.get_schema()
        if not schema_response.status_code == 200:
            msg = "Failed to retrieve schema"
            if "message" in schema_response.json():
                msg = schema_response.json()["message"]
            self.log.emit("Error {0} while retrieving schema: {1}".format(schema_response.status_code, msg))
            self.failed.emit(schema_response.status_code, msg)
        else:
            models_dict = schema_response.json()
            self.log.emit("Successfully retrieved application schema")
            self.success.emit(models_dict["content"])


class ApplicationsWorker(BaseWorker):
    success = QtCore.pyqtSignal(list)
    failed = QtCore.pyqtSignal(int, str)

    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        apps_response = telepat.get_apps()
        if not apps_response.status_code == 200:
            msg = "Failed to retrieve applications"
            if "message" in apps_response.json():
                msg = apps_response.json()["message"]
            self.log.emit("Error {0} while retrieving applications: {1}".format(apps_response.status_code, msg))
            self.failed.emit(apps_response.status_code, msg)
        else:
            apps_list = apps_response.json()
            self.log.emit("Successfully retrieved {0} applications".format(len(apps_list)))
            self.success.emit(apps_list["content"])
            
            
class ContextPatchWorker(BaseWorker):
    success = QtCore.pyqtSignal(TelepatResponse)
    failed = QtCore.pyqtSignal(int, str)
    
    def __init__(self, parent, context):
        super(ContextPatchWorker, self).__init__(parent)
        self.context = context
    
    def run(self):
        telepat = QtCore.QCoreApplication.instance().telepat_instance
        update_response = telepat.update_context(self.context)
        if not update_response.status == 200:
            self.log.emit("Error {0} while patching context: {1}".format(update_response.status, update_response.message))
            self.failed.emit(update_response.status, update_response.message)
        else:
            self.log.emit("Object {0} successfully patched".format(self.context.id))
            self.success.emit(update_response)
