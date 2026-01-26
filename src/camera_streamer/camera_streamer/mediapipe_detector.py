import cv2
import mediapipe as mp
import numpy as np
from math import degrees, acos
import socket
import json
import time

# Import the new PiCameraWrapper
try:
    from .pi_camera_wrapper import PiCameraWrapper
except ImportError:
    # Fallback for running as a standalone script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from pi_camera_wrapper import PiCameraWrapper

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ADDR = ("127.0.0.1", 5005)

# Initialize Camera with Pi Support
camera = PiCameraWrapper(resolution=(352, 288), framerate=30)

mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

FINGER_JOINTS = [
    [5, 6, 8],    # Index
    [9, 10, 12],   # Middle
    [13, 14, 16],  # Ring
    [17, 18, 20]   # Pinky
]
STRAIGHT_FINGER_THRESHOLD_DEG = 130.0
OPEN_THUMB_THRESHOLD_DEG = 140.0
DETECTION_FRAME_THRESHOLD = 10
handshake_counter = 0

FOCAL_PX = 537 
HAND_WIDTH_METERS = 0.06  # FIXED: 6cm (0.06m), not 6 meters!

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

def calculate_depth(p5, p17):
    w_pixel = ((p17[0]-p5[0])**2 + (p17[1]-p5[1])**2)**0.5
    if w_pixel == 0: return 999
    # Now returns meters correctly
    return (HAND_WIDTH_METERS * FOCAL_PX) / w_pixel

def calculate_angle(p1, p2, p3):
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
    hand_type = handedness.classification[0].label

    # Rule 1: Finger Straightness
    straight_fingers = 0
    for joints in FINGER_JOINTS:
        angle = calculate_angle(lm[joints[0]], lm[joints[1]], lm[joints[2]])
        if angle > STRAIGHT_FINGER_THRESHOLD_DEG:
            straight_fingers += 1
    is_fingers_straight = straight_fingers >= 3

    thumb_angle = calculate_angle(lm[0], lm[2], lm[4])
    is_thumb_open = thumb_angle > OPEN_THUMB_THRESHOLD_DEG

    depth_diff = lm[0][2] - lm[9][2]
    is_palm_vertical = depth_diff > 0.01 

    is_handshake = is_fingers_straight and is_thumb_open and is_palm_vertical
    return is_handshake, lm[9], hand_type

# Optimized for Raspberry Pi 4
with mp_hands.Hands(
    max_num_hands=2, # Reduced for performance
    model_complexity=0, # FIXED for RPi4 performance
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5) as hands, \
    mp_pose.Pose(
    model_complexity=0, # FIXED for RPi4 performance
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5) as pose:

    prev_time = time.time()
    while camera.is_opened():
        success, image = camera.read()
        if not success: continue

        # Performance monitoring
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time

        # User mentioned viewing via VNC, so we keep the preview window
        image = cv2.flip(image, 1) # User mirror display logic
        h, w, _ = image.shape
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        results_hand = hands.process(image_rgb)
        results_pose = pose.process(image_rgb)

        status_text = f"FPS: {fps:.1f} | Waiting..."
        wrist_coords_text = "X, Y, Z: ---"
        display_color = (255, 255, 255)

        if results_hand.multi_hand_world_landmarks and results_hand.multi_handedness:
            # We track the nearest hand
            nearest_idx = 0
            min_z = float('inf')

            for i, hand_lms in enumerate(results_hand.multi_hand_landmarks):
                if hand_lms.landmark[0].z < min_z:
                    min_z = hand_lms.landmark[0].z
                    nearest_idx = i

            world_landmarks = results_hand.multi_hand_world_landmarks[nearest_idx]
            img_landmarks = results_hand.multi_hand_landmarks[nearest_idx]
            handedness = results_hand.multi_handedness[nearest_idx]

            p5 = (img_landmarks.landmark[5].x * w, img_landmarks.landmark[5].y * h)
            p17 = (img_landmarks.landmark[17].x * w, img_landmarks.landmark[17].y * h)

            dx = (p5[0]+(p5[0]-p17[0])/2)-w/2
            dy = (p5[1]+(p5[1]-p17[1])/2)-h/2

            # Now in meters correctly
            depth_m = calculate_depth(p5, p17)

            is_hand_handshake, middle_m, hand_label = check_hand_handshake_gesture(world_landmarks, handedness)
            is_pose_handshake = False
            
            if results_pose.pose_landmarks:
                p_lms = results_pose.pose_landmarks.landmark
                side_nodes = POSE_MAP[hand_label]
                
                s_idx = side_nodes['shoulder'].value
                e_idx = side_nodes['elbow'].value
                w_idx = side_nodes['wrist'].value
                
                s_lm = p_lms[s_idx]
                e_lm = p_lms[e_idx]
                wr_lm = p_lms[w_idx]

                if all(l.visibility > 0.5 for l in [s_lm, e_lm, wr_lm]):
                    shoulder = [s_lm.x, s_lm.y, s_lm.z]
                    elbow = [e_lm.x, e_lm.y, e_lm.z]
                    wrist = [wr_lm.x, wr_lm.y, wr_lm.z]
                    
                    arm_angle = calculate_angle(shoulder, elbow, wrist)
                    is_pose_handshake = check_pose_handshake_gesture(arm_angle)

                    # Drawing logic
                    ps = (int(s_lm.x * w), int(s_lm.y * h))
                    pe = (int(e_lm.x * w), int(e_lm.y * h))
                    pwr = (int(wr_lm.x * w), int(wr_lm.y * h))
                    
                    cv2.line(image, ps, pe, (245, 117, 66), 3)
                    cv2.line(image, pe, pwr, (245, 117, 66), 3)
                    cv2.circle(image, ps, 6, (245, 66, 230), -1)
                    cv2.circle(image, pe, 6, (245, 66, 230), -1)
                    cv2.circle(image, pwr, 6, (245, 66, 230), -1)
                        
                current_color = (0, 165, 255)
                if is_hand_handshake and is_pose_handshake:
                    current_color = (0, 255, 0)
                    handshake_counter += 1
                    status_text = f"FPS: {fps:.1f} | CONFIRMING: {handshake_counter}/{DETECTION_FRAME_THRESHOLD}"
                    display_color = current_color
                    if handshake_counter >= DETECTION_FRAME_THRESHOLD:
                        depth_cm = depth_m * 100.0
                        data = {"x": round(float(dx), 2), "y": round(float(dy), 2), "detected": True, 'depth': round(float(depth_cm), 2)}
                        sock.sendto(json.dumps(data).encode(), ADDR)
                        print("SENT:", data)
                        handshake_counter = 0
                else:
                    status_text = f"FPS: {fps:.1f} | Hand: {hand_label}"
                    handshake_counter = 0

                wrist_coords_text = f"depth:{depth_m:.2f}m, X:{dx:.2f}, Y:{dy:.2f}"

                mp_drawing.draw_landmarks(
                    image, img_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2),
                    mp_drawing.DrawingSpec(color=current_color, thickness=2)
                )
        
        cv2.putText(image, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, display_color, 2)
        cv2.putText(image, wrist_coords_text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        cv2.imshow('Pi Handshake Detector', image)
        if cv2.waitKey(1) & 0xFF == 27: break

camera.release()
cv2.destroyAllWindows()
