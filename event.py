from PyQt5 import QtCore
from const import *

class ExceptionEvent(QtCore.QEvent):
    callback = None


class TelepatObjectEvent(QtCore.QEvent):
    obj = None
    notification = None

    def __init__(self, obj, notification, event_type):
        super(TelepatObjectEvent, self).__init__(event_type)
        self.obj = obj
        self.notification = notification

    def object_id(self):
        return self.obj.id


class TelepatContextUpdateEvent(TelepatObjectEvent):
    def __init__(self, obj, notification):
        super(TelepatContextUpdateEvent, self).__init__(obj, notification, TM_EVENT_ON_UPDATE_CONTEXT)


class TelepatContextAddEvent(TelepatObjectEvent):
    def __init__(self, obj, notification):
        super(TelepatContextAddEvent, self).__init__(obj, notification, TM_EVENT_ON_ADD_CONTEXT)


class TelepatObjectAddEvent(TelepatObjectEvent):
    def __init__(self, obj, notification):
        super(TelepatObjectAddEvent, self).__init__(obj, notification, TM_EVENT_ON_ADD_OBJECT)


class TelepatObjectUpdateEvent(TelepatObjectEvent):
    def __init__(self, obj, notification):
        super(TelepatObjectUpdateEvent, self).__init__(obj, notification, TM_EVENT_ON_UPDATE_OBJECT)


class TelepatObjectDeleteEvent(TelepatObjectEvent):
    def __init__(self, obj, notification):
        super(TelepatObjectDeleteEvent, self).__init__(obj, notification, TM_EVENT_ON_DELETE_OBJECT)