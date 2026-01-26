import rclpy
from rclpy.node import Node
import cv2
import mediapipe as mp
import numpy as np
import math
import sys
from std_msgs.msg import String, Float32MultiArray

class HandshakeGestureNode(Node):
    """
    Node for identifying hand gestures and arm extension using MediaPipe.
    Automatically exits after 30 seconds or upon successful identification.
    """
    def __init__(self):
        super().__init__('handshake_gesture_node')
        
        # Camera Setup
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        # MediaPipe Setup
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        self.hands = self.mp_hands.Hands(model_complexity=0, min_detection_confidence=0.7)
        self.pose = self.mp_pose.Pose(model_complexity=0, min_detection_confidence=0.7)
        
        # Publishers
        self.hand_data_pub = self.create_publisher(Float32MultiArray, 'hand_gesture_data', 10)
        self.status_pub = self.create_publisher(String, 'handshake_status', 10)

        self.POSE_MAP = {
            'Left': {'shoulder': self.mp_pose.PoseLandmark.RIGHT_SHOULDER, 
                     'elbow': self.mp_pose.PoseLandmark.RIGHT_ELBOW, 
                     'wrist': self.mp_pose.PoseLandmark.RIGHT_WRIST},
            'Right': {'shoulder': self.mp_pose.PoseLandmark.LEFT_SHOULDER, 
                      'elbow': self.mp_pose.PoseLandmark.LEFT_ELBOW, 
                      'wrist': self.mp_pose.PoseLandmark.LEFT_WRIST}
        }

        # Timer for processing frames
        self.timer = self.create_timer(0.05, self.process_frame)
        
        # Shutdown Timer: Exit the node after 30 seconds
        self.get_logger().info("Hand Detector started. Timeout set for 30 seconds.")
        self.shutdown_timer = self.create_timer(30.0, self.auto_exit)

    def auto_exit(self):
        """Callback to shut down the node after the 30s timeout."""
        self.get_logger().info("30-second timeout reached. Exiting Hand Detector.")
        self.cleanup_and_exit()

    def cleanup_and_exit(self):
        """Graceful shutdown logic."""
        self.cap.release()
        cv2.destroyAllWindows()
        # Raising SystemExit triggers the launch file's OnProcessExit handler
        sys.exit(0)

    def calculate_angle(self, p1, p2, p3):
        v1, v2 = np.array(p1) - np.array(p2), np.array(p3) - np.array(p2)
        norm = np.linalg.norm(v1) * np.linalg.norm(v2)
        return math.degrees(math.acos(np.clip(np.dot(v1, v2) / norm, -1.0, 1.0))) if norm != 0 else 0.0

    def process_frame(self):
        success, frame = self.cap.read()
        if not success: return

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res_hand = self.hands.process(rgb)
        res_pose = self.pose.process(rgb)

        if res_hand.multi_hand_landmarks:
            for i, hand_lms in enumerate(res_hand.multi_hand_landmarks):
                label = res_hand.multi_handedness[i].classification[0].label
                
                # World landmarks for geometry checks
                world_lms = res_hand.multi_hand_world_landmarks[i]
                lm_arr = np.array([[l.x, l.y, l.z] for l in world_lms.landmark])
                
                # Gesture Detection
                straight = 0
                for j in [[5,6,8], [9,10,12], [13,14,16], [17,18,20]]:
                    if self.calculate_angle(lm_arr[j[0]], lm_arr[j[1]], lm_arr[j[2]]) > 130:
                        straight += 1
                thumb_up = self.calculate_angle(lm_arr[0], lm_arr[2], lm_arr[4]) > 140

                # Arm Extension Check
                handshake_ready = False
                if res_pose.pose_landmarks:
                    p = res_pose.pose_landmarks.landmark
                    side = self.POSE_MAP.get(label)
                    if side:
                        s, e, wr = p[side['shoulder'].value], p[side['elbow'].value], p[side['wrist'].value]
                        if all(pt.visibility > 0.5 for pt in [s, e, wr]):
                            arm_ang = self.calculate_angle([s.x, s.y, s.z], [e.x, e.y, e.z], [wr.x, wr.y, wr.z])
                            handshake_ready = 60 < arm_ang < 130

                # If identified, publish and exit immediately to trigger next node
                if straight >= 3 and thumb_up and handshake_ready:
                    wrist = hand_lms.landmark[0]
                    msg = Float32MultiArray()
                    msg.data = [float(wrist.x), float(wrist.y), 1.0]
                    self.hand_data_pub.publish(msg)
                    
                    status = String()
                    status.data = f"Handshake Identified: {label}"
                    self.status_pub.publish(status)
                    self.get_logger().info("Handshake identified! Handing over to YOLO Depth.")
                    
                    # Exit immediately upon successful detection
                    self.cleanup_and_exit()

        cv2.imshow("Hand Identification (Python 3.9)", frame)
        cv2.waitKey(1)

def main():
    rclpy.init()
    node = HandshakeGestureNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()