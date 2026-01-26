# ROS2 Jazzy Hand Controller on Raspberry Pi 4

This document describes how to deploy and run the hand controller on a Raspberry Pi 4 running **Debian Bookworm**.

## Prerequisites

1. **Raspberry Pi 4** (4GB or 8GB RAM recommended)
2. **PiCamera v2** correctly connected
3. **Docker** and **Docker Compose** installed:
   ```bash
   curl -sSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # Logout and login again
   ```
4. **VNC Viewer** installed on your client PC.

## Setup Instructions

### 1. Project Files
Ensure all project files are in `~/nema` on the Pi.

### 2. Build the Docker Image
From the `~/nema` directory, run:
```bash
docker-compose build
```
*Note: This might take 20-30 minutes on a Pi 4 as it builds MediaPipe and ROS2 dependencies.*

### 3. Run the System
```bash
docker-compose up
```

## Viewing the Output

Since the Pi is running headless or via VNC:
1. Connect to the Pi via **VNC Viewer**.
2. Open a terminal on the Pi desktop.
3. The OpenCV preview window will appear on the Pi's desktop (X11 display `:0`).
4. You should see "Handshake Broadcaster (Pi)" with FPS monitoring.

## Performance Tips

- **Model Complexity**: We have set `model_complexity=0` to ensure smooth tracking on the Pi 4.
- **Resolution**: Lowering the resolution in `pi_camera_wrapper.py` can further improve FPS.
- **Cooling**: MediaPipe is CPU intensive; ensure your Pi has proper cooling (heat sinks or fan).

## Troubleshooting

- **Camera Not Found**: Ensure the flat cable is correctly oriented. Run `libcamera-hello` to verify the hardware.
- **Permission Denied**: If Docker fails to access `/dev/video0`, ensure the user is in the `video` and `render` groups.
- **X11 Errors**: Ensure the `DISPLAY` environment variable matches your VNC session (usually `:0` or `:1`).

## Branch Info
This implementation is on the `Impliment_pi` branch.
