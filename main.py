from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import yt_dlp
import uuid
import os
import subprocess
import tempfile
import shutil

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
        output_path = os.path.join(temp_dir, file_id)

        # Use yt-dlp with explicit configuration to avoid the _http_error issue
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
            'extract_audio': True,
            'audioformat': 'mp3',
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_ffmpeg': True,
        }

        # Try using yt-dlp
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            # If yt-dlp fails, try using subprocess to call yt-dlp directly
            print(f"yt-dlp library failed: {e}, trying subprocess...")
            subprocess.run([
                'yt-dlp',
                '-f', 'bestaudio/best',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '192K',
                '--output', output_path,
                url
            ], check=True)

        # Find the generated MP3 file
        mp3_file = None
        for f in os.listdir(temp_dir):
            if f.startswith(file_id) and f.endswith('.mp3'):
                mp3_file = os.path.join(temp_dir, f)
                break

        if not mp3_file:
            # Try to find any mp3 file in the temp directory
            for f in os.listdir(temp_dir):
                if f.endswith('.mp3'):
                    mp3_file = os.path.join(temp_dir, f)
                    break

        if not mp3_file:
            return JSONResponse(
                status_code=404,
                content={"error": "Could not find downloaded file"}
            )

        # Read the file and return it
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
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "download_dir": DOWNLOAD_DIR}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
