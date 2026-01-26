import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
import socket
import json

class MediaPipeBridge(Node):
    def __init__(self):
        super().__init__('mediapipe_bridge')

        self.publisher = self.create_publisher(
            Float32MultiArray,
            'hand_gesture_data',
            10
        )

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 5005))
        self.sock.setblocking(False)

        self.create_timer(0.01, self.read_socket)

    def read_socket(self):
        try:
            data, _ = self.sock.recvfrom(1024)
            d = json.loads(data)

            msg = Float32MultiArray()
            msg.data = [d["x"], d["y"], d["ready"]]
            self.publisher.publish(msg)
        except BlockingIOError:
            pass

def main():
    rclpy.init()
    rclpy.spin(MediaPipeBridge())
    rclpy.shutdown()

if __name__ == '__main__':
    main()
