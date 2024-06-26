import argparse
import os
import sys
import logging

from src.util.utilities import read_vtt, write_vtt, parse_timestamps_to_frames, match_text_to_frames, find_files
from src.video_processing.frame_extractor import extract_frames_with_timestamps
from src.video_processing.video_to_text import extract_image_text, extract_image_description
from src.logger import setup_logger

# Initialize logger
logger = setup_logger('./log/autocaption_log.txt')

def correct_captions(timestamp_to_text, timestamp_to_frames=None, frame_to_transcript=None,
                     frame_to_onscreen_text=None, frame_to_description=None):
    ''' This function uses the information available to autocorrect the .vtt caption file '''
    #TODO complete implementation
    print("Implementation incomplete.")
    return timestamp_to_text


def auto_caption(input_files, output_folder='.', similarity_threshold = 0.95, fps=1.0, num_workers=5):

    # Read auto generated caption
    timestamp_to_text = read_vtt(input_files['caption'])
    logger.info(f"Extracted {len(timestamp_to_text)} lines from {input_files['caption']}")

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

    # Suppress console output for logger
    for handler in logger.handlers:
        if 'StreamHandler' in str(type(handler)):
            handler.setLevel(logging.WARNING)

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

    # Run autocaption
    logger.info(f"Starting autocaption. Arguments: {args}")
    auto_caption(input_files, similarity_threshold=args.sim_thresh, fps=args.fps, output_folder=args.output_folder)


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