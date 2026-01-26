#!/bin/bash
set -e

# source ros2 setup
source "/opt/ros/jazzy/setup.bash"

# source local setup if built
if [ -f "/workspace/install/setup.bash" ]; then
    source "/workspace/install/setup.bash"
fi

exec "$@"
