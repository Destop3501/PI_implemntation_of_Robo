import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import RegisterEventHandler, LogInfo
from launch.event_handlers import OnProcessExit

def generate_launch_description():
    # 1. Path to your Python 3.9 Virtual Environment
    venv_path = os.path.expanduser('~/nema/src/camera_streamer/camera_streamer/mediapipevenv3.9')
    
    
    # Define the Hand Detector Node
    # The 'prefix' wraps the execution in a bash shell to source the venv properly
    hand_detector_node = Node(
        package='camera_streamer', 
        executable='mediapipe_identifier',
        name='hand_detector',
        output='screen',
        prefix=[f'bash -c "source {venv_path}/bin/activate && python3.9 $@"', ' -- ']
    )

    # Define the YOLO Depth & TF Node (Python 3.12 System)
    depth_tf_node = Node(
        package='camera_streamer',
        executable='tf2_runner',
        name='depth_tf_broadcaster',
        output='screen',
    )

    # Event Handler: When hand_detector exits, start depth_tf_node automatically
    start_yolo_on_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=hand_detector_node,
            on_exit=[
                LogInfo(msg='Hand detected. Handshake node closed. Starting YOLO Depth node...'),
                depth_tf_node
            ]
        )
    )

    return LaunchDescription([
        hand_detector_node,
        start_yolo_on_exit
    ])