import json
import re
from collections import deque
from datetime import datetime

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import serial

# Max number of points to keep in live plot
max_points = 1000
timestamps = deque(maxlen=max_points)
dst_values = deque(maxlen=max_points)
lin_flags = deque(maxlen=max_points)

buffer = ""  # persistent buffer for partial reads

# Check if structure is correct -> error occurred in values
structure_regex = re.compile(r'^\{"raw":.*?,"dst":.*?,"ocf":.*?,"cof":.*?,"lin":.*?}$')


def compute_crc16(data: str) -> int:
    crc = 0xFFFF
    for ch in data:
        crc ^= ord(ch) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x8005) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def verify_checksum(line: str) -> (bool, str):
    if "*" not in line:
        return False, None
    payload, chk = line.rsplit("*", 1)
    try:
        transmitted = int(chk, 16)
    except ValueError:
        return False, None

    computed = compute_crc16(payload)
    return transmitted == computed, payload


# Set up plot
fig, ax = plt.subplots(figsize=(12, 5))
plt.tight_layout()

# calculate error rates
err_total = 0
err_struct = 0
err_value = 0


def update_plot(frame):
    global buffer
    global err_total, err_struct, err_value
    if ser.in_waiting:
        raw = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
        buffer += raw

        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            line = line.strip()
            if not line:
                continue
            try:
                valid, payload = verify_checksum(line)
                err_total += 1
                if not valid:
                    print("Checksum failed:", line)
                    if payload and structure_regex.match(payload):
                        print("Value Error")
                        err_value += 1
                    else:
                        print("Structure Error")
                        err_struct += 1
                    continue
                if err_total % 100 == 0:
                    print(
                        f"Total: {err_total} | Struct Errors: {err_struct} ({err_struct / err_total * 100:.2f}%) | Value Errors: {err_value} ({err_value / err_total * 100:.2f}%)")
                data = json.loads(payload)

                # Add new data point
                timestamps.append(datetime.now().strftime("%H:%M:%S"))
                dst_values.append(data["dst"])
                lin_flags.append(data["lin"])

                # Debug output
                # print(
                #     f"Raw: {data['raw']:>4}, dst: {' ' if data['dst'] >= 0 else ''}{data['dst']:.3f}, "
                #     f"OCF: {data['ocf']}, COF: {data['cof']}, LIN: {data['lin']}"
                # )

            except json.JSONDecodeError:
                print("Invalid JSON:", line)

        # Plot update
        ax.clear()
        ax.set_title("Live dst Plot (last 1000 points)")
        ax.set_xlabel("Time")
        ax.set_ylabel("dst (mm)")
        if dst_values:
            y_min = min(dst_values)
            y_max = max(dst_values)
            margin = 0.5 * (y_max - y_min) if y_max != y_min else 1
            ax.set_ylim(y_min - margin, y_max + margin)
        ax.set_xlim(left=0, right=max_points)

        colors = ['red' if l else 'green' for l in lin_flags]
        ax.scatter(range(len(dst_values)), dst_values, c=colors, s=10)

        if len(timestamps) > 10:
            step = len(timestamps) // 10
            ax.set_xticks(range(0, len(timestamps), step))
            ax.set_xticklabels([timestamps[i] for i in range(0, len(timestamps), step)],
                               rotation=45, ha='right')


# Start serial and animation
try:
    ser = serial.Serial(port='COM3', baudrate=115200, timeout=1)
    print("Connected to", ser.name)
    ani = animation.FuncAnimation(fig, update_plot, interval=100)
    plt.show()
except serial.SerialException as e:
    print("Could not open port:", e)
