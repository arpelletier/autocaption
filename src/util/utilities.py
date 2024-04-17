import os
import re
from datetime import datetime

from ..logger import setup_logger

# Initialize logger
logger = setup_logger()


def seconds_to_vtt_format(seconds):
    """Converts seconds to a VTT-style timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:06.3f}"


def parse_timestamps_to_frames(input_dir):
    """ Parses filenames in a directory to map VTT-style timestamps to filenames. """
    timestamp_to_filename = {}
    for filename in os.listdir(input_dir):
        if 'frame' in filename and filename.endswith('.jpg'):
            parts = filename.split('_')
            frame_number, timestamp_with_s = parts[-2], parts[-1].split('s.jpg')[0]
            timestamp_seconds = float(timestamp_with_s)
            formatted_timestamp = seconds_to_vtt_format(timestamp_seconds)
            timestamp_to_filename[formatted_timestamp] = filename
    return timestamp_to_filename


def parse_time_to_seconds(t):
    """ Converts a time string in 'HH:MM:SS.mmm' format to total seconds. """
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
        if file.startswith('._'): # skip metadata files
            continue
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

def find_files_recursive(directory, extension='.mp4', test=False):
    """ Recursively finds all files with the specified extension in the directory. """
    matched_files = []
    for root, dirs, f in os.walk(directory):
        for file in f:
            if file.startswith('._') or not file.endswith(extension): # skip metadata files
                continue
            matched_files.append(os.path.join(root, file))

    # For testing purposes, only use the video files in "./data/Test". These are removed otherwise
    if test:
        matched_files = [m for m in matched_files if "./data/Test/" in m]
    else:
        matched_files = [m for m in matched_files if "./data/Test/" not in m]
    return matched_files


def read_vtt(vtt_file):
    """ Parses a VTT file into a dictionary mapping timestamps to text. """

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
                line_num += 1
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")
    print(f"Wrote to {output_file}")


def match_text_to_frames(time_range_to_text, time_to_frame):
    """ Convert frame times to seconds for easier comparison """
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
