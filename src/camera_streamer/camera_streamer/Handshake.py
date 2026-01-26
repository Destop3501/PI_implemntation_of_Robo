import cv2
import mediapipe as mp
import numpy as np
from math import degrees, acos
import sys

# --- Gesture Recognition Constants ---
FINGER_JOINTS = [
    [5, 6, 8],    # Index
    [9, 10, 12],   # Middle
    [13, 14, 16],  # Ring
    [17, 18, 20]   # Pinky
]
STRAIGHT_FINGER_THRESHOLD_DEG = 130.0
OPEN_THUMB_THRESHOLD_DEG = 140.0

def calculate_angle(p1, p2, p3):
    """Calculates the 3D angle at p2 given three points."""
    p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
    v1 = p1 - p2
    v2 = p3 - p2
    
    dot_product = np.dot(v1, v2)
    mag1 = np.linalg.norm(v1)
    mag2 = np.linalg.norm(v2)
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
        
    cos_angle = np.clip(dot_product / (mag1 * mag2), -1.0, 1.0)
    return degrees(acos(cos_angle))

def check_pose_handshake_gesture(angle):
    return 45 < angle < 135

def check_hand_handshake_gesture(world_landmarks, handedness):
    lm = np.array([[l.x, l.y, l.z] for l in world_landmarks.landmark])
    
    # Rule 1: Finger Straightness
    straight_fingers = 0
    for joints in FINGER_JOINTS:
        angle = calculate_angle(lm[joints[0]], lm[joints[1]], lm[joints[2]])
        if angle > STRAIGHT_FINGER_THRESHOLD_DEG:
            straight_fingers += 1
    is_fingers_straight = straight_fingers >= 3

    # Rule 2: Thumb Openness
    thumb_angle = calculate_angle(lm[0], lm[2], lm[4])
    is_thumb_open = thumb_angle > OPEN_THUMB_THRESHOLD_DEG

    # Rule 3: Palm Orientation (Wrist vs Middle Knuckle depth)
    depth_diff = lm[0][2] - lm[9][2]
    is_palm_vertical = depth_diff > 0.01 

    is_handshake = is_fingers_straight and is_thumb_open and is_palm_vertical
    return is_handshake, lm[0]

def main():
    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands
    mp_pose = mp.solutions.pose
    
    POSE_MAP = {
        'Left': {
            'shoulder': mp_pose.PoseLandmark.RIGHT_SHOULDER,
            'elbow': mp_pose.PoseLandmark.RIGHT_ELBOW,
            'wrist': mp_pose.PoseLandmark.RIGHT_WRIST
        },
        'Right': {
            'shoulder': mp_pose.PoseLandmark.LEFT_SHOULDER,
            'elbow': mp_pose.PoseLandmark.LEFT_ELBOW,
            'wrist': mp_pose.PoseLandmark.LEFT_WRIST
        }
    }

    # --- FIX: Camera Initialization Logic ---
    print("Searching for available camera...")
    # Try different backends if index 0 fails
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 
    
    if not cap.isOpened():
        print("Warning: Could not open camera with V4L2. Trying default...")
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open any video device. Check if the camera is plugged in or used by another app.")
        sys.exit()

    # Set lower resolution to reduce processing lag if needed
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    print("Camera started successfully. Press ESC to exit.")
    
    with mp_hands.Hands(
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5) as hands, \
         mp_pose.Pose(
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5) as pose:

        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            image = cv2.flip(image, 1)
            h, w, _ = image.shape
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            results_hand = hands.process(image_rgb)
            results_pose = pose.process(image_rgb)
            
            handshake_status = "Waiting..."
            wrist_coords_text = "X, Y, Z: ---"
            display_color = (255, 255, 255)

            if results_hand.multi_hand_world_landmarks and results_hand.multi_handedness:
                for i in range(len(results_hand.multi_hand_world_landmarks)):
                    world_landmarks = results_hand.multi_hand_world_landmarks[i]
                    img_landmarks = results_hand.multi_hand_landmarks[i]
                    handedness = results_hand.multi_handedness[i]
                    hand_label = handedness.classification[0].label

                    is_hand_handshake, wrist_m = check_hand_handshake_gesture(world_landmarks, handedness)
                    
                    is_pose_handshake = False
                    if results_pose.pose_landmarks:
                        p_lms = results_pose.pose_landmarks.landmark
                        side_nodes = POSE_MAP[hand_label]
                        
                        s_lm = p_lms[side_nodes['shoulder'].value]
                        e_lm = p_lms[side_nodes['elbow'].value]
                        wr_lm = p_lms[side_nodes['wrist'].value]

                        if all(l.visibility > 0.5 for l in [s_lm, e_lm, wr_lm]):
                            arm_angle = calculate_angle([s_lm.x, s_lm.y, s_lm.z], 
                                                        [e_lm.x, e_lm.y, e_lm.z], 
                                                        [wr_lm.x, wr_lm.y, wr_lm.z])
                            is_pose_handshake = check_pose_handshake_gesture(arm_angle)

                            # Drawing Skeleton
                            for lm_pts in [(s_lm, e_lm), (e_lm, wr_lm)]:
                                pt1 = (int(lm_pts[0].x * w), int(lm_pts[0].y * h))
                                pt2 = (int(lm_pts[1].x * w), int(lm_pts[1].y * h))
                                cv2.line(image, pt1, pt2, (245, 117, 66), 3)

                    current_color = (0, 165, 255)
                    if is_hand_handshake and is_pose_handshake:
                        current_color = (0, 255, 0)
                        handshake_status = f"HANDSHAKE: {hand_label}"
                        display_color = current_color
                    else:
                        handshake_status = f"Tracking: {hand_label}"

                    wrist_coords_text = f"W: X:{wrist_m[0]:.2f}m, Z:{wrist_m[2]:.2f}m"

                    mp_drawing.draw_landmarks(
                        image, img_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2),
                        mp_drawing.DrawingSpec(color=current_color, thickness=2)
                    )

            cv2.putText(image, handshake_status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, display_color, 2)
            cv2.putText(image, wrist_coords_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow('Handshake Detector', image)
            if cv2.waitKey(5) & 0xFF == 27: 
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()