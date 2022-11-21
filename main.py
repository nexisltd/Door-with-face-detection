import os
import random
import threading
import time
from datetime import datetime
from multiprocessing import Manager, Process, cpu_count, set_start_method
from pathlib import Path

import cv2
import face_recognition
import numpy
from dotenv import load_dotenv
from zk import ZK

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def capture(read_frame_list, Global, worker_num):
    """
    It captures frames from a camera and initially tries to detect faces, if it finds faces it passes the frames to process function.

    :param read_frame_list: a list of frames that are read from the camera
    :param Global: a class that contains the variables that are shared between the processes
    :param worker_num: the number of workers
    """
    video_capture = cv2.VideoCapture(os.getenv("ML_CAM_IP"))
    haar_cascade = cv2.CascadeClassifier("Haarcascade_frontalface_default.xml")
    while not Global.is_exit:
        if Global.buff_num != next_id(Global.read_num, worker_num):
            ret, frame = video_capture.read()
            gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces_rect = haar_cascade.detectMultiScale(gray_img, 1.1, 9)
            if numpy.asarray(faces_rect).any():
                read_frame_list[Global.buff_num] = frame
                Global.buff_num = next_id(Global.buff_num, worker_num)
        else:
            time.sleep(0.01)
    video_capture.release()


def process(worker_id, read_frame_list, write_frame_list, Global, worker_num):
    """
    It takes a frame, finds faces in it, and if it finds a face that matches one of the known faces, it
    opens the door

    :param worker_id: The ID of the worker
    :param read_frame_list: a list of frames that are read by the worker
    :param write_frame_list: a list of frames that have been processed by the worker
    :param Global: a class that contains the known_face_encodings and is_exit
    :param worker_num: the number of workers
    """
    known_face_encodings = Global.known_face_encodings
    while not Global.is_exit:
        while (
            Global.read_num != worker_id
            or Global.read_num != prev_id(Global.buff_num, worker_num)
        ) and not Global.is_exit:
            time.sleep(0.01)
        frame_process = read_frame_list[worker_id]
        Global.read_num = next_id(Global.read_num, worker_num)
        rgb_frame = frame_process[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        each_frame = zip(face_locations, face_encodings)
        for (top, right, bottom, left), face_encoding in each_frame:
            if matches := face_recognition.compare_faces(
                known_face_encodings, face_encoding
            ):
                Door()
                break
        while Global.write_num != worker_id:
            time.sleep(0.01)
        write_frame_list[worker_id] = frame_process
        Global.write_num = next_id(Global.write_num, worker_num)


def Door():
    """
    It opens the door
    """
    time.sleep(random.uniform(0.1, 0.5))
    conn = None
    zk = ZK(
        f'{os.getenv("ZK_IP")}',
        port=4370,
        timeout=5,
        password=f'{os.getenv("ZK_PASSWORD")}',
        force_udp=False,
        ommit_ping=False,
    )
    if (datetime.now() - Global.door_opened_at).seconds > 11:
        Global.door_opened_at = datetime.now()
        try:
            conn = zk.connect()
            conn.disable_device()
            conn.test_voice()
            conn.unlock(time=1)
            print(f"The door has been opened at {datetime.now()}")
            conn.enable_device()
        except Exception as e:
            print(e)
        finally:
            if conn:
                conn.disconnect()


def next_id(current_id, worker_num):
    """
    If the current id is equal to the worker number, return 1, otherwise return the current id plus 1

    :param current_id: the id of the current worker
    :param worker_num: the number of workers
    :return: The next id in the sequence.
    """
    return 1 if current_id == worker_num else current_id + 1


def prev_id(current_id, worker_num):
    """
    > If the current id is 1, return the worker number, otherwise return the current id minus 1

    :param current_id: the id of the current worker
    :param worker_num: The number of workers in the system
    :return: The worker number if the current id is 1, otherwise the current id minus 1.
    """
    return worker_num if current_id == 1 else current_id - 1


# A way to make sure that the code in the if statement only runs when the script is executed directly.
if __name__ == "__main__":
    Global = Manager().Namespace()
    Global.buff_num = 1
    Global.read_num = 1
    Global.write_num = 1
    Global.frame_delay = 0
    Global.is_exit = False
    read_frame_list = Manager().dict()
    write_frame_list = Manager().dict()
    Global.door_opened_at = datetime.now()

    worker_num = cpu_count() - 1 if cpu_count() > 2 else 2
    print(f'Using Camera: {os.getenv("ML_CAM_IP")}')
    p = [
        threading.Thread(
            target=capture,
            args=(
                read_frame_list,
                Global,
                worker_num,
            ),
        )
    ]
    print("Starting Video Capture!")
    p[0].start()
    img = os.listdir(BASE_DIR.joinpath("images"))
    print(f"Total image loaded: {len(img)}")
    Global.known_face_encodings = []
    for i in img:
        image = face_recognition.load_image_file(f'{BASE_DIR.joinpath("images")}/{i}')
        face_encoding = face_recognition.face_encodings(image)[0]
        Global.known_face_encodings.append(face_encoding)

    for worker_id in range(1, worker_num + 1):
        p.append(
            Process(
                target=process,
                args=(
                    worker_id,
                    read_frame_list,
                    write_frame_list,
                    Global,
                    worker_num,
                ),
            )
        )
        p[worker_id].start()
    last_num = 1
    tmp_time = time.time()
    while not Global.is_exit:
        while Global.write_num != last_num:
            last_num = Global.write_num
