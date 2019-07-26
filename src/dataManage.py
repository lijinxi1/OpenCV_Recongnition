from PyQt5.QtCore import pyqtSignal, QRegExp
from PyQt5.QtGui import QIcon, QTextCursor, QRegExpValidator, QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QAbstractItemView
from PyQt5.uic import loadUi

import logging
import logging.config
import os
import shutil
import sys
import threading
import multiprocessing

from datetime import datetime

from PyQt5 import QtWidgets

from src.database import DataBase
from src.faceProcess import FaceProcess


class DataManageUI(QWidget):
    log_queue = multiprocessing.Queue()  # 日志队列
    log_signal = pyqtSignal(str)  # 日志信号

    def __init__(self):
        super(DataManageUI, self).__init__()
        loadUi('../ui/DataManage.ui', self)
        self.setWindowIcon(QIcon('../icons/icon.png'))
        self.setFixedSize(1111, 689)

        # 设置字体
        self.dbManageGroupBox.setFont(self.set_font(9))
        self.faceDbGroupBox.setFont(self.set_font(9))

        # 正则表达式限制输入
        stu_id_regx = QRegExp('^[0-9]{8}$')
        stu_id_validator = QRegExpValidator(stu_id_regx, self.queryUserLineEdit)
        self.queryUserLineEdit.setValidator(stu_id_validator)

        # 设置tableWidget只读
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # 数据库,记录数据库操作日志
        self.db = DataBase(self.log_queue)  # 传入日志队列

        # 展示数据库所有数据,显示在tableWidget
        self.query_all_set()

        # 用户管理
        # 查询用户
        self.queryUserButton.clicked.connect(self.query_user_set)
        # 删除用户
        self.deleteUserButton.clicked.connect(self.delete_user_set)

        # 训练人脸数据
        self.face_process = FaceProcess(self.log_queue)
        self.trainButton.clicked.connect(self.train_set)

        # 系统日志
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
    # 展示数据库中已有数据
    def query_all_set(self):
        """
        展示数据库中的数据在table中,user_db
        :return:
        """
        query_ok = self.db.query_all(self.tableWidget, 'FaceBase.db')
        if query_ok:
            # 下一步操作,训练 or 查询
            self.trainButton.setToolTip('')
            self.trainButton.setEnabled(True)
            self.queryUserButton.setToolTip('')
            self.queryUserButton.setEnabled(True)

    # 查询用户
    def query_user_set(self):
        """
        根据stu_id查询,在user_db
        :return:
        """
        stu_id = self.queryUserLineEdit.text().strip()
        is_user_existed, name, face_id = self.db.query_user(stu_id)
        if is_user_existed:
            self.queryUserButton.setIcon(QIcon('../icons/success.png'))
            self.stuIDLineEdit.setText(stu_id)
            self.nameLineEdit.setText(name)
            self.faceIDLineEdit.setText(str(face_id))
            # 下一步,可删除
            self.deleteUserButton.setEnabled(True)
        else:
            self.queryUserButton.setIcon(QIcon('../icons/error.png'))

    def delete_user_set(self):
        """
        根据stu_id删除用户,user_db和sign_db
        :return:
        """
        text = '从数据库中删除该用户和相应人脸数据？'
        informative_text = '<b>是否继续？</b>'
        ret = DataManageUI.call_dialog(QMessageBox.Warning, text, informative_text, QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
        if ret == QMessageBox.Yes:
            stu_id = self.stuIDLineEdit.text()
            is_deleted1 = self.db.delete_user(stu_id, './FaceBase.db')
            is_deleted2 = self.db.delete_user(stu_id, './SignBase.db')
            if is_deleted1 and is_deleted2:
                text = '成功删除学号: <font color=blue>{}</font> '.format(stu_id)
                informative_text = '<b>请重新训练！</b>'
                self.call_dialog(QMessageBox.Information, text, informative_text, QMessageBox.Ok)

                # 清空记录值
                self.stuIDLineEdit.clear()
                self.nameLineEdit.clear()
                self.faceIDLineEdit.clear()
                self.queryUserLineEdit.clear()
                # 更新table展示数据
                self.query_all_set()
                self.deleteUserButton.setIcon(QIcon('../icons/success.png'))
                self.queryUserButton.setIcon(QIcon())
                self.deleteUserButton.setIcon(QIcon())
                self.deleteUserButton.setEnabled(False)
                self.trainButton.setIcon(QIcon())
                # 删除相关人脸数据
                if os.path.exists('{}/stu_{}'.format('../dataset', stu_id)):
                    try:
                        shutil.rmtree('{}/stu_{}'.format('../dataset', stu_id))
                    except Exception as e:
                        self.log_queue.put('Error: can not delete {}/stu_{}'.format('../dataset', stu_id))
            else:
                self.deleteUserButton.setIcon(QIcon('../icons/error.png'))

    def train_set(self):
        """
        训练数据
        :return:
        """
        text = '开始训练/界面会暂停响应一段时间'
        informative_text = '<b>是否继续？</b>'
        ret = DataManageUI.call_dialog(QMessageBox.Question, text, informative_text,
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
        if ret == QMessageBox.Yes:
            is_trained = self.face_process.train()
            if is_trained:
                text = '<font color=green><b>Success!</b></font> 训练完成:../recognizer/trainingData.yml'
                informative_text = '<b>人脸数据训练完成！</b>'
                self.call_dialog(QMessageBox.Information, text, informative_text, QMessageBox.Ok)
                self.trainButton.setIcon(QIcon('../icons/success.png'))
                # 刷新数据展示
                self.query_all_set()
            else:
                self.trainButton.setIcon(QIcon('../icons/error.png'))

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
        :param log:
        :return:
        """
        time = datetime.now().strftime('[%Y/%m/%d %H:%M:%S]')
        log = time + ' ' + log + '\n'

        logging.info(log)

        self.logTextEdit.moveCursor(QTextCursor.End)
        self.logTextEdit.insertPlainText(log)
        self.logTextEdit.ensureCursorVisible()  # 自动滚屏

    @staticmethod
    def call_dialog(icon, text, inforamtive_text, standard_buttons, defalut_button=None):
        """
        对话框
        :param icon: 图标
        :param text: 文字
        :param inforamtive_text:文字
        :param standard_buttons: 按钮
        :param defalut_button: 按钮
        :return:
        """
        msg = QMessageBox()
        msg.setWindowIcon(QIcon('../icons/icon.png'))
        msg.setWindowTitle('OpenCV Face Recognition System - DataManage')
        msg.setIcon(icon)
        msg.setText(text)
        msg.setFont(DataManageUI.set_font(10))
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
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    logging.config.fileConfig('../config/logging.cfg')
    app = QApplication(sys.argv)
    window = DataManageUI()
    window.show()
    sys.exit(app.exec())
