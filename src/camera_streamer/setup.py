from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'camera_streamer'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share',package_name,'launch'),glob(os.path.join('launch','*launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ruwan',
    maintainer_email='ruwan@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'stream_publisher = camera_streamer.stream_publisher:main',
            'web_cam = camera_streamer.web_cam:main',
            'handshake_broadcaster = camera_streamer.handshake_broadcaster:main',
            'tf2_runner=camera_streamer.tf2_runner1:main',
            'mediapipe_identifier=camera_streamer.mediapipe_identifier1:main',
            'mediapipe_bridge=camera_streamer.mediapipe_bridge:main',
            'Watch_the_hand = camera_streamer.Watch_the_hand:main',
            'socket_reciever=camera_streamer.socket_reciever:main',
            'fully_script_of_rotation=camera_streamer.fully_script_of_rotation:main'
        ],
    },
)
