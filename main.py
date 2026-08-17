from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import yt_dlp
import uuid
import os
import subprocess
import tempfile
import shutil
import sys

app = FastAPI()

# Create download directory
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Check if ffmpeg is available
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "YouTube MP3 Proxy is running!",
        "endpoints": ["/download"],
        "ffmpeg_available": check_ffmpeg()
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
        output_path = os.path.join(temp_dir, file_id)

        # Check if ffmpeg is available
        has_ffmpeg = check_ffmpeg()
        
        if not has_ffmpeg:
            # Try to use the built-in audio extraction without ffmpeg
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'no_check_certificate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            # Try to find the downloaded file (might be webm or m4a)
            downloaded_file = None
            for f in os.listdir(temp_dir):
                if f.startswith(file_id):
                    downloaded_file = os.path.join(temp_dir, f)
                    break
                    
            if downloaded_file:
                # Return whatever was downloaded
                with open(downloaded_file, 'rb') as f:
                    file_data = f.read()
                shutil.rmtree(temp_dir, ignore_errors=True)
                return StreamingResponse(
                    iter([file_data]),
                    media_type='audio/mpeg',
                    headers={
                        'Content-Disposition': f'attachment; filename="{file_id}.mp3"',
                        'Content-Length': str(len(file_data))
                    }
                )
        else:
            # Full ffmpeg-powered download
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
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_ffmpeg': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the generated MP3 file
            mp3_file = None
            for f in os.listdir(temp_dir):
                if f.startswith(file_id) and f.endswith('.mp3'):
                    mp3_file = os.path.join(temp_dir, f)
                    break

            if mp3_file:
                with open(mp3_file, 'rb') as f:
                    file_data = f.read()
                shutil.rmtree(temp_dir, ignore_errors=True)
                return StreamingResponse(
                    iter([file_data]),
                    media_type='audio/mpeg',
                    headers={
                        'Content-Disposition': f'attachment; filename="{file_id}.mp3"',
                        'Content-Length': str(len(file_data))
                    }
                )

        # If we get here, no file was found
        return JSONResponse(
            status_code=404,
            content={"error": "Could not find downloaded file"}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ffmpeg_available": check_ffmpeg()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
