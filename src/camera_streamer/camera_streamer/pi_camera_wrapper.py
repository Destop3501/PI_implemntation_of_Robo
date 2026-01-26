import cv2
import numpy as np
import time

class PiCameraWrapper:
    def __init__(self, resolution=(320, 240), framerate=30):
        self.resolution = resolution
        self.framerate = framerate
        self.cap = None
        self.picam2 = None
        self.use_picamera = False

        # Attempt to initialize picamera2 (Modern Pi stack)
        try:
            from picamera2 import Picamera2
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(main={"size": resolution})
            self.picam2.configure(config)
            self.picam2.start()
            self.use_picamera = True
            print("PiCameraWrapper: Using picamera2 (PiCamera v2 detected)")
        except (ImportError, Exception) as e:
            print(f"PiCameraWrapper: picamera2 not available or failed: {e}. Falling back to OpenCV V4L2.")
            self._init_v4l2()

    def _init_v4l2(self):
        # Fallback to standard OpenCV capture
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            print("PiCameraWrapper: Could not open camera with V4L2. Trying default capture.")
            self.cap = cv2.VideoCapture(0)
        
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.framerate)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            print("PiCameraWrapper: Using OpenCV V4L2")
        else:
            print("PiCameraWrapper: ERROR - No camera detected")

    def read(self):
        if self.use_picamera:
            try:
                # Capture a frame as a numpy array
                frame = self.picam2.capture_array()
                return True, frame
            except Exception as e:
                print(f"PiCameraWrapper: PiCamera capture error: {e}")
                return False, None
        else:
            if self.cap and self.cap.isOpened():
                return self.cap.read()
        return False, None

    def release(self):
        if self.use_picamera and self.picam2:
            self.picam2.stop()
            self.picam2.close()
        if self.cap:
            self.cap.release()

    def is_opened(self):
        if self.use_picamera:
            return self.picam2 is not None
        return self.cap is not None and self.cap.isOpened()
