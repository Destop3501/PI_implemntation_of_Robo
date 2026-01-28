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

def test_opencv():
    print("\n--- Testing OpenCV ---")
    try:
        import cv2
        print(f"OpenCV Version: {cv2.__version__}")
        # Test a simple operation
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.putText(img, "Test", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        print("SUCCESS: OpenCV basic operations work.")
        return True
    except Exception as e:
        print(f"FAILED: OpenCV test failed: {e}")
        return False

def test_camera():
    print("\n--- Testing Camera Access ---")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("SUCCESS: Camera /dev/video0 opened via V4L2.")
            cap.release()
            return True
        else:
            print("FAILED: Camera /dev/video0 could not be opened.")
            return False
    except Exception as e:
        print(f"FAILED: Camera test error: {e}")
        return False

if __name__ == "__main__":
    import mediapipe as mp
    print(f"MediaPipe Version: {mp.__version__}")
    
    cv_ok = test_opencv()
    cam_ok = test_camera()
    h_ok = test_hands()
    p_ok = test_pose()
    
    print("\n--- Diagnostic Summary ---")
    print(f"OpenCV: {'OK' if cv_ok else 'FAIL'}")
    print(f"Camera: {'OK' if cam_ok else 'FAIL'}")
    print(f"Hands:  {'OK' if h_ok else 'FAIL'}")
    print(f"Pose:   {'OK' if p_ok else 'FAIL'}")
