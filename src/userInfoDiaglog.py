import sys

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QIcon, QRegExpValidator, QFontDatabase, QFont
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.uic import loadUi


class UserInfoDialog(QDialog):
    def __init__(self):
        super(UserInfoDialog, self).__init__()
        loadUi('../ui/UserInfoDialog.ui',self)
        self.setWindowIcon(QIcon('../icons/icon.png'))
        self.setFixedSize(629,500)

        # 正则表达式限制输入
        stu_id_regx=QRegExp('^[0-9]{8}$')
        stu_id_validator=QRegExpValidator(stu_id_regx,self.stuIDLineEdit)
        self.stuIDLineEdit.setValidator(stu_id_validator)
        # 姓名
        name_regx=QRegExp('^[\u4e00-\u9fa5|A-Z|a-z]{1,50}$')
        name_validator=QRegExpValidator(name_regx,self.nameLineEdit)
        self.nameLineEdit.setValidator(name_validator)
        # 班级
        class_regx = QRegExp('^[\u4e00-\u9fa5|A-Z|a-z|0-9]{1,50}$')
        class_validator = QRegExpValidator(class_regx, self.classLineEdit)
        self.classLineEdit.setValidator(class_validator)
        #邮箱
        email_regx = QRegExp('^[A-Z|a-z|0-9]{1,50}\@[A-Z|a-z|.]{1,50}$')
        email_validator = QRegExpValidator(email_regx, self.emailLineEdit)
        self.emailLineEdit.setValidator(email_validator)

        # 手机号
        phone_regx = QRegExp('^[0-9]{13}$')
        phone_validator = QRegExpValidator(phone_regx, self.phoneLineEdit)
        self.phoneLineEdit.setValidator(phone_validator)
        # 住址
        addr_regx = QRegExp('^[\u4e00-\u9fa5|A-Z|a-z|0-9]{1,50}$')
        addr_validator = QRegExpValidator(addr_regx, self.addrLineEdit)
        self.addrLineEdit.setValidator(addr_validator)

        # 字体设置
        self.infoBox.setFont(self.set_font(9))
        self.tipLabel.setFont(self.set_font(12))

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

if __name__ == '__main__':
    app=QApplication(sys.argv)
    window=UserInfoDialog()
    window.show()
    sys.exit(app.exec_())

