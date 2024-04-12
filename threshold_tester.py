import cv2
import os
import sys
from skimage.metrics import structural_similarity as ssim
import numpy as np
from tqdm import tqdm 
from concurrent.futures import ThreadPoolExecutor

def save_frame(output_path, frame):
    cv2.imwrite(output_path, frame)

def extract_frames(video_path, output_folder, similarity_threshold=0.95):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video = cv2.VideoCapture(video_path)
    total_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    frame_count = 0
    last_frame = None

    with ThreadPoolExecutor(max_workers=5) as executor:  # Adjust max_workers as needed
        pbar = tqdm(total=total_count, desc="Extracting Frames", unit="frame")
        
        while True:
            success, frame = video.read()
            if not success:
                break

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if last_frame is not None:
                sim = ssim(last_frame, gray_frame)

                if sim > similarity_threshold:
                    pbar.update(1)
                    continue

            last_frame = gray_frame
            output_path = os.path.join(output_folder, f"frame_{frame_count:04d}.jpg")
            
            # Submit the save task to the thread pool
            executor.submit(save_frame, output_path, frame)
            
            frame_count += 1
            pbar.update(1)

        pbar.close()

    video.release()



def grid_test(video_path, output_folder, thresholds=[0.95,0.9,0.85,0.8,0.75,0.7]):

    print("Starting threshold tester. Thresholds: ",str(thresholds))    
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

