from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QTextCursor, QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.uic import loadUi

import logging
import logging.config
import threading
import sys
import multiprocessing
from datetime import datetime
from src.database import DataBase
from src.faceProcess import FaceProcess
from src.userInfoDiaglog import UserInfoDialog


class DataRecordUI(QWidget):
    log_signal = pyqtSignal(str)  # 日志信号
    log_queue = multiprocessing.Queue()  # 日志队列

    def __init__(self):
        super(DataRecordUI, self).__init__()
        loadUi('../ui/DataRecord.ui', self)
        self.setWindowIcon(QIcon('../icons/icon.png'))
        self.setFixedSize(1121, 679)

        # OpenCV
        self.face_process = None

        # 数据库
        self.db = DataBase(self.log_queue)
        # 是否有相应数据库,没有则创建
        self.is_created = False
        self.init_database()

        # 用户信息
        self.user_info_dialog = UserInfoDialog()
        self.is_user_info_ready = False
        self.user_info = {'stu_id': '', 'name': ''}
        self.addOrUpdateUserInfoButton.clicked.connect(self.add_or_update_user_information)
        self.migrateToDbButton.clicked.connect(self.migrate_to_db)

        # 人脸采集
        self.is_face_data_ready = False
        self.is_camera_ok = False
        self.faceRecordButton.clicked.connect(self.start_camera_set)

        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        # 日志系统
        self.log_signal.connect(lambda log: self.log_output(log))
        self.log_output_thread = threading.Thread(target=self.receive_log, daemon=True)
        self.log_output_thread.start()

    def init_database(self):
        """
        检查数据库是否创建
        :return:
        """
        self.is_created = self.db.create_database()
        if self.is_created:
            self.addOrUpdateUserInfoButton.setEnabled(True)

    def add_or_update_user_information(self):
        """
        修改或者更改用户信息
        :return:
        """
        stu_id, name = self.user_info.get('stu_id'), self.user_info.get('name')

        self.user_info_dialog.stuIDLineEdit.setText(stu_id)
        self.user_info_dialog.nameLineEdit.setText(name)
        self.user_info_dialog.okButton.clicked.connect(self.check_to_apply_user_info)
        self.user_info_dialog.show()

        self.migrateToDbButton.setIcon(QIcon())

    def check_to_apply_user_info(self):
        """
        用户信息确认
        :return:
        """
        if not (self.user_info_dialog.stuIDLineEdit.hasAcceptableInput()
                and self.user_info_dialog.nameLineEdit.hasAcceptableInput()):
            self.user_info_dialog.msgLabel.setText('<font color=red>输入有误</font>')
        else:
            # 获取用户输入
            self.user_info['stu_id'] = self.user_info_dialog.stuIDLineEdit.text().strip()
            self.user_info['name'] = self.user_info_dialog.nameLineEdit.text().strip()
            self.user_info['class_']=self.user_info_dialog.classLineEdit.text().strip()
            self.user_info['email'] = self.user_info_dialog.emailLineEdit.text().strip()
            self.user_info['phone'] = self.user_info_dialog.phoneLineEdit.text().strip()
            self.user_info['addr'] = self.user_info_dialog.addrLineEdit.text().strip()

            # 信息确认
            stu_id, name = self.user_info.get('stu_id'), self.user_info.get('name')


            self.stuIDLineEdit.setText(stu_id)
            self.nameLineEdit.setText(name)
            self.is_user_info_ready = True
            # 关闭对话框
            self.user_info_dialog.close()
            # 下一步,可以开始采集
            self.faceRecordButton.setEnabled(True)
            self.addOrUpdateUserInfoButton.setIcon(QIcon('../icons/success.png'))

    def migrate_to_db(self):
        """
        同步用户信息到数据库
        :return:
        """
        if self.is_face_data_ready:
            self.faceRecordButton.setIcon(QIcon('../icons/success.png'))
            stu_id, name = self.user_info.get('stu_id'), self.user_info.get('name')
            class_, email = self.user_info.get('class_'), self.user_info.get('email')
            phone, addr = self.user_info.get('phone'), self.user_info.get('addr')
            is_in_database, migrate_ok = self.db.migrate(stu_id, name,class_,email,phone,addr)
            if is_in_database:
                text = '数据库已存在学号为 <font color=blue>{}</font>记录'.format(stu_id)
                informative_text = '<b>将进行覆盖！</b>'
                self.call_dialog(QMessageBox.Warning, text, informative_text, QMessageBox.Yes | QMessageBox.No)
            if not migrate_ok:
                self.migrateToDbButton.setIcon(QIcon('../icons/error.png'))
            else:
                text = '<font color=blue>{}</font> 已添加/更新到数据库。'.format(stu_id)
                informative_text = '<b><font color=blue>{}</font> 的人脸数据采集已完成！</b>'.format(name)
                self.call_dialog(QMessageBox.Information, text, informative_text, QMessageBox.Ok)
                # 清空用户信息缓存
                for key in self.user_info.keys():
                    self.user_info[key] = ''
                self.is_user_info_ready = False
                self.is_face_data_ready = False
                # 清空历史输入
                self.stuIDLineEdit.clear()
                self.nameLineEdit.clear()
                self.migrateToDbButton.setIcon(QIcon('./icons/success.png'))

                # 允许继续增加新用户
                self.addOrUpdateUserInfoButton.setIcon(QIcon())
                self.addOrUpdateUserInfoButton.setEnabled(True)
                self.faceRecordButton.setIcon(QIcon())
                self.faceRecordButton.setEnabled(False)
                self.migrateToDbButton.setIcon(QIcon('../icons/success.png'))
                self.migrateToDbButton.setEnabled(False)

    def start_camera_set(self):
        """
        打开摄像头
        :return:
        """
        self.face_process = FaceProcess(self.log_queue)
        self.is_camera_ok = self.face_process.start_camera(self.faceRecordButton, self.timer)

    def start_face_record_set(self):
        """
        采集人脸数据
        :return:
        """
        stu_id = self.user_info.get('stu_id')
        if self.is_created:
            if self.is_user_info_ready:
                self.addOrUpdateUserInfoButton.setEnabled(False)
                if self.is_camera_ok:
                    self.face_process.start_face_record(stu_id, self.faceDetectCaptureLabel)

    def update_frame(self):
        """
        更新画面
        :return:
        """
        ret = None
        if self.face_process.face_record_num + 1 == self.face_process.min_face_record_num:
            self.face_process.face_record_num += 1
            text = '已采集完{}张图片'.format(self.face_process.min_face_record_num)
            informative_text = '确定'
            ret = self.call_dialog(QMessageBox.Information, text, informative_text, QMessageBox.Ok)
        if ret == QMessageBox.Ok:
            self.is_created = True
            self.is_face_data_ready = True
            self.is_user_info_ready = True
            self.migrateToDbButton.setIcon(QIcon())
            self.migrateToDbButton.setEnabled(True)
        # 显示
        self.start_face_record_set()

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
        日志输出及记录
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
        msg.setIcon(icon)
        msg.setText(text)
        msg.setFont(DataRecordUI.set_font(10))
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
            if self.face_process:
                self.face_process.cap.release()
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DataRecordUI()
    window.show()
    sys.exit(app.exec_())
