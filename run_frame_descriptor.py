from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
import torch
from PIL import Image
import requests

import time
import argparse
import os
import sys
import logging

from src.util.utilities import find_files_recursive
from src.video_processing.frame_extractor import extract_frames_with_timestamps, create_pdf_from_frames
from src.logger import setup_logger

# Initialize logger
logger = setup_logger(log_file_name='./log/run_frame_descriptor_log.txt')


def load_model():
    processor = LlavaNextProcessor.from_pretrained("llava-hf/llava-v1.6-mistral-7b-hf")

    model = LlavaNextForConditionalGeneration.from_pretrained("llava-hf/llava-v1.6-mistral-7b-hf",
                                                torch_dtype=torch.float16, low_cpu_mem_usage=False)
    model.to("cuda:0")

    return processor, model


def inference(prompt, img, model, processor):

    inputs = processor(prompt, img, return_tensors="pt").to("cuda:0")
    output = model.generate(**inputs, max_new_tokens=1000)
    response = processor.decode(output[0], skip_special_tokens=True)

    return response

def generate_prompt(image_filename):
    prompt = "[INST] <image>\nPlease describe this image in detail. What text, if any, is in the image?[/INST]"
    return prompt


def extract_description(response):
    # Remove the instruction prompt
    resp = response.split("[/INST] ")[1]
    # Put into a single line response
    description = " ".join(resp.split("\n"))
    return description

def frame_descriptor(input_files, output_file='./descriptions.txt'):

    # Load multimodal LLM
    processor, model = load_model()

    # Open output file for writing
    with open(output_file, 'w') as outfile:

        # Loop through frame files
        count = 0
        for f in input_files:
            count += 1
            print(f"Processing file {f} ({count} out of {len(input_files)})")
            logger.info(f"Processing file {f} ({count} out of {len(input_files)})")

            start_time = time.time()

            # Prepare input data
            prompt = generate_prompt(f)
            image = Image.open(f)
            logger.info(f"Starting inference. Image: {f}, Prompt: {prompt}")

            # Call multimodal LLM
            response = inference(prompt, image, model, processor)
            description = extract_description(response)

            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f"Finished inference. Image: {f}, Time elapsed: {elapsed_time}")

            logger.info(f"Response: {response}")
            outfile.write(f+'\t'+description+"\n")
            outfile.flush()

        logger.info("Finished frame extraction.")


def validate_paths(video_folder_path):
    valid_folder = video_folder_path and os.path.isdir(video_folder_path)

    # At least one of video or caption file must be valid if specified
    if not valid_folder:
        print("Error: Please provide a valid path to an input folder.")
        print("Folder path valid:", valid_folder)
        sys.exit(1)


def setup_arg_parser():
    parser = argparse.ArgumentParser(description="Creates descriptions for the frame .jpg files.")

    parser.add_argument('-i',"--input_folder", type=str, default=".",
                        help="Path to the input folder containing frames files.")

    parser.add_argument('-o',"--output_file", type=str, default="./descriptions.txt",
                        help="Path to the output file where results will be stored.")
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
    validate_paths(args.input_folder)

    input_files = find_files_recursive(args.input_folder, '.jpg')
    logger.info(f"Number of frame files: {len(input_files)}")
    logger.info(f"{input_files}")

    # Run description batcher
    logger.info(f"Starting description batcher. Arguments: {args}")
    frame_descriptor(input_files, output_file=args.output_file)


if __name__ == "__main__":
    main()
