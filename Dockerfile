# Use official ROS2 Jazzy image as base
FROM ros:jazzy-ros-base

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for MediaPipe, OpenCV, and PiCamera
RUN apt-get update && apt-get install -y \
    python3-pip \
    libcamera-dev \
    libcamera-tools \
    libcap-dev \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Install MediaPipe (ensure we get the ARM64 version)
RUN pip3 install --no-cache-dir --break-system-packages \
    mediapipe \
    numpy \
    setuptools \
    picamera2

# Pre-download MediaPipe models to avoid runtime download issues
RUN python3 -c "import mediapipe as mp; mp.solutions.hands.Hands(model_complexity=0); mp.solutions.pose.Pose(model_complexity=0)"

# Install ROS2 Desktop components (for Rviz if needed, though we use base for now)
# User wants "everything inside the pi", so we add common tools
RUN apt-get update && apt-get install -y \
    ros-jazzy-desktop \
    ros-jazzy-tf2-ros \
    ros-jazzy-geometry-msgs \
    ros-jazzy-trajectory-msgs \
    ros-jazzy-joint-trajectory-controller \
    ros-jazzy-joint-state-broadcaster \
    ros-jazzy-xacro \
    && rm -rf /var/lib/apt/lists/*

# Setup workspace
ENV WORKSPACE=/workspace
WORKDIR $WORKSPACE

# Entrypoint setup
COPY ./ros_entrypoint_pi.sh /
RUN chmod +x /ros_entrypoint_pi.sh

# User environment
ENV DISPLAY=:0
ENV QT_X11_NO_MITSHM=1

ENTRYPOINT ["/ros_entrypoint_pi.sh"]
CMD ["bash"]
