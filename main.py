from datetime import datetime
import os
import cv2
import face_recognition
from zk import ZK
from pathlib import Path
from multiprocessing import Process, Manager, cpu_count, set_start_method
import threading
import platform
import time
import numpy
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


# Get next worker's id
def next_id(current_id, worker_num):
    return 1 if current_id == worker_num else current_id + 1


# Get previous worker's id
def prev_id(current_id, worker_num):
    return worker_num if current_id == 1 else current_id - 1


# A subprocess use to capture frames.
def capture(read_frame_list, Global, worker_num):

    video_capture = cv2.VideoCapture(os.getenv("ML_CAM_IP"))
   

    while not Global.is_exit:
        # If it's time to read a frame
        if Global.buff_num != next_id(Global.read_num, worker_num):
            # Grab a single frame of video
            ret, frame = video_capture.read()
            read_frame_list[Global.buff_num] = frame
            Global.buff_num = next_id(Global.buff_num, worker_num)
        else:
            time.sleep(0.01)

    # Release webcam
    video_capture.release()

def Door():
    conn = None
    zk = ZK(f'{os.getenv("ZK_IP")}', port=4370, timeout=5, password=f'{os.getenv("ZK_PASSWORD")}', force_udp=False,
            ommit_ping=False)
    if (datetime.now()-Global.door_opened_at).seconds>10:
        try:
            conn = zk.connect()
            conn.disable_device()
            conn.test_voice()
            conn.unlock(time=1)
            print(f"The door has been opened at {datetime.now().replace(microsecond=0)}")
            conn.enable_device()
        except Exception as e:
            print(e)
        finally:
            if conn:
                conn.disconnect()
                Global.door_opened_at=datetime.now()



# Many subprocess use to process frames.
def process(worker_id, read_frame_list, write_frame_list, Global, worker_num):
    known_face_encodings = Global.known_face_encodings
    while not Global.is_exit:

        # Wait to read
        while (Global.read_num != worker_id or Global.read_num != prev_id(Global.buff_num, worker_num)) and not Global.is_exit:
            time.sleep(0.01)

        # Delay to make the video look smoother
        time.sleep(Global.frame_delay)

        # Read a single frame from frame list
        frame_process = read_frame_list[worker_id]

        # Expect next worker to read frame
        Global.read_num = next_id(Global.read_num, worker_num)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_frame = frame_process[:, :, ::-1]

        # Find all the faces and face encodings in the frame of video, cost most time
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        each_frame = zip(face_locations,face_encodings)

        # Loop through each face in this frame of video
        for (top, right, bottom, left), face_encoding in each_frame:
            if matches := face_recognition.compare_faces(known_face_encodings, face_encoding):
                Door()
                break
        # Wait to write
        while Global.write_num != worker_id:
            time.sleep(0.01)

        # Send frame to global
        write_frame_list[worker_id] = frame_process

        # Expect next worker to write frame
        Global.write_num = next_id(Global.write_num, worker_num)
        
if __name__ == '__main__':


    if platform.system() == 'Darwin':
        set_start_method('forkserver')

    # Global variables
    Global = Manager().Namespace()
    Global.buff_num = 1
    Global.read_num = 1
    Global.write_num = 1
    Global.frame_delay = 0
    Global.is_exit = False
    read_frame_list = Manager().dict()
    write_frame_list = Manager().dict()
    Global.door_opened_at=datetime.now()

    # Number of workers (subprocess use to process frames)
    worker_num = cpu_count() - 1 if cpu_count() > 2 else 2
    # Subprocess list
    print(f'Using Camera: {os.getenv("ML_CAM_IP")}')
    p = [threading.Thread(target=capture, args=(read_frame_list, Global, worker_num,))]
    print('Starting Video Capture!')
    p[0].start()

    our_face_encodings = []
    img = os.listdir(BASE_DIR.joinpath("images"))
    print(f'Total image loaded: {len(img)}')

    for i in img:
        image = face_recognition.load_image_file(f'{BASE_DIR.joinpath("images")}/{i}')
        face_encoding = face_recognition.face_encodings(image)[0]
        our_face_encodings.append(face_encoding)

    Global.known_face_encodings=our_face_encodings.copy()


    # Create workers
    for worker_id in range(1, worker_num + 1):
        p.append(Process(target=process, args=(worker_id, read_frame_list, write_frame_list, Global, worker_num,)))
        p[worker_id].start()

    # Start to show video
    last_num = 1
    fps_list = []
    tmp_time = time.time()
    while not Global.is_exit:
        while Global.write_num != last_num:
            last_num = Global.write_num

            # Calculate fps
            delay = time.time() - tmp_time
            tmp_time = time.time()
            fps_list.append(delay)
            if len(fps_list) > 5 * worker_num:
                fps_list.pop(0)
            fps = len(fps_list) / numpy.sum(fps_list)
            if fps < 6:
                Global.frame_delay = (1 / fps) * 0.75
            elif fps < 20:
                Global.frame_delay = (1 / fps) * 0.5
            elif fps < 30:
                Global.frame_delay = (1 / fps) * 0.25
            else:
                Global.frame_delay = 0
