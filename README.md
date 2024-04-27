# AutoVC
Automatic Video Caption (AutoVC) is a pipeline which automatically creates context-aware video captions based on the content of a video file. Generally applicable to any video files, this software is currently in development with a focus on e-Learning content generation. This software 1) extracts key frames from a video file and extracts unique video frames essentially extracting the lecture slides from the presenter; 2) uses a vision-language foundation model (LLaVA) to describe the key frames and extract the on-screen text; 3) [in progress] leverages a language foundation model (LLaMA 3) to correct an existing .vtt caption file based on the extracted descriptions and on-screen text.

### Input:
* A video file in .mp4 format.
* An automatically generated video caption file (.vtt) from Vimeo.com.

### Output:
* A folder of video stills representing the key frames as .jpg files.
* A combined .pdf file of the resulting frames.
* An automatically corrected .vtt file to be uploaded to Vimeo.com.
* A full transcript of the video based on the resulting captions, as a .txt file.

### Usage:
Docker hub: https://hub.docker.com/r/arpelletier/autocaption
Instructions will be added soon.
