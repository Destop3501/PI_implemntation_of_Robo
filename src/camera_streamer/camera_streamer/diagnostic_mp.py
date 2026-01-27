import mediapipe as mp
import cv2
import numpy as np

def test_hands():
    print("\n--- Testing MediaPipe Hands ---")
    try:
        hands = mp.solutions.hands.Hands(model_complexity=0)
        print("SUCCESS: Hands model initialized.")
        return True
    except Exception as e:
        print(f"FAILED: Hands model failed to initialize: {e}")
        return False

def test_pose():
    print("\n--- Testing MediaPipe Pose ---")
    try:
        pose = mp.solutions.pose.Pose(model_complexity=0)
        print("SUCCESS: Pose model initialized.")
        return True
    except Exception as e:
        print(f"FAILED: Pose model failed to initialize: {e}")
        return False

if __name__ == "__main__":
    print(f"MediaPipe Version: {mp.__version__}")
    h_ok = test_hands()
    p_ok = test_pose()
    
    if h_ok and p_ok:
        print("\nBoth models initialized successfully! The error might be occurring during the processing of a frame.")
    else:
        print("\nDiagnostic complete. One or more models failed to initialize.")
