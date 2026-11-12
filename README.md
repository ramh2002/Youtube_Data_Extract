# YouTube Slide Text Extractor

Extract the text from slides (PPTs) shown in a YouTube lecture or any local video file. The script downloads the video, samples frames, runs OCR, and **removes duplicate slides** so you get one clean, timestamped text file with only unique slides.

## Features

- Works with any YouTube URL, or a local video file
- Duplicate removal in two layers:
  - **Image check:** skips frames nearly identical to one already kept (saves OCR time)
  - **Text check:** skips slides whose OCR text is highly similar to any earlier slide, so revisited slides are caught too
- Timestamped output, so you can jump back to the exact moment in the video
- Saves only unique slide images (optional)
- Cross-platform (Windows, macOS, Linux)
- Configurable via command-line options

## Requirements

- Python 3.8+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (a separate install, see below)
- Python packages: `yt-dlp`, `opencv-python`, `pytesseract`, `numpy`

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```

2. **(Recommended) Create a virtual environment**

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Or manually:

   ```bash
   pip install yt-dlp opencv-python pytesseract numpy
   ```

4. **Install the Tesseract OCR engine**

   | OS      | Command / Link                                                                 |
   |---------|--------------------------------------------------------------------------------|
   | Windows | Download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) |
   | macOS   | `brew install tesseract`                                                       |
   | Linux   | `sudo apt install tesseract-ocr`                                               |

   The script finds Tesseract automatically. If it doesn't, pass `--tesseract-cmd`.

## Usage

```bash
# Pass a URL
python youtube_ppt_extract.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Or run without arguments and you will be prompted for the URL
python youtube_ppt_extract.py

# Use a local video file
python youtube_ppt_extract.py --video lecture.mp4

# Custom sampling interval and duplicate sensitivity
python youtube_ppt_extract.py "URL" --interval 3 --text-similarity 0.9
```

## Options

| Option                    | Default  | Description                                                        |
|---------------------------|----------|--------------------------------------------------------------------|
| `url`                     | prompt   | YouTube video URL                                                  |
| `--video FILE`            | -        | Use a local video file instead of downloading                      |
| `-o`, `--output-dir`      | `output` | Base output folder                                                 |
| `--interval`              | `5`      | Seconds between sampled frames                                     |
| `--image-threshold`       | `1.0`    | Mean pixel difference below which frames count as identical        |
| `--text-similarity`       | `0.92`   | Text similarity (0-1) at or above which a slide is a duplicate     |
| `--min-chars`             | `10`     | Ignore frames with less OCR text than this                         |
| `--lang`                  | `eng`    | Tesseract language code (e.g. `hin`, `fra`, `deu`)                 |
| `--tesseract-cmd`         | auto     | Full path to the Tesseract executable                              |
| `--cookies-from-browser`  | -        | Browser to read YouTube cookies from (`chrome`, `firefox`, `edge`) |
| `--no-frames`             | off      | Save only text, not slide images                                   |

## Output

```
output/
└── <video_id>/
    ├── extracted_text.txt   # timestamped text of unique slides
    └── frames/
        ├── slide_0001.jpg
        ├── slide_0002.jpg
        └── ...
```

Example `extracted_text.txt`:

```
Video: Item Analysis | Difficulty Index
Unique slides: 12
============================================================

[00:00:05] slide_0001.jpg
Item Analysis
...
----------------------------------------
```

## Tuning

| Problem                                              | Fix                                                                 |
|------------------------------------------------------|---------------------------------------------------------------------|
| Near-duplicates kept (e.g. bullets appear one by one)| Lower `--text-similarity` to about `0.85`                           |
| Distinct slides wrongly dropped                      | Raise `--text-similarity` to about `0.97` and use a smaller `--interval` |
| Slides missed in fast-changing videos                | Use a smaller `--interval` (e.g. `2`)                               |
| Small or blurry text misread                         | Make sure the source is 720p or higher; OCR works best on clear slides |
| Non-English slides                                   | Install the Tesseract language pack and pass `--lang`               |

## Troubleshooting

### `ERROR: The page needs to be reloaded` (or other YouTube download errors)

YouTube changes often, and old `yt-dlp` versions break. Try these in order:

1. **Update yt-dlp**
   ```bash
   pip install -U yt-dlp
   ```
2. **Install a JavaScript runtime (Deno)**, which recent yt-dlp versions need for YouTube
   - Windows: `winget install DenoLand.Deno`
   - Then open a new terminal and check with `deno --version`
3. **Use your browser cookies**
   ```bash
   python youtube_slide_extract.py "URL" --cookies-from-browser chrome
   ```
4. **Download manually, then use local mode**
   ```bash
   yt-dlp -f "bestvideo[height<=1080]" -o "lecture.%(ext)s" "URL"
   python youtube_ppt_extract.py --video lecture.webm
   ```

### `Tesseract OCR not found`

Install Tesseract (see [Installation](#installation)) and add it to your PATH, or pass the path explicitly:

```bash
python youtube_ppt_extract.py "URL" --tesseract-cmd "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## How it works

1. Downloads the video track with `yt-dlp` (audio isn't needed)
2. Samples one frame every `--interval` seconds
3. Compares each frame's thumbnail with kept slides and skips near-identical ones
4. Runs OCR on the remaining frames
5. Compares the normalized text against all kept slides and drops duplicates
6. Saves unique slides and a timestamped text file

## Disclaimer

This tool is for personal and educational use. Respect copyright and YouTube's Terms of Service, and only process videos you have the right to download and use.

## License

MIT License. See [LICENSE](LICENSE) for details.
