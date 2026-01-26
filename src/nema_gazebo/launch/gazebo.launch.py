import os
from ament_index_python.packages import get_package_share_directory

import launch
from launch.conditions import IfCondition
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, IfElseSubstitution, EqualsSubstitution

import launch_ros
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    Nema_Description_pkg = get_package_share_directory("nema_description")
    rviz_launch_file = os.path.join(Nema_Description_pkg,'launch','rviz.launch.py')
    urdffile = os.path.join(Nema_Description_pkg,'urdf', 'model.urdf.xacro')

    Nema_gazebo_pkg = get_package_share_directory("nema_gazebo")
    yamlfile = os.path.join(Nema_gazebo_pkg,'config','ros2_controllers.yaml')
    worldgazebo = os.path.join(Nema_gazebo_pkg,'gazebo_world','empty.world')

    camara_pkg = get_package_share_directory("camera_streamer")
    camara_launch_file = os.path.join(camara_pkg,"launch","camara.launch.py")

    pkg_ros_gz_sim = launch_ros.substitutions.FindPackageShare('ros_gz_sim').find('ros_gz_sim')
    gz_sim_luanch = os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')

    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    use_sim_time = LaunchConfiguration('use_sim_time')

    robot_description = ParameterValue(Command([
            "xacro ",
            LaunchConfiguration("model")
        ]),
        value_type=str
    )

    load_rviz_launch_py = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource([
            rviz_launch_file
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items(),
    )

    declared_arguments = [
        DeclareLaunchArgument(
            name='headless',
            default_value='false',
            description='Set to "true" to run Gazebo headlessly.'
        ),
        DeclareLaunchArgument(
            name="model", 
            default_value=urdffile,
            description="Absalute URDF file"
        ),
        DeclareLaunchArgument(
            name='use_sim_time',
            default_value='true',
            description='Flag to enable use sim time'
        ),
        DeclareLaunchArgument(
            name='use_robot_state_pub',
            default_value='true',
            description='Flag to enable robot state publisher'
        ),

    ]
        
    headless = LaunchConfiguration('headless')

    start_gazebo = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource([
            gz_sim_luanch
        ]),
        launch_arguments={"gz_args": IfElseSubstitution(
            headless,
            if_value=["-s -r -v 4 empty.sdf"],
            else_value=[" -r -v 4 empty.sdf"]
            )
        }.items(), 
    )

    gazebo_ros_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        ],
        output='screen'
    )

    start_gazebo_ros_spawner_cmd = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', '/robot_description',
            '-allow_renaming', 'true',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.0',
        ]
    )

    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            {"robot_description": robot_description,
             "use_sim_time": use_sim_time},
            yamlfile
        ],
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
    )

    body_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["body_controller", "--controller-manager", "/controller_manager"],
    )

    leftarm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["leftarm_controller", "--controller-manager", "/controller_manager"],
    )

    rightarm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["rightarm_controller", "--controller-manager", "/controller_manager"],
    )

    spawners_chain = launch.actions.RegisterEventHandler(
        launch.event_handlers.OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[body_controller_spawner,leftarm_controller_spawner, rightarm_controller_spawner],
        )
    )

    # load_camara_launch_py = launch.actions.IncludeLaunchDescription(
    #     launch.launch_description_sources.PythonLaunchDescriptionSource([
    #         camara_launch_file
    #     ]),
    #     launch_arguments={
    #         'use_sim_time': use_sim_time
    #     }.items(),
    # )

    node_list=[
        load_rviz_launch_py,
        start_gazebo,
        gazebo_ros_bridge,
        # start_gazebo_ros_spawner_cmd,
        controller_manager,
        joint_state_broadcaster_spawner,
        # load_camara_launch_py,
        
        spawners_chain
        
    ]
    
    return LaunchDescription(declared_arguments + node_list)

