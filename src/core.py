import logging
import logging.config
import sys
import threading

import multiprocessing
from datetime import datetime

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QTextCursor, QFontDatabase, QFont
from PyQt5.uic import loadUi

from src.database import DataBase
from src.faceProcess import FaceProcess


class CoreUI(QMainWindow):
    log_queue = multiprocessing.Queue()     # 日志队列
    log_signal = pyqtSignal(str)    # log 信号

    def __init__(self):
        super(CoreUI, self).__init__()
        loadUi('../ui/Core.ui', self)
        self.setWindowIcon(QIcon('../icons/icon.png'))
        self.setFixedSize(1136, 676)

        # 检查数据库
        self.db = None
        self.is_db_ready = False
        self.check_database_set()

        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame_set)

        # 点击签到
        self.signButton.clicked.connect(self.start_camera_sign)
        # 图像处理
        self.face_process = None
        self.is_camera_ok = None

        # 日志系统
        self.log_signal.connect(lambda log: self.log_output(log))
        self.log_output_thread = threading.Thread(target=self.receive_log, daemon=True)
        self.log_output_thread.start()

    def check_database_set(self):
        """
        检查数据库是否存在
        :return:
        """
        self.db = DataBase(self.log_queue)
        self.is_db_ready = self.db.check_database()
        self.signButton.setEnabled(True)

    def start_camera_sign(self):
        '''
        打开摄像头
        :return:
        '''
        self.face_process = FaceProcess(self.log_queue)
        self.is_camera_ok = self.face_process.start_camera(self.signButton, self.timer)

    def update_frame_set(self):
        """
        更新显示画面
        :return:
        """
        self.face_process.update_frame(self.realTimeCaptureLabel)

    def receive_log(self):
        """
        处理系统日志
        :return:
        """
        while True:
            data = self.log_queue.get()
            if data:
                self.log_signal.emit(data)
            else:
                continue

    def log_output(self, log):
        """
        log输出及记录
        :param log: 日志
        :return:
        """
        time = datetime.now().strftime('[%Y/%m/%d %H:%M:%S]')
        log = time + ' ' + log + '\n'

        logging.info(log)

        self.logTextEdit.moveCursor(QTextCursor.End)
        self.logTextEdit.insertPlainText(log)
        self.logTextEdit.ensureCursorVisible()  # 自动滚屏

    @staticmethod
    def set_font(font_size):
        """
        设置字体,与运行环境无关
        :param font_size: 字体大小
        :return:
        """
        ttf = QFontDatabase()
        fid = ttf.addApplicationFont('./fzqgjt.ttf')
        font = QFont()
        font.setFamily(ttf.applicationFontFamilies(fid)[0])
        font.setPointSize(font_size)
        return font

    @staticmethod
    def call_dialog(icon, text, inforamtive_text, standard_buttons, defalut_button=None):
        """
        对话框
        :param icon:
        :param text:
        :param inforamtive_text:
        :param standard_buttons:
        :param defalut_button:
        :return:
        """
        msg = QMessageBox()
        msg.setWindowIcon(QIcon('../icons/icon.png'))
        msg.setWindowTitle('OpenCV Face Recognition System - DataManage')
        # msg.setFont('方正启体简体')
        msg.setIcon(icon)
        msg.setText(text)
        msg.setFont(CoreUI.set_font(10))
        msg.setInformativeText(inforamtive_text)
        msg.setStandardButtons(standard_buttons)
        if defalut_button:
            msg.setDefaultButton(defalut_button)
        return msg.exec()

    def closeEvent(self, event) -> None:
        """
        窗口关闭
        :param event:事件
        :return:
        """
        text = '<font color=green ><center>-----<b>将离开此界面！-----</b></center></font> '
        informative_text = '<b><center>=====>是否离开？====</center></b>'
        ret=self.call_dialog(QMessageBox.Question,text,informative_text,QMessageBox.Yes|QMessageBox.No,
                             QMessageBox.No)
        if ret == QtWidgets.QMessageBox.Yes:
            self.timer.stop()
            if  self.face_process:
                self.face_process.cap.release()
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    logging.config.fileConfig('../config/logging.cfg')
    app = QApplication(sys.argv)
    window = CoreUI()
    window.show()
    sys.exit(app.exec())
