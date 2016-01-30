from PyQt5 import QtCore
from const import TM_EVENT_ON_UPDATE_CONTEXT


class ExceptionEvent(QtCore.QEvent):
    callback = None


class TelepatObjectEvent(QtCore.QEvent):
	updated_object = None
	notification = None

	def __init__(self, updated_object, notification):
		super(TelepatObjectEvent, self).__init__(TM_EVENT_ON_UPDATE_CONTEXT)
		self.updated_object = updated_object
		self.notification = notification

	def object_id(self):
		return self.updated_object.id