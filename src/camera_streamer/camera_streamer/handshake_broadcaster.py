import rclpy
from rclpy.node import Node
import cv2
import mediapipe as mp
import numpy as np
import math
import sys
from tf2_ros import TransformBroadcaster, Buffer, TransformListener
from geometry_msgs.msg import TransformStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

# Import the new PiCameraWrapper
try:
    from .pi_camera_wrapper import PiCameraWrapper
except ImportError:
    # Fallback for running as a standalone script if needed
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from pi_camera_wrapper import PiCameraWrapper

class HandshakeBroadcaster(Node):
    def __init__(self):
        super().__init__('handshake_broadcaster')
        
        # Initialize Camera with Pi Support
        self.camera = PiCameraWrapper(resolution=(320, 240), framerate=30)
        
        if not self.camera.is_opened():
            self.get_logger().error("Could not open any video device.")
            sys.exit()

        # TF and Joint Publisher
        self.tf_broadcaster = TransformBroadcaster(self)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Publisher for the body controller
        self.joint_pub = self.create_publisher(JointTrajectory, '/body_controller/joint_trajectory', 10)

        # MediaPipe Setup - Optimized for Raspberry Pi 4
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        # model_complexity=0 is faster on RPi4
        self.hands = self.mp_hands.Hands(
            model_complexity=0, 
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        )
        self.pose = self.mp_pose.Pose(
            model_complexity=0, 
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        )
        
        # Gesture Mapping
        self.POSE_MAP = {
            'Left': {'shoulder': self.mp_pose.PoseLandmark.RIGHT_SHOULDER, 'elbow': self.mp_pose.PoseLandmark.RIGHT_ELBOW, 'wrist': self.mp_pose.PoseLandmark.RIGHT_WRIST},
            'Right': {'shoulder': self.mp_pose.PoseLandmark.LEFT_SHOULDER, 'elbow': self.mp_pose.PoseLandmark.LEFT_ELBOW, 'wrist': self.mp_pose.PoseLandmark.LEFT_WRIST}
        }

        # Constants
        self.F_FOCAL = 537
        self.W_WIDTH = 0.06  # FIXED: 6cm (0.06m) average hand width, not 6 meters!
        self.FINGER_JOINTS = [[5, 6, 8], [9, 10, 12], [13, 14, 16], [17, 18, 20]]

        # Frequency synced to ros2_controllers.yaml (20Hz = 0.05s)
        self.timer = self.create_timer(0.05, self.main_loop)

        self.get_logger().info("HandshakeBroadcaster initialized for Raspberry Pi 4.")

    def calculate_angle(self, p1, p2, p3):
        v1, v2 = np.array(p1) - np.array(p2), np.array(p3) - np.array(p2)
        norm = np.linalg.norm(v1) * np.linalg.norm(v2)
        # Avoid division by zero
        if norm < 1e-6:
            return 0.0
        return math.degrees(math.acos(np.clip(np.dot(v1, v2) / norm, -1.0, 1.0)))

    def main_loop(self):
        success, frame = self.camera.read()
        if not success: 
            return

        h, w, _ = frame.shape
        # PiCamera might already be oriented correctly depending on mount
        # We process a flipped version for the user's "mirror" experience if needed
        rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        
        results_hand = self.hands.process(rgb)
        results_pose = self.pose.process(rgb)

        hand_data = []
        if results_hand.multi_hand_landmarks:
            for i in range(len(results_hand.multi_hand_landmarks)):
                img_lms = results_hand.multi_hand_landmarks[i]
                p5 = (img_lms.landmark[5].x * w, img_lms.landmark[5].y * h)
                p17 = (img_lms.landmark[17].x * w, img_lms.landmark[17].y * h)
                dist = math.sqrt((p17[0]-p5[0])**2 + (p17[1]-p5[1])**2)
                # depth_m now based on 0.06m width
                depth_m = (self.W_WIDTH * self.F_FOCAL) / dist if dist != 0 else 999
                
                hand_data.append({
                    'depth': depth_m,
                    'img_lms': img_lms,
                    'world_lms': results_hand.multi_hand_world_landmarks[i],
                    'label': results_hand.multi_handedness[i].classification[0].label
                })

        if hand_data:
            nearest = min(hand_data, key=lambda x: x['depth'])
            
            # 1. Check Hand Gesture
            lm = np.array([[l.x, l.y, l.z] for l in nearest['world_lms'].landmark])
            straight = sum(1 for j in self.FINGER_JOINTS if self.calculate_angle(lm[j[0]], lm[j[1]], lm[j[2]]) > 130.0)
            thumb_ok = self.calculate_angle(lm[0], lm[2], lm[4]) > 140.0
            
            # 2. Check Pose Gesture (Arm Angle)
            is_pose_ok = False
            if results_pose.pose_landmarks:
                p_lms = results_pose.pose_landmarks.landmark
                side = self.POSE_MAP[nearest['label']]
                s, e, wr = p_lms[side['shoulder'].value], p_lms[side['elbow'].value], p_lms[side['wrist'].value]
                
                if s.visibility > 0.6 and e.visibility > 0.6 and wr.visibility > 0.6:
                    arm_angle = self.calculate_angle([s.x, s.y, s.z], [e.x, e.y, e.z], [wr.x, wr.y, wr.z])
                    is_pose_ok = 45 < arm_angle < 135

            if straight >= 3 and thumb_ok and is_pose_ok:
                # depth is already in meters now
                self.broadcast_hand_tf(nearest['img_lms'].landmark[9], nearest['depth'])
                self.control_robot()

        # Display output for VNC viewing
        cv2.imshow("Handshake Broadcaster (Pi)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            pass

    def broadcast_hand_tf(self, center_lm, depth_m):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'body_link' 
        t.child_frame_id = 'user_hand'
        t.transform.translation.x = float(depth_m)
        t.transform.translation.y = float(-(center_lm.x - 0.5) * depth_m)
        t.transform.translation.z = float(-(center_lm.y - 0.5) * depth_m)
        self.tf_broadcaster.sendTransform(t)

    def control_robot(self):
        try:
            # Lookup transform from base to detected hand
            now = rclpy.time.Time()
            trans = self.tf_buffer.lookup_transform('base_link', 'user_hand', now, timeout=rclpy.duration.Duration(seconds=0.1))
            x, y, z = trans.transform.translation.x, trans.transform.translation.y, trans.transform.translation.z
            
            body_z = math.atan2(y, x)
            face_x = -math.atan2(z - 0.5, math.sqrt(x**2 + y**2)) 

            self.publish_joints(np.clip(body_z, -0.85, 0.85), np.clip(face_x, -0.85, 0.85))
        except Exception as e:
            # Silent fail for TF lookup errors to avoid spamming
            pass

    def publish_joints(self, b_z, f_x):
        msg = JointTrajectory()
        msg.joint_names = ['body_joint', 'face_joint_x']
        p = JointTrajectoryPoint()
        p.positions = [float(b_z), float(f_x)]
        # Velocity for smoother tracking at high frequency
        p.time_from_start.nanosec = 10000000 # 10ms for 100Hz sync
        msg.points.append(p)
        self.joint_pub.publish(msg)

def main():
    rclpy.init()
    node = HandshakeBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.camera.release()
        cv2.destroyAllWindows()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
