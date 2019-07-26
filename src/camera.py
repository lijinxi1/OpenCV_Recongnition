# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'camera.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow


class Ui_camera(object):
    def setupUi(self, camera):
        camera.setObjectName("camera")
        camera.resize(250, 315)

        self.retranslateUi(camera)
        QtCore.QMetaObject.connectSlotsByName(camera)

    def retranslateUi(self, camera):
        _translate = QtCore.QCoreApplication.translate
        camera.setWindowTitle(_translate("camera", "Form"))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_camera()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
