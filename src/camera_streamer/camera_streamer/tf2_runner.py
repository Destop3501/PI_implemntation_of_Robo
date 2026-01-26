import rclpy
from rclpy.node import Node
import cv2
import numpy as np
from ultralytics import YOLO
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Float32MultiArray

class DepthTFBroadcaster(Node):
    """
    Node that gets wrist coordinates, calculates depth via YOLO, 
    and broadcasts the TF frame.
    """
    def __init__(self):
        super().__init__('depth_tf_broadcaster')
        
        # YOLO Setup
        self.yolo_model = YOLO('yolov8n.pt') 
        self.FOCAL_LENGTH_PX = 537
        
        # TF Broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Subscription to MediaPipe coordinates
        self.subscription = self.create_subscription(
            Float32MultiArray,
            'hand_gesture_data',
            self.gesture_callback,
            10)

        # Camera for YOLO (Shared access usually requires a single capture node, 
        # but for this separation we initialize it here as well)
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2) 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    def get_yolo_depth(self):
        success, frame = self.cap.read()
        if not success: return 1.5 # Fallback depth
        
        results = self.yolo_model(frame, verbose=False, classes=[0]) # Person
        for r in results:
            for box in r.boxes:
                b = box.xyxy[0].cpu().numpy()
                w_px = b[2] - b[0]
                # Est Depth = (Proxied Real Width * Focal) / Pixel Width
                return (0.5 * self.FOCAL_LENGTH_PX) / w_px
        return 1.5

    def gesture_callback(self, msg):
        # msg.data = [wrist_x, wrist_y, is_ready]
        x_norm, y_norm, is_ready = msg.data
        
        if is_ready > 0.5:
            depth_m = self.get_yolo_depth()
            
            t = TransformStamped()
            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = 'camera_link'
            t.child_frame_id = 'handshake_target'
            
            # Convert normalized 2D to 3D Camera Space
            t.transform.translation.x = depth_m
            t.transform.translation.y = -(x_norm - 0.5) * depth_m 
            t.transform.translation.z = -(y_norm - 0.5) * depth_m
            
            t.transform.rotation.w = 1.0
            self.tf_broadcaster.sendTransform(t)
            self.get_logger().info(f"Broadcasting handshake TF at depth: {depth_m:.2f}m")

def main():
    rclpy.init()
    node = DepthTFBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        rclpy.shutdown()

if __name__ == '__main__':
    main()