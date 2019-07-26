import cv2
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtGui import QImage, QPixmap
from src.database import DataBase


# 检测过程有干扰
class RecordDisturbance(Exception):
    pass


class FaceProcess(object):
    min_face_record_num = 200  # 采集数量
    face_record_num = 0  # 记录当前采集数目
    cap = cv2.VideoCapture()  # 摄像头
    recognizer = None  # 识别器
    face_cascade = None
    signed = []  # 记录签到的人脸

    def __init__(self, log_queue):
        super(FaceProcess, self).__init__()
        self.log_queue = log_queue
        self.db = DataBase(log_queue)
        self.confidenceThreshold = 50  # 置信度阈值,越小精度越高
        self.is_train_data_loaded = False  # 训练数据加载
        self.is_face_detect_load = False  # 识别数据加载

    @staticmethod
    def change_cv2_draw(image, str, local, sizes, colour):
        """
        给图片添加文字
        :param image: 输入的图像,已读取
        :param str: 添加的字符
        :param local: 位置
        :param sizes: 字体大小,单位px
        :param colour: 颜色RGB
        :return image:添加文字的图像
        """
        cv2img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(cv2img)
        draw = ImageDraw.Draw(pil_img)  # 图片上打印
        font = ImageFont.truetype('fzqgjt.ttf', sizes, encoding="utf-8")  # 加载字体
        draw.text(local, str, colour, font=font)
        image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return image

    def detect_face(self, img):
        """
        检测人脸
        :param img:输入的图像帧
        :return :返回人脸位置,及脸部图像
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 直方图均衡化
        gray = cv2.equalizeHist(gray)
        if not self.is_face_detect_load:
            self.face_cascade = cv2.CascadeClassifier('../haarcascades/haarcascade_frontalface_default.xml')
            self.is_face_detect_load = True
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(90, 90))
        if len(faces) == 0:
            return None, None
        try:
            if len(faces) > 1:
                raise RecordDisturbance
        except RecordDisturbance:
            self.log_queue.put('Error: detect more one face ,please try again.')
            return None, None
        (x, y, w, h) = faces[0]
        return (x, y, w, h), gray[y:y + h, x:x + w]

    def face_detect_update(self):
        """
        检测人脸,识别信息,更新输出
        :return frame: 处理过得画面帧,是否识别
        """
        if not self.cap.isOpened():
            self.cap.open(cv2.CAP_DSHOW + 0)
        ret, frame = self.cap.read()
        face, gray = self.detect_face(frame)
        # 加载数据
        if not self.is_train_data_loaded and os.path.isfile('../recognizer/trainingData.yml'):
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.recognizer.read('../recognizer/trainingData.yml')
            self.is_train_data_loaded = True
        if face:
            gray = cv2.resize(gray, (200, 200))
            (x, y, w, h) = face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (232, 138, 30), 1)
            gray = np.array(gray, 'uint8')  # 图片数据转换
            face_id, confidence = self.recognizer.predict(gray)
            if confidence > self.confidenceThreshold:
                is_known, stu_id, name, created_time = self.db.query_by_face_id(face_id)
                if is_known:
                    if stu_id :
                        if stu_id not in self.signed:
                            self.signed.append(stu_id)
                            self.db.update_sign_time(stu_id)
                            self.log_queue.put('Success: signed successfully , can go away !')
                        frame = self.change_cv2_draw(frame, 'stu_id: ' + str(stu_id), (x + w + 5, y), 20, (0, 0, 255))
                        frame = self.change_cv2_draw(frame, 'face_id: ' + str(face_id), (x + w + 5, y + 25), 20,
                                                     (0, 0, 255))
                        frame = self.change_cv2_draw(frame, 'name: ' + str(name), (x + w + 5, y + 50), 20, (0, 0, 255))
                        frame = self.change_cv2_draw(frame, '签到成功 ', (x + w + 5, y + 75), 20,
                                                     (0, 0, 255))

                else:
                    frame = self.change_cv2_draw(frame, 'Unknown', (x + w + 5, y), 20, (255, 0, 0))
        return frame

    def prepare_train_data(self, data_folder_path):
        """
        准备训练数据
        :param data_folder_path: 文件目录
        :returns faces,labels: 人脸数据,标签
        """
        dirs = os.listdir(data_folder_path)

        faces = []
        labels = []
        face_id = 1
        for dir_name in dirs:
            if not dir_name.startswith('stu_'):
                continue
            stu_id = dir_name.replace('stu_', '')
            self.db.update_face_id(stu_id, face_id)  # 更新face_id
            subject_dir_path = os.path.join(data_folder_path, dir_name)
            subject_images_names = os.listdir(subject_dir_path)
            for image_name in subject_images_names:
                if image_name.startswith('.'):
                    continue
                image_path = os.path.join(subject_dir_path, image_name)
                image = Image.open(image_path).convert('L')
                image = np.array(image, 'uint8')
                faces.append(image)
                labels.append(face_id)
        face_id += 1
        return faces, labels

    def train(self):
        """
        训练数据
        :return is_trained: 是否训练成功
        """
        is_trained = True
        try:
            # 人脸数据集合
            if not os.path.exists('../dataset'):
                raise FileNotFoundError
            face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            faces, labels = self.prepare_train_data('../dataset')

            face_recognizer.train(faces, np.array(labels))
            face_recognizer.save('../recognizer/trainingData.yml')  # 保存
        except FileNotFoundError:
            self.log_queue.put('Error: can not found face data dir {}'.format('../dataset'))
            is_trained = False
        except Exception as e:
            self.log_queue.put('Error: failed to train.')
            is_trained = False
        else:
            self.log_queue.put('Success: train finished successful.')
        return is_trained

    def start_camera(self, status, timer):
        """
        打开摄像头,启动定时器,更新画面
        :param status: 按钮点击状态
        :param timer: 定时器
        :return is_camera_ok:是否成功打开摄像头
        """
        is_camera_ok = True
        if status:
            if not self.cap.isOpened():
                self.cap.open(cv2.CAP_DSHOW + 0)
                # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 511)
            ret, frame = self.cap.read()
            if not ret:
                is_camera_ok = False
                self.log_queue.put('Error: can not open camera, please check it.')
                self.cap.release()
            else:
                timer.start(5)  # 启动定时器
                self.log_queue.put('Success: camera opened, start the timer.')
            return is_camera_ok
        else:
            if self.cap.isOpened():
                if timer.isActive():
                    timer.stop()
                self.cap.release()
                self.log_queue.put('Error: have not opened camera.')
            return False

    def start_face_record(self, stu_id, label):
        """
        开始采集脸部数据
        :param stu_id: 用户学号
        :param label: 用于展示的label标签
        :return:
        """
        is_face_record = True
        if self.face_record_num < self.min_face_record_num:
            if not self.cap.isOpened():
                self.cap.open(cv2.CAP_DSHOW + 0)
            ret, frame = self.cap.read()
            face, gray = self.detect_face(frame)
            try:
                if not os.path.exists('{}/stu_{}'.format('../dataset', stu_id)):
                    os.makedirs('{}/stu_{}'.format('../dataset', stu_id))
                if face:
                    x, y, w, h = face
                    gray = cv2.resize(gray, (200, 200))
                    cv2.imwrite('{}/stu_{}/img.{}.jpg'.format('../dataset', stu_id, self.face_record_num + 1),
                                gray)
                    if self.face_record_num % 10 == 0:
                        self.log_queue.put('collect {} images, {} are need.'.format(self.face_record_num + 1,
                                                                                    self.min_face_record_num))
                else:
                    is_face_record = False
            except Exception as e:
                self.log_queue.put('Error: cant write images .')
            else:
                if is_face_record:
                    self.face_record_num += 1
                    cv2.rectangle(frame, (x - 5, y - 5), (x + w + 10, y + h + 10), (0, 0, 255), 2)
                self.display_image(frame, label)  # 展示数据
        else:
            ret, frame = self.cap.read()
            self.face_record_num += 1
            self.display_image(frame, label)  # 展示原本画面帧

    def update_frame(self, label):
        """
        展示画面帧到指定位置,在core中使用
        :param label: 控件
        :return:
        """
        if self.cap.isOpened():
            real_time_frame = self.face_detect_update()
            self.display_image(real_time_frame, label)

    @staticmethod
    def display_image(img, label):
        # BGR -> RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # default：The image is stored using 8-bit indexes into a colormap， for example：a gray image
        qformat = QImage.Format_Indexed8

        if len(img.shape) == 3:  # rows[0], cols[1], channels[2]
            if img.shape[2] == 4:
                # The image is stored using a 32-bit byte-ordered RGBA format (8-8-8-8)
                # A: alpha channel，不透明度参数。如果一个像素的alpha通道数值为0%，那它就是完全透明的
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        # img.shape[1]：图像宽度width，img.shape[0]：图像高度height，img.shape[2]：图像通道数
        # QImage.__init__ (self, bytes data, int width, int height, int bytesPerLine, Format format)
        # 从内存缓冲流获取img数据构造QImage类
        # img.strides[0]：每行的字节数（width*3）,rgb为3，rgba为4
        # strides[0]为最外层(即一个二维数组所占的字节长度)，strides[1]为次外层（即一维数组所占字节长度），strides[2]为最内层（即一个元素所占字节长度）
        # 从里往外看，strides[2]为1个字节长度（uint8），strides[1]为3*1个字节长度（3即rgb 3个通道）
        # strides[0]为width*3个字节长度，width代表一行有几个像素

        out_image = QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat)
        label.setPixmap(QPixmap.fromImage(out_image))
        label.setScaledContents(True)  # 图片自适应大小
