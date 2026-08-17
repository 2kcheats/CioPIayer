from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
import yt_dlp
import uuid
import os

app = FastAPI()

# Create download directory
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"status": "online", "message": "YouTube MP3 Proxy is running!"}

@app.get("/download")
def download_audio(url: str = Query(..., description="YouTube video URL")):
    """
    Download audio from a YouTube URL and return the MP3 file.
    Example: /download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
    """
    try:
        # Generate a unique filename
        file_id = str(uuid.uuid4())
        output_path = os.path.join(DOWNLOAD_DIR, file_id)

        # Configure yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the generated MP3 file
        mp3_file = None
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(file_id) and f.endswith('.mp3'):
                mp3_file = os.path.join(DOWNLOAD_DIR, f)
                break

        if not mp3_file:
            return JSONResponse(
                status_code=404,
                content={"error": "Could not find downloaded file"}
            )

        # Return the file
        return FileResponse(
            mp3_file,
            media_type='audio/mpeg',
            filename=os.path.basename(mp3_file),
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
def health_check():
    return {"status": "healthy"}
