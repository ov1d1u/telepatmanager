import threading
import requests
import shelve
import uuid
import platform
import json
import hashlib
from jsonobject import *
from os.path import expanduser
from socketIO_client import SocketIO

home = expanduser("~")

class TelepatError(Exception):
    pass


class TelepatBaseObject(JsonObject):
    object_id = StringProperty()
    context = None
    model = ""

    def patch_against(self, updated_obj):
        if not isinstance(updated_obj, TelepatBaseObject):
            raise TelepatError("The received object is not the same as the current one")
        patch = {
            "model": self.model,
            "id": self.object_id,
            "context": self.context.id
        }
        patches = []
        # Deleted keys
        deletions = list(set(self.keys()) - set(updated_obj.keys()))
        for del_prop in deletions:
            del_patch = {
                "op": "delete",
                "path": "{0}/{1}/{2}".format(self.model, self.object_id, del_prop)
            }
            patches.append(deletions)

        for key in list(updated_obj.keys()):
            if not updated_obj[key] == self[key]:
                replace_patch = {
                    "op": "replace",
                    "path": "{0}/{1}/{2}".format(self.model, self.object_id, key),
                    "value": updated_obj[key]
                }
                patches.append(replace_patch)

        patch["patches"] = patches
        return patch

class TelepatContext(TelepatBaseObject):
    name = StringProperty()
    id = StringProperty()
    state = IntegerProperty()
    meta = DictProperty()

    def patch_against(self, updated_obj):
        if not isinstance(updated_obj, TelepatContext):
            raise TelepatError("The received object is not the same as the current one")
        patch = {
            "id": self.id
        }
        patches = []
        # Deleted keys
        deletions = list(set(self.keys()) - set(updated_obj.keys()))
        for del_prop in deletions:
            del_patch = {
                "op": "delete",
                "path": "context/{0}/{1}".format(self.id, del_prop)
            }
            patches.append(deletions)

        for key in list(updated_obj.keys()):
            if not updated_obj[key] == self[key]:
                replace_patch = {
                    "op": "replace",
                    "path": "context/{0}/{1}".format(self.id, key),
                    "value": updated_obj[key]
                }
                patches.append(replace_patch)

        patch["patches"] = patches
        return patch


class TelepatResponse:
    def __init__(self, response):
        self.status = response.status_code
        self.json_data = response.json()
        self.content = self.json_data["content"] if "content" in self.json_data else None
        self.message = self.json_data["message"] if "message" in self.json_data else "" 

    def getObjectOfType(self, class_type):
        if type(self.content) == list:
            objects = []
            for json_dict in self.content:
                objects.append(class_type(json_dict))
            return objects
        else:
            return class_type(self.content)


class TelepatDB:
    db_name = "TELEPAT_OPERATIONS"
    db_op_prefix = "TP_OPERATIONS_"
    db_objects_prefix = "TP_OBJECTS_"

    def __init__(self):
        self.db = shelve.open("{0}/{1}".format(home, ".telepat.db"))

    def prefixForChannel(self, channel_id):
        return "{0}{1}".format(self.db_objects_prefix, channel_id)

    def keyForObject(self, object_id, channel_id):
        return "{0}:{1}".format(self.prefixForChannel(channel_id), object_id)

    def objectExists(self, object_id, channel_id):
        return self.keyForObject(object_id, channel_id) in self.db

    def get_object(self, object_id, channel_id):
        object_key = self.keyForObject(object_id, channel_id)
        return self.db[object_key] if object_id in self.db else None

    def objects_in_channel(self, channel_id):
        return self.db[channel_id] if channel_id in self.db else []

    def set_operations_data(self, key, obj):
        self.db["{0}{1}".format(self.db_op_prefix, key)] = obj
        self.db.sync()

    def get_operations_data(self, key):
        op_key = "{0}{1}".format(self.db_op_prefix, key)
        return self.db[op_key] if op_key in self.db else None

    def persist_object(self, obj, channel_id):
        self.db[self.keyForObject(obj.object_id, channel_id)] = obj
        self.db.sync()

    def persist_objects(self, objects, channel_id):
        self.db[channel_id] = objects
        self.db.sync()

    def delete_objects(self, channel_id):
        del self.db[channel_id]

    def empty(self):
        self.db.clear()


class Telepat(object):
    def __init__(self, remote_url, sockets_url):
        self.device_id = ""
        self.token = ""
        self.app_id = ""
        self.bearer = ""
        self._api_key = ""
        self._remote_url = ""
        self._mServerContexts = {}

        self.remote_url = remote_url
        self.sockets_url = sockets_url

        self.db = TelepatDB()
        if self.db.get_operations_data("device_id"):
            self.device_id = self.db.get_operations_data("device_id")

        self.token_event = threading.Event()
        self.ws_thread = threading.Thread(target=self._start_ws)
        self.ws_thread.start()

    def _start_ws(self):
        def on_socket_welcome(*args):
            response_data = args[0]
            self.token = response_data['sessionId']
            print("Received sessionId: {0}".format(self.token))
            self.token_event.set()

        def on_socket_message(*args):
            print("Received ws message: {0}".format(args[0]))

        self.socketIO = SocketIO(self.sockets_url, 80)
        self.socketIO.on('message', on_socket_message)
        self.socketIO.on('welcome', on_socket_welcome)
        self.socketIO.wait()

    def _headers_with_headers(self, headers):
        new_headers = {}
        new_headers["Content-Type"] = "application/json"
        new_headers["X-BLGREQ-UDID"] = self.device_id
        new_headers["X-BLGREQ-SIGN"] = self.api_key
        new_headers["X-BLGREQ-APPID"] = self.app_id
        if self.bearer:
            new_headers["Authorization"] = "Bearer {0}".format(self.bearer)
        if headers:
            return dict(list(new_headers.items()) + list(headers.items()))
        else:
            return new_headers

    def _url(self, endpoint):
        return "{0}{1}".format(self.remote_url, endpoint)

    def _get(self, endpoint, parameters, headers):
        return requests.get(self._url(endpoint), params=parameters, headers=self._headers_with_headers(headers))

    def _post(self, endpoint, parameters, headers):
        return requests.post(self._url(endpoint), data=json.dumps(parameters), headers=self._headers_with_headers(headers))

    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        self._api_key = hashlib.sha256(value.encode()).hexdigest()

    @property
    def remote_url(self):
        return self._remote_url

    @remote_url.setter
    def remote_url(self, value):
        self._remote_url = value[:-1] if value.endswith("/") else value

    def context_map(self):
        return self._mServerContexts

    def register_device(self, update=False):
        self.token_event.wait(15)
        if not self.token:
            if hasattr(self, "socketIO"):
                self.socketIO.disconnect()
            raise TelepatError('Websocket connection failed')
        params = {}
        info = {"os": platform.system(),
                "version": platform.release()
        }
        if not update: info["udid"] = str(uuid.uuid4())
        params["info"] = info
        params["volatile"] = {
            "type": "sockets",
            "token": self.token,
            "active": 1
        }
        response = self._post("/device/register", params, {})
        if response.status_code == 200:
            response_json = response.json()
            if "identifier" in response_json["content"]:
                device_id = response_json["content"]["identifier"]
                self.db.set_operations_data("device_id", device_id)
        print(response)
        return response

    def login_admin(self, username, password):
        params = {
            "email": username,
            "password": password
        }
        response = self._post("/admin/login", params, {})
        if response.status_code == 200:
            self.bearer = response.json()["content"]["token"]
        return response

    def get_apps(self):
        return self._get("/admin/apps", {}, {})

    def get_schema(self):
        return self._get("/admin/schema/all", {}, {})

    def get_all(self):
        response = self._get("/admin/contexts", {}, {})
        contexts_response = TelepatResponse(response)
        for context in contexts_response.getObjectOfType(TelepatContext):
            self._mServerContexts[context.id] = context
        return contexts_response

    def update_context(self, updated_context):
        context = self.context_map()[updated_context.id]
        return TelepatResponse(self._post("/admin/context/update", context.patch_against(updated_context), {}))