import os
import gc
from PIL import Image
from reportlab.pdfgen import canvas
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import cv2
from skimage.metrics import structural_similarity as ssim

from ..logger import setup_logger
from ..util.utilities import parse_timestamps_to_frames, parse_time_to_seconds

# Initialize logger
logger = setup_logger()


def create_pdf_from_frames(frames_folder, output_pdf_path='video_frames.pdf'):
    # Extract time of each frame
    time_to_frame = parse_timestamps_to_frames(frames_folder)
    frame_times = {parse_time_to_seconds(time): frame for time, frame in time_to_frame.items()}
    sorted_frame_times = sorted(frame_times.items())

    # List of ordered frames by time
    ordered_frames = [os.path.join(frames_folder, frame) for _, frame in sorted_frame_times]

    # Start creating the PDF
    if ordered_frames:
        c = canvas.Canvas(output_pdf_path)

        # Assuming all images have the same dimensions
        first_image = Image.open(ordered_frames[0])
        width, height = first_image.size
        c.setPageSize((width, height))

        for frame_path in ordered_frames:
            c.drawImage(frame_path, 0, 0, width, height)
            c.showPage()  # End the current page and start a new one

        c.save()
        logger.info(f"PDF created successfully at {output_pdf_path}")
    else:
        logger.info("No frames were found to add to the PDF.")


def process_frame(frame_data):
    try:
        frame, next_frame, output_path, similarity_threshold = frame_data
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_next_frame = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)

        similarity = ssim(gray_frame, gray_next_frame)

        logger.info(f"{output_path}: {similarity}")

        if similarity < similarity_threshold:
            cv2.imwrite(output_path, frame)
            return True

    except Exception as e:
        logger.error(f"Error processing frame: {e}")
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


def extract_frames_with_timestamps(video_path, output_folder, similarity_threshold=0.95, num_workers=5, skip_frames_fps=1.0):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Get the name of the video w/o file extension
    base_name = os.path.basename(video_path)
    file_name_without_extension = os.path.splitext(base_name)[0]

    video = cv2.VideoCapture(video_path)

    # Get the frame rate of the video
    fps = video.get(cv2.CAP_PROP_FPS)
    skip_frames = skip_frames_fps * fps

    total_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0
    last_frame = None
    last_output_path = None
    last_saved_frame_index = -skip_frames  # Initialize so that the first frame can be set as last_frame
    task_queue = Queue(maxsize=num_workers * 2)

    logger.info(f"Starting frame extraction. Video file: {video_path}")
    logger.info(f"Settings: Similarity threshold {similarity_threshold}, num_workers {num_workers}, skip_frames {skip_frames}")
    logger.info(f"Output directory: {output_folder}")

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

            if frame_count - last_saved_frame_index == skip_frames:

                # Calculate the timestamp of the current frame
                timestamp = frame_count / fps
                formatted_timestamp = f"{timestamp:.3f}"  # Format to 3 decimal places

                filename = f"{file_name_without_extension}_frame_{frame_count:04d}_{formatted_timestamp}s.jpg"

                if last_frame is not None:
                    task_queue.put((last_frame, frame, last_output_path, similarity_threshold))
                last_frame = frame
                last_output_path = os.path.join(output_folder, filename)
                last_saved_frame_index = frame_count  # Update the index of the last saved frame

            frame_count += 1
            pbar.update(1)

        # Signal workers to stop processing
        for _ in range(num_workers):
            task_queue.put(None)

        pbar.close()

    video.release()
    logger.info('Video released and processing done')
    gc.collect()
    return True
