import subprocess

def test_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"FFmpeg is installed. Version info: {result.stdout.splitlines()[0]}")
        else:
            print("FFmpeg failed to run.")
    except FileNotFoundError:
        print("FFmpeg not found in PATH.")

if __name__ == "__main__":
    test_ffmpeg()
