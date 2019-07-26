import sqlite3
import os
from PyQt5.QtWidgets import QTableWidgetItem
from datetime import datetime


# 找不到训练过的人脸数据库文件
class TrainingDataNotFoundError(FileNotFoundError):
    pass


# 找不到用户数据库文件
class DatabaseNotFoundError(FileNotFoundError):
    pass


# 找不到签到数据库
class SignBaseNotFoundError(FileNotFoundError):
    pass


# 数据库记录不存在
class RecordNotFound(Exception):
    pass


# 取消数据库更新操作
class OperationCancel(Exception):
    pass


class DataBase(object):
    def __init__(self, log_queue):
        # 定义的数据库及数据集
        self.user_db = './FaceBase.db'  # 用户数据库
        self.train_db = '../recognizer/trainingData.yml'  # 训练后的数据
        self.dataset = '../dataset'  # 人脸数据
        self.sign_db = './SignBase.db'  # 签到数据库

        # 日志队列,由调用界面传入
        self.log_queue = log_queue

    def check_database(self):
        """
        检查相关的数据库是否存在
        :return is_db_ready:数据库是否存在
        """
        is_db_ready = True
        try:
            #  数据库文件是否存在
            if not os.path.isfile(self.user_db):
                raise DatabaseNotFoundError
            if not os.path.isfile(self.train_db):
                raise TrainingDataNotFoundError
            if not os.path.isfile(self.sign_db):
                raise DatabaseNotFoundError

            conn = sqlite3.connect(self.user_db)
            cursor = conn.cursor()
            cursor.execute('select count(*) from users')
        except DatabaseNotFoundError:
            self.log_queue.put('Error: can not found user database : {}.'.format(self.user_db))
            is_db_ready = False
        except TrainingDataNotFoundError:
            self.log_queue.put('Error: can not found training database : {}.'.format(self.train_db))
            is_db_ready = False
        except SignBaseNotFoundError:
            self.log_queue.put('Error: can not found sign database: {}.'.format(self.sign_db))
            is_db_ready = False
        except FileNotFoundError:
            self.log_queue.put('Error: file not found error, while check the necessary database.')
            is_db_ready = False
        else:
            cursor.close()
            conn.close()
            self.log_queue.put('Success: found all need database , system will be worked.')
        return is_db_ready

    def query_all(self, table, database):
        """
        根据给定的数据库,返回其中数据,并以特定形式展示出来
        :param table: 展示组件,一般为tableWidget
        :param database: 指定的数据库
        :return query_ok: 是否显示成功
        """
        query_ok = True
        try:
            if not os.path.isfile(database):
                raise FileNotFoundError

            conn = sqlite3.connect(database)
            cursor = conn.cursor()

            res = cursor.execute('select * from users')
            # 先清空table
            while table.rowCount() > 0:
                table.removeRow(0)
            # 展示结果
            for row_index, row_data in enumerate(res):
                table.insertRow(row_index)
                for col_index, col_data in enumerate(row_data):
                    table.setItem(row_index, col_index, QTableWidgetItem(str(col_data)))

            cursor.execute('select count(*) from users')
            result = cursor.fetchone()
            user_count = result[0]
        except FileNotFoundError:
            self.log_queue.put('Error: can not found database : {} , nothing will be displayed.'.format(database))
            query_ok = False
        except Exception as e:
            self.log_queue.put('Error: while query {}, an unexpected error occur.'.format(database))
            query_ok = False
        else:
            cursor.close()
            conn.close()
            self.log_queue.put('Success: found {}  users in {}'.format(user_count, database))
        return query_ok

    def query_user(self, stu_id):
        """
        根据stu_id 查询是数据库user_db
        :param stu_id: 查询学号
        :returns is_user_existed,name,face_id:用户是否存在,姓名,face_id
        """
        name, face_id = None, None
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        is_user_existed = True
        try:
            cursor.execute('select * from users where stu_id=?', (stu_id,))
            ret = cursor.fetchall()
            if not ret:
                raise RecordNotFound
            face_id = ret[0][1]
            name = ret[0][2]
        except RecordNotFound:
            is_user_existed = False
            self.log_queue.put('Error: not found the user {} in database {}'.format(stu_id, self.user_db))
        finally:
            cursor.close()
            conn.close()
        return is_user_existed, name, face_id

    def delete_user(self, stu_id, database):
        """
        根据stu_id删除用户数据
        :param stu_id:查询学号
        :param database: 数据库,可传入user_db,sign_db
        :return is_deleted:是否删除成功
        """
        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        is_deleted = True
        try:
            cursor.execute('delete from users where stu_id=?', (stu_id,))
        except Exception as e:
            cursor.close()
            self.log_queue.put('Error: can not delete user {} from {}, because not found'.format(stu_id, database))
            is_deleted = False
        else:
            self.log_queue.put('Success: delete user {} from {}.'.format(stu_id, database))
            cursor.close()
            conn.commit()
        finally:
            conn.close()
            return is_deleted

    def update_face_id(self, stu_id, face_id):
        """
        更新user_db的训练数据库,标记是否训练
        :param stu_id: 用户学号
        :param face_id: 训练后的face_id,默认为-1
        :return is_update_face_id: face_id是否更新成功
        """
        is_update_face_id = True
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()

        try:
            cursor.execute('select * from users where stu_id=?', (stu_id,))
            ret = cursor.fetchall()
            if not ret:
                raise RecordNotFound
            cursor.execute('update users set face_id=? where stu_id=?', (face_id, stu_id))
        except RecordNotFound:
            self.log_queue.put('Error: can not found the record of {} from {}.'.format(stu_id, self.user_db))
            self.log_queue.put('found {} face data from {}, however ignore.'.format(stu_id, self.dataset))
            is_update_face_id = False
        else:
            self.log_queue.put('Success: update the face_id of {} from {}.'.format(stu_id, self.user_db))
        finally:
            cursor.close()
            conn.commit()
            conn.close()
            return is_update_face_id

    def update_sign_time(self, stu_id):
        """
        根据stu_id更新签到时间
        :param stu_id: 用户学号
        :return is_update_sign_time:是否成功更新签到时间
        """
        is_update_sign_time = True
        conn = sqlite3.connect(self.sign_db)
        cursor = conn.cursor()

        try:
            cursor.execute('select * from users where stu_id=?', (stu_id,))
            ret = cursor.fetchall()
            if not ret:
                raise RecordNotFound
            cursor.execute('update users set signed=?,signed_time=? where stu_id=?',
                           ('是', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stu_id))
        except RecordNotFound:
            self.log_queue.put('Error: can not found the record of {} from {}.'.format(stu_id, self.sign_db))
            is_update_sign_time = False
        else:
            self.log_queue.put('Success: update the signed_time {} from {}.'.format(stu_id, self.sign_db))
        finally:
            cursor.close()
            conn.commit()
            conn.close()
            return is_update_sign_time

    def create_database(self):
        """
        创建数据库user_db,signed_db等
        :return is_created:  是否成功创建
        """
        is_created = True
        if not os.path.exists(self.dataset):
            os.makedirs(self.dataset)
        if not os.path.exists('../recognizer'):
            os.makedirs('../recognizer')
        conn1 = sqlite3.connect(self.user_db)
        cursor1 = conn1.cursor()
        try:
            # 查询数据表,不存在则创建
            cursor1.execute('''CREATE TABLE IF NOT EXISTS users (
                                          stu_id VARCHAR(8) PRIMARY KEY NOT NULL,
                                          face_id INTEGER DEFAULT -1,
                                          name VARCHAR(50) NOT NULL,
                                          created_time DATE DEFAULT (date('now','localtime')),
                                          _class VARCHAR(50) NOT NULL,
                                          email VARCHAR(50) NOT NULL,
                                          phone VARCHAR(50) NOT NULL,
                                          addr VARCHAR(50) NOT NULL
                                          )
                                      ''')
            # 查询表记录数
            cursor1.execute('SELECT Count(*) FROM users')
            result = cursor1.fetchone()
            user_num = result[0]
        except Exception as e:
            self.log_queue.put('Error: can not create database: {}.'.format(self.user_db))
            is_created = False
        else:
            self.log_queue.put(
                'Success: create database {} successfully, found {} users'.format(self.user_db, user_num))
        finally:
            cursor1.close()
            conn1.commit()
            conn1.close()

        conn2 = sqlite3.connect(self.sign_db)
        cursor2 = conn2.cursor()
        try:
            cursor2.execute('''CREATE TABLE IF NOT EXISTS users (
                                                     stu_id VARCHAR(8) PRIMARY KEY NOT NULL,
                                                     name VARCHAR(30) NOT NULL,
                                                     _class  VARCHAR(30) NOT NULL,
                                                     signed VARCHAR(30)   DEFAULT  '否',
                                                     signed_time VARCHAR(50) DEFAULT  '无'
                                                     )
                                                 ''')
            # 查询表记录数
            cursor2.execute('SELECT Count(*) FROM users')
            result = cursor2.fetchone()
            user_count = result[0]
        except Exception as e:
            self.log_queue.put('Error: can not create database: {}.'.format(self.sign_db))
            is_created = False
        else:
            self.log_queue.put(
                'Success: create database {} successfully, found {} users'.format(self.sign_db, user_count))
        finally:
            cursor2.close()
            conn2.commit()
            conn2.close()
        return is_created

    def migrate(self, stu_id, name,class_,email,phone,addr):
        """
        合并数据到数据库user_db,sign_de
        :param stu_id: 用户学号
        :param name: 姓名
        :return is_in_database,migrate_ok: 是否在数据库,是否同步成功
        """
        conn1 = sqlite3.connect(self.user_db)
        cursor1 = conn1.cursor()
        is_in_database = False
        migrate_ok = True
        try:
            cursor1.execute('select * from users where stu_id=?', (stu_id,))
            if cursor1.fetchall():
                is_in_database = True
                # 更新数据库信息
                cursor1.execute('update users set name=?,_class=?,email=?,phone=?,addr=? where stu_id=?', (
                    name,class_,email,phone,addr, stu_id))
            else:
                cursor1.execute('insert into users (stu_id,name,_class,email,phone,addr) values (?,?,?,?,?,?)', (
                    stu_id, name,class_,email,phone,addr))
            cursor1.execute('select count(*) from users')
            result = cursor1.fetchone()
            user_num = result[0]
        except Exception as e:
            self.log_queue.put('Error: can not insert or update to database {}.'.format(self.user_db))
            migrate_ok = False
        else:
            self.log_queue.put('Success: update or insert successfully, found {} users in {}'.format(user_num,
                                                                                                     self.user_db))
        finally:
            cursor1.close()
            conn1.commit()
            conn1.close()

        # sign_db
        conn2 = sqlite3.connect(self.sign_db)
        cursor2 = conn2.cursor()
        try:
            cursor2.execute('select * from users where stu_id=?', (stu_id,))
            if cursor2.fetchall():
                is_in_database = True
                # 更新数据库信息
                cursor2.execute('update users set name=?,_class=? where stu_id=?', (name,class_, stu_id))
            else:
                cursor2.execute('insert into users (stu_id,name,_class) values (?,?,?)', (stu_id, name,class_))
            cursor2.execute('select count(*) from users')
            result = cursor2.fetchone()
            user_count = result[0]
        except Exception as e:
            self.log_queue.put('Error: can not insert or update to database {}.'.format(self.sign_db))
            migrate_ok = False
        else:
            self.log_queue.put('Success: update or insert successfully, found {} users in {}'.format(user_count,
                                                                                                     self.sign_db))
        finally:
            cursor2.close()
            conn2.commit()
            conn2.close()
        return is_in_database, migrate_ok

    def query_by_face_id(self, face_id):
        """
        根据face_id查询数据
        :param face_id: 用户face_id
        :return:
        """
        is_known = True
        stu_id, name, created_time = '', '', ''
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE face_id=?", (face_id,))
            result = cursor.fetchall()
            if result:
                stu_id = result[0][0]
                name = result[0][2]
                created_time = result[0][3]
            else:
                is_known = False
                raise Exception
        except Exception as e:
            self.log_queue.put('Error: can not found user by face_id {}'.format(face_id))
        finally:
            cursor.close()
            conn.close()
            return is_known, stu_id, name, created_time


if __name__ == '__main__':
    pass
    # db = DataBase()
    # print(db.check_database())
