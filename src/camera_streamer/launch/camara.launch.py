import os
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    venv_path = os.path.expanduser('~/nema/mp_venv')
    activate_and_run = f"source {venv_path}/bin/activate"

    return LaunchDescription([
        Node(
            package='camera_streamer',
            executable='handshake_broadcaster',  # This must match the entry_point in setup.py
            name='handshake_broadcaster_node',
            output='screen',
            prefix=['/bin/bash -c "', activate_and_run, '" --'],
            parameters=[{
                'video_device': '/dev/video0', # Use /dev/video0 if video2 fails
                'image_size': [320, 240],
                # 'camera_frame_id': 'camara_link_optical'
            }]
        )
    ])