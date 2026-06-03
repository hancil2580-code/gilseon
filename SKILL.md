# /watch — Claude watches a video

Analyze video content by downloading, extracting frames, and obtaining transcripts.

## Usage

```
/watch <video-url-or-path> [options]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--max-frames` | 80 | Cap on frame count (hard max 100) |
| `--resolution` | 512 | Frame width in pixels |
| `--fps` | auto | Override automatic frame rate |
| `--start` | — | Range start (SS, MM:SS, or HH:MM:SS) |
| `--end` | — | Range end |
| `--whisper` | auto | Force `groq` or `openai` backend |
| `--no-whisper` | — | Disable Whisper fallback |
| `--out-dir` | tmp | Custom working directory |

### Examples

```bash
# Analyze a YouTube video
python3 scripts/watch.py https://youtube.com/watch?v=...

# Focus on a specific segment
python3 scripts/watch.py https://youtube.com/watch?v=... --start 1:30 --end 3:00

# Local file, higher resolution
python3 scripts/watch.py ./recording.mp4 --resolution 1024
```

## Setup

```bash
python3 scripts/setup.py
```

Checks for `ffmpeg`, `ffprobe`, `yt-dlp` and scaffolds `~/.config/watch/.env` for API keys.

## Requirements

- Python 3.9+
- `ffmpeg` and `ffprobe`
- `yt-dlp`
- `GROQ_API_KEY` or `OPENAI_API_KEY` (for videos without native captions)

## How it works

1. **Download** — `yt-dlp` fetches the video and any available captions
2. **Extract frames** — `ffmpeg` samples frames at an auto-scaled rate based on video duration
3. **Transcribe** — Uses native captions if available, otherwise Whisper API
4. **Report** — Outputs a markdown report with frame paths and timestamped transcript
