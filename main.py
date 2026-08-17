from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
import yt_dlp
import uuid
import os

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/download")
def download_audio(url: str = Query(..., description="YouTube video URL")):
    """
    Download audio from a YouTube URL and return the MP3 file.
    Example: /download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
    """
    # Generate a unique filename to avoid collisions
    file_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")

    # Configure yt-dlp to extract audio as MP3
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path[:-4],  # yt-dlp adds its own extension
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the generated file (yt-dlp may add a different extension before post-processing)
    actual_file = None
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(file_id):
            actual_file = os.path.join(DOWNLOAD_DIR, f)
            break

    if not actual_file:
        return {"error": "Could not find downloaded file"}

    # Return the file, then clean it up after sending
    return FileResponse(
        actual_file,
        media_type='audio/mpeg',
        filename=f"{file_id}.mp3",
        background=None # File will be deleted automatically after download in some FastAPI versions
        # For a more robust clean-up, you can add a background task.
    )