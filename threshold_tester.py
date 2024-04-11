import cv2
import os
import sys
from skimage.metrics import structural_similarity as ssim
import numpy as np

def extract_frames(video_path, output_folder, similarity_threshold=0.95):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video = cv2.VideoCapture(video_path)
    
    frame_count = 0
    last_frame = None

    while True:
        success, frame = video.read()
        if not success:
            break

        # Convert the frame to grayscale to reduce computational complexity
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Compare the current frame with the last frame using SSIM
        if last_frame is not None:
            sim = ssim(last_frame, gray_frame)

            # If the similarity is above the threshold, skip saving this frame
            if sim > similarity_threshold:
                continue

        # Update the last frame and save the current frame
        last_frame = gray_frame
        output_path = os.path.join(output_folder, f"frame_{frame_count:04d}.jpg")
        cv2.imwrite(output_path, frame)
        
        frame_count += 1

    video.release()


def grid_test(video_path, output_folder, thresholds=[0.95,0.9,0.85,0.8,0.75,0.7]):
    
    for thresh in thresholds:
        print(thresh)
        threshold_output = os.path.join(output_folder,'threshold_%s'%(thresh))
        extract_frames(video_path, threshold_output, similarity_threshold=thresh)



### Parse arguments ###
if len(sys.argv) < 2:
	print("Incorrect usage.")
	print("python autocaption.py video.mp4")
	sys.exit(0)


# Usage
video_path = sys.argv[1]  
output_folder = 'threshold_tester'  # Folder to save the extracted images

grid_test(video_path, output_folder)

