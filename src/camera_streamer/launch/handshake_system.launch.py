from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='camera_streamer',
            executable='handshake_broadcaster',
            name='handshake_broadcaster',
            output='screen'
        )
    ])
