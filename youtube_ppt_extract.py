from pytube import YouTube
import cv2
import pytesseract
import os

# Path to Tesseract OCR (Update this based on your system)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def download_youtube_video(url, save_path="video.mp4"):
    """Download YouTube video using pytube."""
    yt = YouTube(url)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
    print(f"Downloading: {yt.title}")
    stream.download(filename=save_path)
    print(f"Video downloaded: {save_path}")
    return save_path


def extract_frames(video_path, output_folder="frames", interval=5):
    """Extract frames from video at a given interval (in seconds)."""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_interval = interval * fps
    count = 0
    saved_frames = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if count % frame_interval == 0:
            frame_path = os.path.join(output_folder, f"frame_{saved_frames}.png")
            cv2.imwrite(frame_path, frame)
            saved_frames += 1
        count += 1

    cap.release()
    print(f"Extracted {saved_frames} frames to {output_folder}")
    return output_folder


def extract_text_from_frames(frames_folder, output_file="extracted_text.txt"):
    """Extract text from frames using OCR."""
    text_data = []
    for frame_file in sorted(os.listdir(frames_folder)):
        frame_path = os.path.join(frames_folder, frame_file)
        text = pytesseract.image_to_string(frame_path)
        text_data.append(f"Text from {frame_file}:\n{text}\n")

    with open(output_file, "w") as file:
        file.writelines(text_data)

    print(f"Extracted text saved to {output_file}")


# Main Workflow
youtube_url = "https://www.youtube.com/watch?v=1rtSLz20yVw"
video_file = "Learning_teaching.mp4"
frames_folder = "extracted_frames"
text_output_file = "Item_Analysis.txt"

# Step 1: Download YouTube Video
video_path = download_youtube_video(youtube_url, save_path=video_file)

import yt_dlp

def download_video_audio_separately(url):
    options = {
        'outtmpl': '%(title)s.%(ext)s',
        'format': 'bestvideo/best',  # Downloads only the best video
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])
    print("Downloaded video and audio separately.")

#youtube_url = "https://youtu.be/nWRz3gdnNL8?si=UCO7-RQ0DlTpvV0G"
#download_video_audio_separately(youtube_url)


#video_path="E:/Youtube_text_extract/youtube_data_extract/Item Analysis ｜ Difficulty Index ｜Discrimination Power ｜ Effectiveness of distractor by Zeshan Umar.mp4"
# Step 2: Extract Frames
#frames_folder = extract_frames(video_path, output_folder=frames_folder)

import pytesseract

# Set Tesseract OCR executable path
#pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# Step 3: Extract Text from Frames
#extract_text_from_frames(frames_folder, output_file=text_output_file)
