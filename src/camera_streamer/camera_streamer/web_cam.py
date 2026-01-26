import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge

class WebcamPublisher(Node):
    def __init__(self):
        super().__init__('webcam_publisher')
        
        # 1. Declare the parameter so it can be set via launch file or CLI
        self.declare_parameter('camera_frame_id', 'camera_link_optical')
        
        # Create a publisher on the 'image_raw' topic
        self.publisher_ = self.create_publisher(Image, 'image_raw', 10)
        
        # Matches your working script settings
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        
        self.bridge = CvBridge()
        # Timer to capture frames at ~20 FPS
        self.timer = self.create_timer(0.05, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            # Convert OpenCV image to ROS 2 Image message
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            
            # 2. Add the Frame ID and Timestamp to the header
            # This makes the data compatible with TF and RViz
            msg.header.frame_id = self.get_parameter('camera_frame_id').get_parameter_value().string_value
            msg.header.stamp = self.get_clock().now().to_msg()
            
            self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = WebcamPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.cap.release()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()