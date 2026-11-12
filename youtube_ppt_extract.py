#!/usr/bin/env python3
"""
Extract unique slide text from a YouTube video (or a local video file).

Usage:
    python youtube_ppt_extract.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python youtube_ppt_extract.py            # will prompt for the URL
    python youtube_ppt_extract.py URL --interval 3 --text-similarity 0.9
    python youtube_ppt_extract.py --video my_lecture.mp4

Requirements:
    pip install yt-dlp opencv-python pytesseract numpy
    + install the Tesseract OCR engine (see notes below)
"""

import argparse
import difflib
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import pytesseract
import yt_dlp


# --------------------------------------------------------------------------
# Setup helpers
# --------------------------------------------------------------------------
def configure_tesseract(custom_path=None):
    """Locate the Tesseract executable on Windows / macOS / Linux."""
    if custom_path:
        pytesseract.pytesseract.tesseract_cmd = custom_path
        return
    if shutil.which("tesseract"):
        return  # already on PATH

    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
        "/usr/bin/tesseract",
    ]
    for p in common_paths:
        if Path(p).exists():
            pytesseract.pytesseract.tesseract_cmd = p
            return

    sys.exit(
        "Tesseract OCR not found. Install it and add it to PATH, or pass "
        "--tesseract-cmd /path/to/tesseract"
    )


def download_video(url, out_dir):
    """Download the video track only (audio isn't needed for OCR)."""
    options = {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),  # video id avoids weird filenames
        "format": "bestvideo[height<=1080]/best[height<=1080]/best",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = info["requested_downloads"][0]["filepath"]
    return Path(filepath), info["id"], info.get("title", info["id"])


# --------------------------------------------------------------------------
# Duplicate detection
# --------------------------------------------------------------------------
def make_thumbnail(frame):
    """Small grayscale version of a frame for fast comparison."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (256, 144), interpolation=cv2.INTER_AREA).astype(np.float32)


def is_duplicate_image(thumb, kept_thumbs, threshold):
    """True if thumb is almost pixel-identical to an already kept frame."""
    return any(np.mean(np.abs(thumb - t)) < threshold for t in kept_thumbs)


def normalize_text(text):
    """Lowercase, strip punctuation/extra whitespace so OCR noise matters less."""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def is_duplicate_text(norm_text, kept_texts, similarity):
    """True if text is >= `similarity` similar to any already kept slide."""
    for existing in kept_texts:
        if difflib.SequenceMatcher(None, norm_text, existing).ratio() >= similarity:
            return True
    return False


# --------------------------------------------------------------------------
# Main extraction
# --------------------------------------------------------------------------
def format_time(seconds):
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def extract_unique_slides(video_path, work_dir, interval, img_threshold,
                          text_similarity, min_chars, lang, keep_frames):
    frames_dir = work_dir / "frames"
    if keep_frames:
        frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        sys.exit(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(interval * fps)))

    kept_thumbs, kept_texts, results = [], [], []
    frame_idx, sampled, skipped_img, skipped_text = 0, 0, 0, 0

    while True:
        # grab() is much faster than read() for frames we don't need
        if not cap.grab():
            break
        if frame_idx % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            sampled += 1
            timestamp = frame_idx / fps

            thumb = make_thumbnail(frame)
            if is_duplicate_image(thumb, kept_thumbs, img_threshold):
                skipped_img += 1
            else:
                text = pytesseract.image_to_string(frame, lang=lang).strip()
                norm = normalize_text(text)

                if len(norm) < min_chars:
                    pass  # blank / no-text frame (title fade, speaker view, etc.)
                elif is_duplicate_text(norm, kept_texts, text_similarity):
                    skipped_text += 1
                else:
                    kept_thumbs.append(thumb)
                    kept_texts.append(norm)
                    name = f"slide_{len(results) + 1:04d}.jpg"
                    if keep_frames:
                        cv2.imwrite(str(frames_dir / name), frame)
                    results.append((name, timestamp, text))
                    print(f"  [+] {format_time(timestamp)} -> {name}")

            if total_frames > 0 and sampled % 20 == 0:
                print(f"  ... {frame_idx / total_frames:.0%} processed")
        frame_idx += 1

    cap.release()
    print(f"\nSampled {sampled} frames | unique slides: {len(results)} | "
          f"duplicates skipped: {skipped_img + skipped_text} "
          f"(image: {skipped_img}, text: {skipped_text})")
    return results


def save_text(results, output_file, title):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Video: {title}\nUnique slides: {len(results)}\n")
        f.write("=" * 60 + "\n\n")
        for name, ts, text in results:
            f.write(f"[{format_time(ts)}] {name}\n{text}\n")
            f.write("-" * 40 + "\n")
    print(f"Extracted text saved to: {output_file}")


def parse_args():
    p = argparse.ArgumentParser(description="Extract unique slide text from a YouTube video.")
    p.add_argument("url", nargs="?", help="YouTube URL (prompted if omitted)")
    p.add_argument("--video", help="Use a local video file instead of downloading")
    p.add_argument("-o", "--output-dir", default="output", help="Base output folder (default: output)")
    p.add_argument("--interval", type=float, default=5, help="Seconds between sampled frames (default: 5)")
    p.add_argument("--image-threshold", type=float, default=1.0,
                   help="Mean pixel difference below which frames count as identical (default: 1.0)")
    p.add_argument("--text-similarity", type=float, default=0.92,
                   help="0-1 text similarity at which a slide is a duplicate (default: 0.92)")
    p.add_argument("--min-chars", type=int, default=10,
                   help="Ignore frames with less OCR text than this (default: 10)")
    p.add_argument("--lang", default="eng", help="Tesseract language code (default: eng)")
    p.add_argument("--tesseract-cmd", help="Full path to the tesseract executable")
    p.add_argument("--no-frames", action="store_true", help="Don't save slide images, only text")
    return p.parse_args()


def main():
    args = parse_args()
    configure_tesseract(args.tesseract_cmd)

    base_dir = Path(args.output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    if args.video:
        video_path = Path(args.video)
        video_id, title = video_path.stem, video_path.stem
    else:
        url = args.url or input("Enter YouTube video URL: ").strip()
        if not url:
            sys.exit("No URL provided.")
        print("Downloading video...")
        video_path, video_id, title = download_video(url, base_dir)

    work_dir = base_dir / re.sub(r"[^\w\-]", "_", video_id)
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nProcessing: {title}")
    results = extract_unique_slides(
        video_path, work_dir, args.interval, args.image_threshold,
        args.text_similarity, args.min_chars, args.lang, not args.no_frames,
    )
    save_text(results, work_dir / "extracted_text.txt", title)


if __name__ == "__main__":
    main()
