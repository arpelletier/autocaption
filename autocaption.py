import argparse
import os
import sys
import logging
import re
from tqdm import tqdm
import gc
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

from PIL import Image
import pytesseract
import cv2
from skimage.metrics import structural_similarity as ssim


def seconds_to_vtt_format(seconds):
    """Converts seconds to a VTT-style timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:06.3f}"


def parse_timestamps_to_frames(input_dir):
    """
    Parses filenames in a directory to map VTT-style timestamps to filenames.
    """
    timestamp_to_filename = {}
    for filename in os.listdir(input_dir):
        if filename.startswith('frame_') and filename.endswith('.jpg'):
            # Example filename: 'frame_6800_272.000s.jpg'
            parts = filename.split('_')
            if len(parts) == 3:
                frame_number, timestamp_with_s = parts[1], parts[2].split('s.jpg')[0]
                timestamp_seconds = float(timestamp_with_s)
                formatted_timestamp = seconds_to_vtt_format(timestamp_seconds)
                timestamp_to_filename[formatted_timestamp] = filename

    return timestamp_to_filename


def parse_time_to_seconds(t):
    """Converts a time string in 'HH:MM:SS.mmm' format to total seconds."""
    return datetime.strptime(t, '%H:%M:%S.%f').time().hour * 3600 + \
           datetime.strptime(t, '%H:%M:%S.%f').time().minute * 60 + \
           datetime.strptime(t, '%H:%M:%S.%f').time().second + \
           datetime.strptime(t, '%H:%M:%S.%f').time().microsecond / 1e6


def find_files(directory, require_audio=False, require_captions=False):
    """ Checks for .mp4, .m4a, and .vtt files in directory """
    video_file = None
    audio_file = None
    caption_file = None

    # Loop through all files in the specified directory
    for file in os.listdir(directory):
        if file.endswith('.mp4'):
            video_file = os.path.join(directory, file)
        elif file.endswith('.m4a'):
            audio_file = os.path.join(directory, file)
        elif file.endswith('.vtt'):
            caption_file = os.path.join(directory, file)

    # Check for mandatory .mp4 file
    if not video_file:
        raise FileNotFoundError("No .mp4 video file found in the directory.")

    # Check for optional .m4a and .vtt files based on flags
    if require_audio and not audio_file:
        raise FileNotFoundError("Required .m4a audio file not found in the directory.")
    if require_captions and not caption_file:
        raise FileNotFoundError("Required .vtt caption file not found in the directory.")

    return {
        'video': video_file,
        'audio': audio_file,
        'caption': caption_file
    }


def read_vtt(vtt_file):
    """Parses a VTT file into a dictionary mapping timestamps to text."""

    # Compile regex to match timestamps and initialize dictionary for captions
    timestamp_regex = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')
    captions = {}

    try:
        with open(vtt_file, 'r', encoding='utf-8') as file:
            current_start, current_end = None, None
            current_text = []

            for line in file:
                match = timestamp_regex.match(line.strip())
                if match:
                    if current_start:
                        captions[(current_start, current_end)] = ' '.join(current_text)
                    current_start, current_end = match.groups()
                    current_text = []
                elif line.strip() and not line.strip().isdigit():
                    current_text.append(line.strip())

            if current_start:  # Save the last caption block
                captions[(current_start, current_end)] = ' '.join(current_text)

    except FileNotFoundError:
        print(f"File not found: {vtt_file}")
    except Exception as e:
        print(f"Error reading {vtt_file}: {e}")

    return captions


def write_vtt(captions_dict, output_file):
    """ Writes a dictionary of captions into a VTT file format. """
    heading_text = "WEBVTT - This file was automatically generated by VIMEO and edited using autocaption.py"
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(heading_text+"\n\n")  # VTT header
            line_num = 0
            for (start, end), caption in captions_dict.items():
                file.write(f"{line_num}\n{start} --> {end}\n{caption}\n\n")
                line_num+=1
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")
    print(f"Wrote to {output_file}")


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


def extract_frames_with_timestamps(video_path, output_folder, similarity_threshold=0.95, num_workers=5, skip_frames_fps=1.0):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

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

    logging.info(f"Starting frame extraction. Video file: {video_path}")
    logging.info(f"Settings: Similarity threshold {similarity_threshold}, num_workers {num_workers}, skip_frames {skip_frames}")
    logging.info(f"Output directory: {output_folder}")

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

                filename = f"frame_{frame_count:04d}_{formatted_timestamp}s.jpg"

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
    logging.info('Video released and processing done')
    gc.collect()
    return True


def match_text_to_frames(time_range_to_text, time_to_frame):
    # Convert frame times to seconds for easier comparison
    frame_times = {parse_time_to_seconds(time): frame for time, frame in time_to_frame.items()}
    sorted_frame_times = sorted(frame_times.items())  # Sort by time (seconds)

    # Prepare the dictionary to hold frame to text mappings
    frame_to_text = {frame: {} for frame in time_to_frame.values()}

    # Iterate through each time range and text
    for (start, end), text in time_range_to_text.items():
        start_sec = parse_time_to_seconds(start)
        end_sec = parse_time_to_seconds(end)

        # Find the frame interval this text falls into
        previous_time = 0
        for time, frame in sorted_frame_times:
            if previous_time <= start_sec < time:
                frame_to_text[frame][start, end] = text
            previous_time = time

    return frame_to_text


def extract_image_text(input_dir):
    """ Extracts text from all .jpg images in the specified directory. """
    text_dict = {}
    for filename in os.listdir(input_dir):
        if filename.endswith('.jpg'):
            image_path = os.path.join(input_dir, filename)
            image = Image.open(image_path)
            extracted_text = pytesseract.image_to_string(image)
            text_dict[filename] = extracted_text.strip()
    # TODO: Resulting text is very dirty and needs data cleaning.
    return text_dict


def extract_image_description(input_dir):
    ''' This function generates a description of the .jpg image '''
    # TODO complete implementation
    print("This function is not implemented yet.")
    return None


def correct_captions(timestamp_to_text, timestamp_to_frames=None, frame_to_transcript=None,
                     frame_to_onscreen_text=None, frame_to_description=None):
    ''' This function uses the information available to autocorrect the .vtt caption file '''
    #TODO complete implementation
    print("Implementation incomplete.")
    return timestamp_to_text


def auto_caption(input_files, output_folder='.', similarity_threshold = 0.95, fps=1.0, num_workers=5):

    # Read auto generated caption
    timestamp_to_text = read_vtt(input_files['caption'])
    logging.info(f"Extracted {len(timestamp_to_text)} lines from {input_files['caption']}")

    # Extract frames
    frames_output_folder = os.path.join(output_folder, "frames")
    extracted_frames_successful = extract_frames_with_timestamps(input_files['video'],frames_output_folder,
                                                                 similarity_threshold=similarity_threshold,
                                                                 num_workers=num_workers, skip_frames_fps=fps)

    # Prepare multimodal data
    if extracted_frames_successful:

        # Extract timestamps for frames
        timestamp_to_frames = parse_timestamps_to_frames(frames_output_folder)

        # Extract text from frames
        frame_to_onscreen_text = extract_image_text(frames_output_folder)

        # Extract image description
        frame_to_description = extract_image_description(frames_output_folder)

        # Match frames to auto-generated timestamps
        frame_to_transcript = match_text_to_frames(timestamp_to_text, timestamp_to_frames)

        # Edit the vtt file
        corrected_timestamp_to_text = correct_captions(timestamp_to_text,
                                                       timestamp_to_frames=timestamp_to_frames,
                                                       frame_to_transcript=frame_to_transcript,
                                                       frame_to_onscreen_text=frame_to_onscreen_text,
                                                       frame_to_description=frame_to_description
                                                       )
    else:
        corrected_timestamp_to_text = correct_captions(timestamp_to_text) # No image / on-screen info

    # Write corrected captions to file
    vtt_output_file = os.path.join(output_folder,"autocorrected_autogenerated_captions.vtt")
    write_vtt(timestamp_to_text, vtt_output_file)


def validate_paths(video_path, caption_path, video_folder_path):
    # Check if at least one of the paths is valid
    valid_video = video_path and os.path.isfile(video_path)
    valid_caption = caption_path and os.path.isfile(caption_path)
    valid_folder = video_folder_path and os.path.isdir(video_folder_path)

    # At least one of video or caption file must be valid if specified
    if not (valid_video or valid_caption or valid_folder):
        print("Error: Please provide a valid path to a video file, caption file, or an input folder.")
        print("Video path valid:", valid_video)
        print("Caption path valid:", valid_caption)
        print("Folder path valid:", valid_folder)
        sys.exit(1)


def validate_parameters(sim_thresh, fps, num_workers):
    if not (0.0 <= sim_thresh <= 1.0):
        raise ValueError("Similarity threshold must be a float between 0.0 and 1.0.")
    if fps <= 0:
        raise ValueError("Frames per second must be a non-negative, non-zero value.")
    if num_workers <= 1:
        raise ValueError("Number of workers must be greater than 1")


def setup_arg_parser():
    parser = argparse.ArgumentParser(description="Automatically corrects a .vtt caption file based on given parameters.")

    # Add arguments to CLI
    parser.add_argument('-s',"--sim_thresh", type=float, default=0.95,
                        help="Similarity threshold for frame comparison. Default is 0.95.")
    parser.add_argument('-f',"--fps", type=float, default=1.0,
                        help="Frames per second to be processed for frame skipping. Lower fps processes faster. Default is 1.0 fps.")
    parser.add_argument('-w',"--num_workers", type=int, default=5,
                        help="Number of workers to parse video into non-redundant frames. Greater workers uses more computational resources")

    # Arguments for video and caption paths or an input folder
    parser.add_argument('-v',"--video", type=str, default="",
                        help="Path to the video file (e.g., video.mp4).")
    parser.add_argument('-c',"--vtt", type=str, default="",
                        help="Path to the VTT caption file. (e.g., auto_generated_captions.vtt from Vimeo)")
    parser.add_argument('-i',"--input_folder", type=str, default="",
                        help="Path to the input folder containing video and VTT files, automatically identify files.")

    # Argument for the output folder
    parser.add_argument('-o',"--output_folder", type=str, default="",
                        help="Path to the output folder where results will be stored.")

    return parser


def main():

    # Parse arguments
    parser = setup_arg_parser()
    args = parser.parse_args()

    # Validate input paths
    validate_paths(args.video, args.vtt, args.input_folder)
    if args.input_folder:
        input_files = find_files(args.input_folder)
        logging.info(f"Extracted files: {input_files}")
    else:
        input_files = {}
        if args.vtt:
            input_files['caption'] = args.vtt
        if args.video:
            input_files['video'] = args.video

    # Validate parameters
    try:
        validate_parameters(args.sim_thresh, args.fps, args.num_workers)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Configure logging
    log_folder = './log/' if len(args.output_folder) == 0 else args.output_folder
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    logfile = os.path.join(log_folder,'autocaption_log.txt')
    logging.basicConfig(filename=logfile, filemode='w', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Run autocaption
    logging.info(f"Starting autocaption. Arguments: {args}")
    auto_caption(input_files, similarity_threshold = args.sim_thresh, fps=args.fps, output_folder=args.output_folder)


if __name__ == "__main__":
    main()

'''
TODO: 
- Prototype an image to description model
- Make API calls to a multimodal LLM to correct .vtt caption (Google Gemini)
- Test a local multimodal LLM to see its performance compared to the multimodal one
- Write a response parser to automatically correct the .vtt caption.
- Write an interactive program to step through the .vtt correction, accepting user input/suggestions to co-edit the captions
'''