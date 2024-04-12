import cv2
import os
import sys
from skimage.metrics import structural_similarity as ssim
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import Pool

def process_batch(batch, similarity_threshold=0.95):
    results = []
    for i in range(len(batch) - 1):
        frame, next_frame = batch[i][0], batch[i + 1][0]
        output_path = batch[i][1]

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_next_frame = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)

        if ssim(gray_frame, gray_next_frame) < similarity_threshold:
            results.append((output_path, frame))

    # Consider also freeing the frames after processing to save memory
    return results

def extract_frames(video_path, output_folder, similarity_threshold=0.95, batch_size=50, num_workers=1):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video = cv2.VideoCapture(video_path)
    total_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    batches = []
    current_batch = []
    frame_count = 0

    with Pool(num_workers) as pool:
        pbar = tqdm(total=total_count, desc="Extracting Frames", unit="frame")
        
        while True:
            success, frame = video.read()
            if not success:
                if current_batch:
                    batches.append(current_batch)
                break

            output_path = os.path.join(output_folder, f"frame_{frame_count:04d}.jpg")
            current_batch.append((frame, output_path))
            
            if len(current_batch) == batch_size:
                batches.append(current_batch)
                current_batch = []
            
            frame_count += 1
            pbar.update(1)

        processed_batches = pool.map(process_batch, batches)

        pbar.close()

    video.release()

    # Simplify the edge checking and saving logic
    with ThreadPoolExecutor(max_workers=num_workers) as writer:
        for batch in processed_batches:
            for path, frame in batch:
                writer.submit(cv2.imwrite, path, frame)

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

