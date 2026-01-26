import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():
    # Define the path to your virtual environment's python executable
    venv_python = '/home/ruwan/nema/src/camera_streamer/camera_streamer/mediapipevenv3.9/bin/python3.9'
    
    # Define the path to your python script
    script_path = '/home/ruwan/nema/src/camera_streamer/camera_streamer/mediapipe_detector.py'

    mediapipe_process = ExecuteProcess(
        cmd=[venv_python, script_path],
        name='mediapipe_process',
        output='screen',
        cwd='/home/ruwan/nema/src/camera_streamer/camera_streamer/',
        shell=False
    )
    socketNode = Node(
        package='camera_streamer',
        executable='socket_reciever',
        name='hand_socket_receiver',
        output='screen'
    )
    Face_Tracking = Node(
        package='camera_streamer',
        executable='Watch_the_hand',
        name='hand_tracking_controller',
        output='screen'
    )

    return LaunchDescription([
        mediapipe_process,
        socketNode,
        Face_Tracking
    ])