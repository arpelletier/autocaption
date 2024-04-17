import argparse
import os
import sys
import logging

from src.video_processing.frame_extractor import extract_frames_with_timestamps
from src.logger import setup_logger

# Initialize logger
logger = setup_logger('./log/frame_extractor_log.txt')


def frame_extractor(input_files, similarity_threshold=0.95, fps=1.0, num_workers=5):

    for f in input_files:
        logger.info(f"Processing file {f}")
        print(f"Processing file {f}")

        output_folder = os.path.join(os.path.dirname(f),'frames')

        extract_frames_with_timestamps(f, output_folder,
                                       similarity_threshold=similarity_threshold,
                                       num_workers=num_workers,
                                       skip_frames_fps=fps)

        logger.info(f"Written to folder {output_folder}")

    logger.info("Finished frame extraction.")


def find_files_recursive(directory, extension='.mp4', test=False):
    """ Recursively finds all files with the specified extension in the directory. """
    matched_files = []
    for root, dirs, f in os.walk(directory):
        for file in f:
            if file.endswith(extension):
                matched_files.append(os.path.join(root, file))

    # For testing purposes, only use the video files in "./data/Test". These are removed otherwise
    if test:
        matched_files = [m for m in matched_files if "./data/Test/" in m]
    else:
        matched_files = [m for m in matched_files if "./data/Test/" not in m]
    return matched_files


def validate_paths(video_path, video_folder_path):
    # Check if at least one of the paths is valid
    valid_video = video_path and os.path.isfile(video_path)
    valid_folder = video_folder_path and os.path.isdir(video_folder_path)

    # At least one of video or caption file must be valid if specified
    if not (valid_video or valid_folder):
        print("Error: Please provide a valid path to a video file or an input folder.")
        print("Video path valid:", valid_video)
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
    parser = argparse.ArgumentParser(description="Extract frames for all videos in the subdirectory and creates a .pdf")

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
    parser.add_argument('-i',"--input_folder", type=str, default=".",
                        help="Path to the input folder containing video files, searching recursively.")

    return parser


def main():

    # Suppress console output for logger
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(logging.WARNING)

    # Parse arguments
    parser = setup_arg_parser()
    args = parser.parse_args()

    # Validate input paths
    validate_paths(args.video, args.input_folder)
    input_files = []
    if args.input_folder:
        input_files = find_files_recursive(args.input_folder)
    else:
        input_files += [args.video]
    logger.info(f"Number of video files: {len(input_files)}")
    logger.info(f"{input_files}")

    # Validate parameters
    try:
        validate_parameters(args.sim_thresh, args.fps, args.num_workers)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Run frame extractor
    logger.info(f"Starting frame extractor. Arguments: {args}")
    frame_extractor(input_files, similarity_threshold=args.sim_thresh, fps=args.fps)


if __name__ == "__main__":
    main()
