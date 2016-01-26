#! /usr/bin/env python
import os
import sys
from PyQt5 import QtWidgets
from telepatmanager import TelepatManager

class TelepatManagerApplication(QtWidgets.QApplication):
    telepat_instance = None
    
    def __init__(self, args):
        super(TelepatManagerApplication, self).__init__(args)

if __name__ == "__main__":
    app = TelepatManagerApplication(sys.argv)
    win = TelepatManager()
    win.show()
    sys.excepthook = win.excepthook
    os._exit(app.exec_())
