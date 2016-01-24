log_widget = None

def log(line):
	if log_widget:
		text = log_widget.toPlainText()
		if text:
			log_widget.setPlainText("{0}\n{1}".format(text, line))
		else:
			log_widget.setPlainText("{0}".format(line))
		log_widget.verticalScrollBar().setValue(log_widget.verticalScrollBar().maximum())

def set_widget(widget):
	global log_widget
	log_widget = widget
