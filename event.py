from PyQt5 import QtCore
from const import TM_EVENT_ON_ADD_CONTEXT, TM_EVENT_ON_UPDATE_CONTEXT


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