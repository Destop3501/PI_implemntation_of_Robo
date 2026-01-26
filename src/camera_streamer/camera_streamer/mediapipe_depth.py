import socket
import json
import math

# Listen to Handshake Identifier
in_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
in_sock.bind(("127.0.0.1", 5005))

FOCAL_PX = 537 # From your tf2_runner1.py
HAND_WIDTH_METERS = 6 

while True:
    data, _ = in_sock.recvfrom(1024)
    msg = json.loads(data)
    
    if msg["detected"]:
        # Estimate depth based on normalized coordinates or hand scale
        # Here we use a ratio logic for depth
        depth = (HAND_WIDTH_METERS * FOCAL_PX) / max(msg["x"], 0.01) # Simplified depth scaling
        
        final_payload = {
            "x": msg["x"],
            "y": msg["y"],
            "depth": depth
        }
        out_sock.sendto(json.dumps(final_payload).encode(), BRIDGE_ADDR)