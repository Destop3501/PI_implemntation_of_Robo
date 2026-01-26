import cv2
import mediapipe as mp
import numpy as np
import math
import socket
import json

# ---------------- Socket Setup ----------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ADDR = ("127.0.0.1", 5005)

# ---------------- Camera ----------------
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# ---------------- MediaPipe ----------------
mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose

hands = mp_hands.Hands(
    model_complexity=0,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

pose = mp_pose.Pose(
    model_complexity=0,
    min_detection_confidence=0.7
)

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

def calculate_angle(p1, p2, p3):
    v1, v2 = np.array(p1) - np.array(p2), np.array(p3) - np.array(p2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norm == 0:
        return 0.0
    return math.degrees(math.acos(np.clip(np.dot(v1, v2) / norm, -1.0, 1.0)))

# ---------------- Main Loop ----------------
while True:
    success, frame = cap.read()
    if not success:
        continue

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    res_hand = hands.process(rgb)
    res_pose = pose.process(rgb)

    if res_hand.multi_hand_landmarks and res_pose.pose_landmarks:
        for i, hand_lms in enumerate(res_hand.multi_hand_landmarks):
            label = res_hand.multi_handedness[i].classification[0].label
            world = res_hand.multi_hand_world_landmarks[i]
            lm = np.array([[l.x, l.y, l.z] for l in world.landmark])

            # Finger check
            straight = 0
            for j in [[5,6,8], [9,10,12], [13,14,16], [17,18,20]]:
                if calculate_angle(lm[j[0]], lm[j[1]], lm[j[2]]) > 130:
                    straight += 1

            thumb_up = calculate_angle(lm[0], lm[2], lm[4]) > 140

            # Arm extension
            side = POSE_MAP.get(label)
            if not side:
                continue

            p = res_pose.pose_landmarks.landmark
            s, e, w = p[side['shoulder'].value], p[side['elbow'].value], p[side['wrist'].value]

            if min(s.visibility, e.visibility, w.visibility) < 0.5:
                continue

            arm_angle = calculate_angle(
                [s.x, s.y, s.z],
                [e.x, e.y, e.z],
                [w.x, w.y, w.z]
            )

            ready = straight >= 3 and thumb_up and (60 < arm_angle < 130)

            if ready:
                wrist = hand_lms.landmark[0]
                payload = {
                    "x": float(wrist.x),
                    "y": float(wrist.y),
                    "ready": 1.0
                }
                sock.sendto(json.dumps(payload).encode(), ADDR)

    cv2.imshow("MediaPipe Handshake Detection", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
