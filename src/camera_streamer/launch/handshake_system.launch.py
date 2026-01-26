import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():

    # -------- PATHS (CHANGE IF NEEDED) --------
    venv_path = os.path.expanduser(
        '~/nema/src/camera_streamer/camera_streamer/mediapipevenv3.9'
    )

    mediapipe_script = os.path.expanduser(
        '~/nema/src/camera_streamer/camera_streamer/mediapipe_identifier1.py'
    )

    # -------- MediaPipe Process (Python 3.9) --------
    mediapipe_process = ExecuteProcess(
        cmd=[
            f'{venv_path}/bin/python',
            mediapipe_script
        ],
        name='mediapipe_process',
        output='screen'
    )

    # -------- ROS 2 Bridge Node (Python 3.12) --------
    mediapipe_bridge_node = Node(
        package='camera_streamer',
        executable='mediapipe_bridge',
        name='mediapipe_bridge',
        output='screen'
    )

    # -------- TF + YOLO Node --------
    tf_node = Node(
        package='camera_streamer',
        executable='tf2_runner',
        name='depth_tf_broadcaster',
        output='screen'
    )

    # -------- Launch Everything --------
    return LaunchDescription([
        mediapipe_process,
        mediapipe_bridge_node,
        tf_node
    ])
