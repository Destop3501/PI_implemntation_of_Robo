import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
import socket
import json

class HandSocketReceiver(Node):
    def __init__(self):
        super().__init__('hand_socket_receiver')

        self.pose_pub = self.create_publisher(PoseStamped, '/hand_pose', 10)
        # self.side_sub = self.create_publisher(String, '/hand_side', 10)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 5005))
        self.sock.setblocking(False)

        self.timer = self.create_timer(0.02, self.receive_data)
        self.get_logger().info("Listening for MediaPipe handshake data...")

    def receive_data(self):
        try:
            data, _ = self.sock.recvfrom(1024)
            msg = json.loads(data.decode())

            if not msg["detected"]:
                return

            pose = PoseStamped()
            pose.header.frame_id = "camera_link"
            pose.header.stamp = self.get_clock().now().to_msg()

            pose.pose.position.x = (msg["x"])
            pose.pose.position.y = (msg["y"])
            pose.pose.position.z = -(msg['depth'])

            pose.pose.orientation.w = 1.0
            self.pose_pub.publish(pose)

            # side = String()
            # side.data = msg["hand"]
            # self.side_pub.publish(side)

        except BlockingIOError:
            pass

def main():
    rclpy.init()
    node = HandSocketReceiver()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
