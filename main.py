from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import yt_dlp
import uuid
import os
import subprocess
import tempfile
import shutil
import glob

app = FastAPI()

# Create download directory
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "YouTube MP3 Proxy is running!",
        "endpoints": ["/download"]
    }

@app.get("/download")
async def download_audio(url: str = Query(..., description="YouTube video URL")):
    """
    Download audio from a YouTube URL and return the MP3 file.
    Example: /download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
    """
    try:
        # Create a temporary directory for this download
        temp_dir = tempfile.mkdtemp()
        file_id = str(uuid.uuid4())
        # yt-dlp will add its own extension, so we don't add .mp3 here
        output_path = os.path.join(temp_dir, file_id)

        # Configure yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': False,  # Set to False so we can see what's happening
            'no_warnings': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_ffmpeg': True,
        }

        # Download the audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # List all files in the temp directory to see what was created
        print(f"Files in temp_dir: {os.listdir(temp_dir)}")

        # Find the generated MP3 file (yt-dlp might add .mp3 or leave it as .webm)
        mp3_file = None
        for f in os.listdir(temp_dir):
            # Check for any file that starts with our file_id and ends with .mp3
            if f.startswith(file_id) and f.endswith('.mp3'):
                mp3_file = os.path.join(temp_dir, f)
                break
            # If no .mp3 found, check for .webm or .m4a (yt-dlp might not convert properly)
            if f.startswith(file_id) and (f.endswith('.webm') or f.endswith('.m4a')):
                mp3_file = os.path.join(temp_dir, f)
                break

        if not mp3_file:
            # Try to find any file in the temp directory
            files = os.listdir(temp_dir)
            if files:
                mp3_file = os.path.join(temp_dir, files[0])
                print(f"Using fallback file: {mp3_file}")

        if not mp3_file or not os.path.exists(mp3_file):
            return JSONResponse(
                status_code=404,
                content={"error": "Could not find downloaded file"}
            )

        # Read the file
        with open(mp3_file, 'rb') as f:
            file_data = f.read()

        # Clean up the temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        # Return the file
        return StreamingResponse(
            iter([file_data]),
            media_type='audio/mpeg',
            headers={
                'Content-Disposition': f'attachment; filename="{file_id}.mp3"',
                'Content-Length': str(len(file_data))
            }
        )

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
