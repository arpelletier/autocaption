import sys
import os
import imageio
from moviepy.editor import VideoFileClip

def trim_video(input_path, output_path, end_time):
    # Load the video file
    video = VideoFileClip(input_path)
    
    # Trim the video
    trimmed_video = video.subclip(0, end_time)
    
    # Write the trimmed video to the output file
    trimmed_video.write_videofile(output_path, codec='libx264', audio_codec='aac')

### Parse arguments ###
if len(sys.argv) < 2:
	print("Incorrect usage.")
	print("python prepare_test_video.py video.mp4")
	sys.exit(0)


# Usage
input_video_path = sys.argv[1] # Path to the input video
output_video_path = 'trimmed_video.mp4'  # Path for the trimmed output video

# Extract the first 5 minutes (300 seconds)
trim_video(input_video_path, output_video_path, end_time=300)

