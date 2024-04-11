import cv2
import os
import sys


def extract_frames_with_timestamps(video_path, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load the video
    video = cv2.VideoCapture(video_path)

    # Get the frame rate of the video
    fps = video.get(cv2.CAP_PROP_FPS)

    frame_count = 0
    timestamps = {}  # Dictionary to store frame timestamps

    while True:
        success, frame = video.read()
        if not success:
            break

        # Calculate the timestamp of the current frame
        timestamp = frame_count / fps
        formatted_timestamp = f"{timestamp:.3f}"  # Format to 3 decimal places

        # Save the frame as a JPEG file
        filename = f"frame_{frame_count:04d}_{formatted_timestamp}s.jpg"
        output_path = os.path.join(output_folder, filename)
        cv2.imwrite(output_path, frame)

        # Store the timestamp in the dictionary
        timestamps[filename] = formatted_timestamp

        frame_count += 1

    video.release()

    # Optionally, save the timestamps to a file
    with open(os.path.join(output_folder, 'timestamps.txt'), 'w') as f:
        for filename, timestamp in timestamps.items():
            f.write(f"{filename}: {timestamp}s\n")

### Parse arguments ###
if len(sys.argv) < 2:
	print("Incorrect usage.")
	print("python autocaption.py video.mp4")
	sys.exit(0)


# Usage
video_path = sys.argv[1]  
output_folder = 'extracted_frames'  # Folder to save the extracted images

extract_frames_with_timestamps(video_path, output_folder)

