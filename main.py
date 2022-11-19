
from time import sleep
from datetime import datetime
import os
import cv2
import face_recognition
from zk import ZK
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
door_opened_at=datetime.now()


def Door():
    global door_opened_at
    conn = None
    zk = ZK(f'{os.getenv("ZK_IP")}', port=4370, timeout=5, password=f'{os.getenv("ZK_PASSWORD")}', force_udp=False,
            ommit_ping=False)
    if (datetime.now()-door_opened_at).seconds>10:
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
                door_opened_at=datetime.now()

video_capture = cv2.VideoCapture(os.getenv("ML_CAM_IP"))
print(f'Using Camera: {os.getenv("ML_CAM_IP")}')

known_face_encodings = []
img = os.listdir(BASE_DIR.joinpath("images"))
print(f'Total image loaded: {len(img)}')

for i in img:
    image = face_recognition.load_image_file(f'{BASE_DIR.joinpath("images")}/{i}')
    face_encoding = face_recognition.face_encodings(image)[0]
    known_face_encodings.append(face_encoding)

print('Starting Video Capture!')
while True:
    # Grab a single frame of video
    ret, frame = video_capture.read()
    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_frame = frame[:, :, ::-1]

    # Find all the faces and face enqcodings in the frame of video
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    each_frame = zip(face_locations,face_encodings)

    # Loop through each face in this frame of video
    for (top, right, bottom, left), face_encoding in each_frame:
        if matches := face_recognition.compare_faces(known_face_encodings, face_encoding):
            Door()
            break
        
