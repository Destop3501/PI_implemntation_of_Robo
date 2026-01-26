import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import math


def clamp(value, min_val, max_val):
    """Clamp value to min/max"""
    return max(min(value, max_val), min_val)


class HandTrackingController(Node):
    """
    Controls robot body, face, arms, and hand sequentially
    based on human hand position and side (left/right)
    """

    def __init__(self):
        super().__init__('hand_tracking_controller')

        # ----- State -----
        self.hand_pose = None      # geometry_msgs/PoseStamped
        self.hand_side = None      # 'left' or 'right'
        self.joint_state = None    # sensor_msgs/JointState

        self.state = "IDLE"        # FSM: IDLE -> BODY_TURN -> FACE_TURN -> ARM_MOVE -> HAND_ROTATE

        # ----- Subscribers -----
        self.create_subscription(PoseStamped, '/hand_pose', self.pose_cb, 10)
        self.create_subscription(String, '/hand_side', self.side_cb, 10)
        self.create_subscription(JointState, '/joint_states', self.joint_cb, 10)

        # ----- Publisher -----
        # Single controller handles all joints from YAML
        self.pub = self.create_publisher(
            JointTrajectory,
            '/body_controller/joint_trajectory',
            10
        )

        # Timer for loop
        self.timer = self.create_timer(0.1, self.control_loop)

        # ----- Targets -----
        self.body_target = None
        self.face_target = None
        self.arm_target = None
        self.hand_target = None

        # Tolerance for checking if joint reached target
        self.tol = 0.05

    # ---------- Callbacks ----------
    def pose_cb(self, msg):
        self.hand_pose = msg

    def side_cb(self, msg):
        if msg.data in ["left", "right"]:
            self.hand_side = msg.data

    def joint_cb(self, msg):
        self.joint_state = msg

    # ---------- Helpers ----------
    def get_joint(self, name):
        if self.joint_state and name in self.joint_state.name:
            idx = self.joint_state.name.index(name)
            return self.joint_state.position[idx]
        return None

    def reached(self, name, target):
        cur = self.get_joint(name)
        return cur is not None and abs(cur - target) < self.tol

    # ---------- Control Loop ----------
    def control_loop(self):
        if not self.hand_pose or not self.hand_side:
            return

        # ----- FSM STATES -----
        if self.state == "IDLE":
            # Compute body target
            self.body_target = clamp((self.hand_pose.pose.position.x - 0.5) * 2.0, -1.5, 1.5)
            self.send_joint("body_joint", self.body_target)
            self.state = "BODY_TURN"
            self.get_logger().info("State: BODY_TURN")

        elif self.state == "BODY_TURN":
            if self.reached("body_joint", self.body_target):
                # Compute face target
                self.face_target = clamp(-(self.hand_pose.pose.position.y - 0.5) * 1.2, -0.8, 0.8)
                self.send_joint("face_joint_x", self.face_target)
                self.state = "FACE_TURN"
                self.get_logger().info("State: FACE_TURN")

        elif self.state == "FACE_TURN":
            if self.reached("face_joint_x", self.face_target):
                self.compute_arm_target()
                self.send_arm()
                self.state = "ARM_MOVE"
                self.get_logger().info("State: ARM_MOVE")

        elif self.state == "ARM_MOVE":
            # Wait until first joint of selected arm reaches target
            arm_joint_name = "left_joint1" if self.hand_side == "left" else "right_joint1"
            if self.reached(arm_joint_name, self.arm_target):
                # Compute hand rotation
                self.compute_hand_target()
                self.send_hand()
                self.state = "HAND_ROTATE"
                self.get_logger().info("State: HAND_ROTATE")

        elif self.state == "HAND_ROTATE":
            # Once hand reached, return to IDLE or keep tracking
            hand_joint_name = "left_joint3" if self.hand_side == "left" else "right_joint3"
            if self.reached(hand_joint_name, self.hand_target):
                self.state = "IDLE"
                self.get_logger().info("State: IDLE - ready for next handshake")

    # ---------- Motion Computation ----------
    def compute_arm_target(self):
        # Arm moves X axis only
        z = self.hand_pose.pose.position.z
        self.arm_target = clamp(0.3 + z * 0.5, 0.2, 0.8)

    def compute_hand_target(self):
        # Hand rotates along X based on depth (z)
        z = self.hand_pose.pose.position.z
        self.hand_target = clamp(-0.2 + z * 0.5, -0.5, 0.5)

    # ---------- Command Senders ----------
    def send_joint(self, joint_name, value):
        traj = JointTrajectory()
        traj.joint_names = [joint_name]
        point = JointTrajectoryPoint()
        point.positions = [value]
        point.time_from_start.sec = 1
        traj.points.append(point)
        self.pub.publish(traj)

    def send_arm(self):
        traj = JointTrajectory()
        point = JointTrajectoryPoint()
        point.time_from_start.sec = 1

        if self.hand_side == "LEFT":
            traj.joint_names = ["left_joint1", "left_joint2", "left_joint3"]
        else:
            traj.joint_names = ["right_joint1", "right_joint2", "right_joint3"]

        point.positions = [self.arm_target] * 3  # X axis only
        traj.points.append(point)
        self.pub.publish(traj)

    def send_hand(self):
        traj = JointTrajectory()
        point = JointTrajectoryPoint()
        point.time_from_start.sec = 1

        if self.hand_side == "LEFT":
            traj.joint_names = ["left_joint3"]  # last joint = hand X rotation
        else:
            traj.joint_names = ["right_joint3"]

        point.positions = [self.hand_target]
        traj.points.append(point)
        self.pub.publish(traj)


def main():
    rclpy.init()
    rclpy.spin(HandTrackingController())
    rclpy.shutdown()


if __name__ == "__main__":
    main()
