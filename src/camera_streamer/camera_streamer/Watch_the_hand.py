import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import math
import time

class PID:
    def __init__(self, kp, ki, kd, limit):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.limit = limit

        self.prev_error = 0
        self.interganal = 0
        self.prev_time = time.time()

    def update(self, target, current):
        now = time.time()
        dt = max(now - self.prev_time, 1e-3)

        error = target - current
        self.interganal = error * dt
        derative = (error -self.prev_error)/dt

        output=(
            self.kp * error +
            self.ki * self.interganal +
            self.kd * derative
        )
        
        output = max(min(output, self.limit), -self.limit)

        self.prev_error = error
        self.prev_time = now
        return current + output

class HandTracker(Node):
    def __init__(self):
        super().__init__('hand_tracker')

        self.sub = self.create_subscription(
            PoseStamped,
            '/hand_pose',
            self.hand_cb,
            10
        )

        self.pub = self.create_publisher(
            JointTrajectory,
            '/body_controller/joint_trajectory',
            10
        )

        self.body_yaw =0.0
        self.face_pitch = 0.0 

        self.body_pid = PID(kp=1.2 , ki=0.0, kd=0.15, limit=0.02)
        self.face_pid = PID(kp=1.0 , ki=0.0, kd=0.12, limit=0.015)

        self.get_logger().info("Hand tracking controller started")

    def hand_cb(self, msg: PoseStamped):
        # Hand position in robot base frame
        x = msg.pose.position.x
        z = msg.pose.position.y
        y = msg.pose.position.z

        # ---------------- BODY YAW (Z axis) ----------------
        body_yaw_target = math.atan2(x, y)

        # ---------------- FACE PITCH (X axis) ----------------
        distance_xy = math.sqrt(x*x + y*y)
        face_pitch_target = math.atan2(z - 0.150, distance_xy)  # 0.150 = face height

        # Safety clamp
        body_yaw_target = max(min(body_yaw_target, 1.5), -1.5)
        face_pitch_target = max(min(face_pitch_target, 0.8), -0.8)

        self.body_yaw = self.body_pid.update(body_yaw_target, self.body_yaw)
        self.face_pitch = self.face_pid.update(face_pitch_target, self.face_pitch)

        traj = JointTrajectory()
        traj.joint_names = [
            'body_joint',
            'face_joint_x'
        ]

        point = JointTrajectoryPoint()
        point.positions = [body_yaw_target, face_pitch_target]
        point.time_from_start.sec = 1

        traj.points.append(point)
        self.pub.publish(traj)

def main():
    rclpy.init()
    node = HandTracker()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
