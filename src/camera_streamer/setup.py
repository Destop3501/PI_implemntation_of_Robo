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
    description='A hand controller transmitter for Pi using Mediapipe and PiCamera v2',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'handshake_broadcaster = camera_streamer.handshake_broadcaster:main',
            'mediapipe_detector = camera_streamer.mediapipe_detector:main',
        ],
    },
)
