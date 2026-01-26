import os
from ament_index_python.packages import get_package_share_directory

import launch
from launch.conditions import IfCondition
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, LaunchConfiguration, IfElseSubstitution, EqualsSubstitution

import launch_ros
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

from moveit_configs_utils import MoveItConfigsBuilder

package_name_moveit_config = 'nema_moveit_config'

def generate_launch_description():


    Nema_gazebo_pkg = get_package_share_directory("nema_gazebo")
    gazebo_launch_file = os.path.join(Nema_gazebo_pkg,'launch','gazebo.launch.py')
    Nema_camera_pkg = get_package_share_directory("camera_streamer")
    mediapipe_launch_file = os.path.join(Nema_camera_pkg, 'launch', 'mediapipe.launch.py')

    Nema_moveit_pkg = FindPackageShare(package=package_name_moveit_config).find(package_name_moveit_config)

    print(Nema_moveit_pkg)
    
    initial_positions_file_path = os.path.join(Nema_moveit_pkg,'config', 'initial_positions.yaml')
    joint_limits_file_path = os.path.join(Nema_moveit_pkg,'config', 'joint_limits.yaml')
    kinematics_file_path = os.path.join(Nema_moveit_pkg,'config', 'kinematics.yaml')
    moveit_controllers_file_path = os.path.join(Nema_moveit_pkg,'config', 'moveit_controllers.yaml')
    srdf_model_path = os.path.join(Nema_moveit_pkg,'config', 'nema_robot.srdf')
    pilz_cartesian_limits_file_path = os.path.join(Nema_moveit_pkg,'config', 'pilz_cartesian_limits.yaml')
    rvizfile = os.path.join(Nema_moveit_pkg,'rviz', 'moveit.rviz')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')

    declared_arguments = [
        DeclareLaunchArgument(
            name='use_sim_time',
            default_value='true',
            description='Flag to enable use sim time'
        ),
        DeclareLaunchArgument(
            name='use_rviz',
            default_value='true',
            description='Whether to start RViz'
        )
    ]

    load_gazebo_launch_py = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource([
            gazebo_launch_file
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
    )

    robot_spawner_node = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '-topic', '/robot_description',
            '-allow_renaming', 'true',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.0',
        ]
    )
    

    # Create MoveIt configuration
    moveit_config = (
        MoveItConfigsBuilder('NEma', package_name=package_name_moveit_config)
        .trajectory_execution(file_path=moveit_controllers_file_path)
        .robot_description_semantic(file_path=srdf_model_path)
        .joint_limits(file_path=joint_limits_file_path)
        .robot_description_kinematics(file_path=kinematics_file_path)
        .planning_pipelines(
            pipelines=["ompl", "pilz_industrial_motion_planner", "stomp"],
            default_planning_pipeline="ompl"
        )
        .planning_scene_monitor(
            publish_robot_description=False,
            publish_robot_description_semantic=True,
            publish_planning_scene=True,
        )
        .pilz_cartesian_limits(file_path=pilz_cartesian_limits_file_path)
        .to_moveit_configs()
    )

    move_group_capabilities = {"capabilities": "move_group/ExecuteTaskSolutionCapability"}

    start_move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {'use_sim_time': use_sim_time},
            {'start_state': {'content': initial_positions_file_path}},
            # move_group_capabilities,
        ],
    )

    start_rviz_node = Node(
            condition=IfCondition(use_rviz),
            package="rviz2",
            executable="rviz2",
            arguments=[
                "-d",[rvizfile]
            ],
            output="screen",
            parameters=[
                moveit_config.robot_description,
                moveit_config.robot_description_semantic,
                moveit_config.planning_pipelines,
                moveit_config.robot_description_kinematics,
                moveit_config.joint_limits,
                {'use_sim_time': use_sim_time}
            ],
        )

    load_mediapipe_launch_py = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource([
            mediapipe_launch_file
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
    )
    
    # delayed_mediapipe = TimerAction(
    #     period=5.0,
    #     actions=[load_mediapipe_launch_py]
    # )

    move_spawners_chain = RegisterEventHandler(
        OnProcessExit(
            target_action=robot_spawner_node,
            on_exit=[
                TimerAction(
                period=10.0,   # wait AFTER robot is spawned
                actions=[
                    start_move_group_node, 
                    start_rviz_node, 
                    # delayed_mediapipe
                ]
            )],
        )
    )
    delayed_moveit_rviz_mediapipe = TimerAction(
        period=10.0,
        actions=[
            start_move_group_node,
            start_rviz_node,
            load_mediapipe_launch_py
        ]
    )

    node_list=[
        load_gazebo_launch_py,
        robot_spawner_node,
        
        delayed_moveit_rviz_mediapipe,
        
    ]
#     node_list = [
#     load_gazebo_launch_py,
#     TimerAction(
#         period=10.0,  # wait for Gazebo + robot to spawn
#         actions=[
#             start_move_group_node,
#             start_rviz_node,
#             TimerAction(      # wait 5s before MediaPipe
#                 period=5.0,
#                 actions=[load_mediapipe_launch_py]
#             )
#         ]
#     )
# ]
    return LaunchDescription(declared_arguments + node_list)

