import logging
import sys
import threading
import webbrowser
import cv2
import multiprocessing
import logging.config
from datetime import datetime

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon, QFontDatabase, QFont
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow, QMessageBox
from PyQt5.uic import loadUi
from src.dataManage import DataManageUI
from src.core import CoreUI
from src.dataRecord import DataRecordUI
from src.faceProcess import FaceProcess
from src.database import DataBase


class StartUI(QWidget):
    log_signal = pyqtSignal(str)  # 日志信号
    log_queue = multiprocessing.Queue()  # 日志队列

    def __init__(self):
        super(StartUI, self).__init__()
        loadUi('../ui/start.ui', self)
        self.setWindowIcon(QIcon('../icons/icon.png'))
        self.setFixedSize(1141, 682)

        # 设置字体

        self.functionBox.setFont(self.set_font(9))
        self.helpBox.setFont(self.set_font(9))
        self.signBox.setFont(self.set_font(9))
        self.label.setFont(self.set_font(24))

        # 数据库
        self.db = DataBase(self.log_queue)
        self.prepare_database()
        self.query_all_sign()  # 显示

        # 主要功能
        self.signButton.clicked.connect(self.core_ui)
        self.faceRecordButton.clicked.connect(self.record_ui)
        self.dataManageButton.clicked.connect(self.data_manage_ui)

        # 帮助与支持
        self.githubButton.clicked.connect(lambda: webbrowser.open('https://github.com/lijinxi1/'))
        self.developerButton.clicked.connect(lambda: webbrowser.open('http://www.yunyi520.top'))

        # 打赏作者
        self.reward_author()

        # 刷新签到情况
        self.flushButton.clicked.connect(self.query_all_sign)

        # 日志系统
        self.log_signal.connect(lambda log: self.log_output(log))
        self.log_output_thread = threading.Thread(target=self.receive_log, daemon=True)
        self.log_output_thread.start()

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

    # 显示微信二维码
    def reward_author(self):
        face_process = FaceProcess(self.log_queue)
        img = cv2.imread('wechat.png')
        face_process.display_image(img, self.wechatLabel)

    @staticmethod
    def core_ui():
        core = CoreUI()
        core.show()

    @staticmethod
    def data_manage_ui():
        data_manage = DataManageUI()
        data_manage.show()

    @staticmethod
    def record_ui():
        record = DataRecordUI()
        record.show()

    def prepare_database(self):
        """
        准备必须的数据库
        :return:
        """
        is_db_ready = self.db.check_database()
        if not is_db_ready:
            is_created = self.db.create_database()
            if not is_created:
                self.log_queue.put('Error: can not initial database.')
            else:
                self.log_queue.put('Success: database have been created already.')

    def query_all_sign(self):
        """
        展示签到的情况
        :return:
        """
        query_ok = self.db.query_all(self.tableWidget, './SignBase.db')
        if query_ok:
            self.log_queue.put('Success: signed data have been shown.')
        else:
            self.log_queue.put('Error: can not show the data in SignBase')

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

    @staticmethod
    def log_output(log):
        """
        记录日志
        :param log:日志
        :return:
        """
        time = datetime.now().strftime('[%Y/%m/%d %H:%M:%S]')
        log = time + ' ' + log + '\n'
        # 记录日志
        logging.info(log)

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
        msg.setIcon(icon)
        msg.setText(text)
        msg.setFont(StartUI.set_font(10))    # 字体
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
        text = '<font color=green ><center>----<b>将退出此程序！</b>----</center></font> '
        informative_text = '<b><center>====>是否要退出？=====<center></b>'
        ret=self.call_dialog(QMessageBox.Question,text,informative_text,QMessageBox.Yes|QMessageBox.No,
                             QMessageBox.No)
        if ret == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    logging.config.fileConfig('../config/logging.cfg')
    app = QApplication(sys.argv)
    window = StartUI()
    window.show()
    sys.exit(app.exec_())
