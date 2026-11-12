import cv2
import pytesseract
from PIL import Image
import os

# Set the path to the Tesseract executable (if not in PATH)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_frames(video_path, output_folder, frame_interval=10):
    """
    Extract frames from a video and save them to a folder.
    
    :param video_path: Path to the video file.
    :param output_folder: Folder to save the extracted frames.
    :param frame_interval: Extract every nth frame (default is 1, meaning every frame).
    """
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    frame_count = 0
    saved_frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Save every nth frame
        if frame_count % frame_interval == 0:
            frame_path = os.path.join(output_folder, f"frame_{saved_frame_count:04d}.jpg")
            cv2.imwrite(frame_path, frame)
            saved_frame_count += 1

        frame_count += 1

    cap.release()
    print(f"Extracted {saved_frame_count} frames to {output_folder}")

def extract_text_from_frames(frames_folder, output_text_file):
    """
    Extract text from all frames in a folder using OCR.
    
    :param frames_folder: Folder containing the frames.
    :param output_text_file: File to save the extracted text.
    """
    # Open the output text file
    with open(output_text_file, "w", encoding="utf-8") as text_file:
        # Iterate through all frames in the folder
        for frame_name in sorted(os.listdir(frames_folder)):
            frame_path = os.path.join(frames_folder, frame_name)

            # Load the frame as an image
            image = Image.open(frame_path)

            # Perform OCR on the image
            text = pytesseract.image_to_string(image)

            # Write the extracted text to the output file
            text_file.write(f"Text from {frame_name}:\n")
            text_file.write(text + "\n")
            text_file.write("-" * 40 + "\n")

    print(f"Extracted text saved to {output_text_file}")

if __name__ == "__main__":
    # Path to the video file
    video_path = "E:/Youtube_text_extract/youtube_data_extract/Item Analysis ｜ Difficulty Index ｜Discrimination Power ｜ Effectiveness of distractor by Zeshan Umar.webm"

    # Folder to save extracted frames
    frames_folder = "extracted_frames"

    # File to save extracted text
    output_text_file = "extracted_minimum.txt"

    # Extract frames from the video
    extract_frames(video_path, frames_folder, frame_interval=30)  # Extract every 30th frame

    # Extract text from the frames
    extract_text_from_frames(frames_folder, output_text_file)