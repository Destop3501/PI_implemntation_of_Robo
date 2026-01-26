import rclpy
from rclpy.node import Node
import cv2
from ultralytics import YOLO
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Float32MultiArray

class DepthTFBroadcaster(Node):
    def __init__(self):
        super().__init__('depth_tf_broadcaster')

        self.model = YOLO('yolov8n.pt')
        self.focal_px = 537

        self.tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(
            Float32MultiArray,
            'hand_gesture_data',
            self.callback,
            10
        )

        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

    def get_depth(self):
        ok, frame = self.cap.read()
        if not ok:
            return 1.5

        results = self.model(frame, classes=[0], verbose=False)
        for r in results:
            for box in r.boxes:
                w_px = (box.xyxy[0][2] - box.xyxy[0][0]).item()
                return (0.5 * self.focal_px) / w_px
        return 1.5

    def callback(self, msg):
        x, y, ready = msg.data
        if ready < 0.5:
            return

        depth = self.get_depth()

        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "camera_link"
        t.child_frame_id = "handshake_target"

        t.transform.translation.x = depth
        t.transform.translation.y = -(x - 0.5) * depth
        t.transform.translation.z = -(y - 0.5) * depth
        t.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(t)

def main():
    rclpy.init()
    rclpy.spin(DepthTFBroadcaster())
    rclpy.shutdown()

if __name__ == '__main__':
    main()
