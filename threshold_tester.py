import cv2
import re
import os
import sys
import logging
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import gc
from queue import Queue, Empty, Full
import time
import shutil


def process_frame(frame_data):
    try:
        frame, next_frame, output_path, similarity_threshold = frame_data
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_next_frame = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)

        similarity = ssim(gray_frame, gray_next_frame) 

        logging.info(f"{output_path}: {similarity}")
        
        if similarity < similarity_threshold:
            cv2.imwrite(output_path, frame)
            return True


    except Exception as e:
        logging.error(f"Error processing frame: {e}")
    return False

def worker(task_queue):
    while True:
        try:
            task = task_queue.get(timeout=1)  # wait for a task
            if task is None:
                break  # None is a signal to stop processing
            process_frame(task)
        except Empty:
            continue

def extract_frames(video_path, output_folder, similarity_threshold=0.95, num_workers=5):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video = cv2.VideoCapture(video_path)
    total_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0
    last_frame = None
    last_output_path = None
    task_queue = Queue(maxsize=num_workers * 2)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        pbar = tqdm(total=total_count, desc="Extracting Frames", unit="frame")
        
        # Start worker threads
        for _ in range(num_workers):
            executor.submit(worker, task_queue)

        # Enqueue tasks
        while True:
            success, frame = video.read()
            if not success:
                break

            output_path = os.path.join(output_folder, f"frame_{frame_count:04d}.jpg")
            
            if last_frame is not None:
                task_queue.put((last_frame, frame, last_output_path, similarity_threshold))
            
            last_frame = frame
            last_output_path = output_path
            frame_count += 1
            pbar.update(1)

        # Signal workers to stop processing
        for _ in range(num_workers):
            task_queue.put(None)

        pbar.close()

    video.release()
    logging.info('Video released and processing done')
    gc.collect()


def parse_frame_scores_from_log(file_path):
    score_dict = {}
    pattern = re.compile(r"(\S+\.jpg):\s+(\d+\.\d+)")  # Regex to find paths and scores

    with open(file_path, 'r') as file:
        for line in file:
            match = pattern.search(line)
            if match:
                # Extracting file path and score
                file_path = match.group(1)
                score = float(match.group(2))
                score_dict[file_path] = score

    return score_dict


def filter_frames_by_threshold(img2sim, output_folder, thresh):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    images = []  # Track the images above this threshold
    for img, sim in img2sim.items():
        if sim < thresh and os.path.exists(img):
            new_file_path = os.path.join(output_folder, os.path.basename(img))
            logging.info("Copying {} to {}".format(img, new_file_path))
            shutil.copy(img, new_file_path)  # Copy the file to the new directory
            images.append(new_file_path)  # Append the new file path to the list
    return images


def grid_test(video_path, output_folder, thresholds=[0.95,0.9,0.85,0.8,0.75,0.7]):
    logging.info("Starting threshold tester. Thresholds: %s", thresholds)    

    # Extract all frames, calculating similiarity to logfile 
    all_frame_output = os.path.join(output_folder, f'threshold_{1.0}')
    extract_frames(video_path, all_frame_output, similarity_threshold=1.0)

    # Parse the image to similarity file
    img2sim = parse_frame_scores_from_log(logfile)

    for thresh in thresholds:
        logging.info(f"Processing threshold: {thresh}")
        threshold_output = os.path.join(output_folder, f'threshold_{thresh}')
        images = filter_frames_by_threshold(img2sim,threshold_output,thresh)
        print(f"Threshold {thresh}:\t{len(images)} images.")


# Configure logging
logfile = 'log.txt'
logging.basicConfig(filename=logfile, filemode='w', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

### Parse arguments ###
if len(sys.argv) < 2:
    print("Incorrect usage.")
    print("python threshold_tester.py video.mp4")
    sys.exit(0)


# Usage
video_path = sys.argv[1]  
output_folder = 'threshold_test'  # Folder to save the extracted images

grid_test(video_path, output_folder)

