import shutil
import subprocess
import os

print("🔍 Checking FFmpeg availability...\n")

# 1️⃣ PATH se ffmpeg dhundho
ffmpeg_path = shutil.which("ffmpeg")

if ffmpeg_path:
    print(f"✅ FFmpeg found in PATH:")
    print(ffmpeg_path)
else:
    print("❌ FFmpeg NOT found in system PATH")

print("\n-----------------------------\n")

# 2️⃣ Common locations check karo
possible_paths = [
    "./ffmpeg",
    "/usr/bin/ffmpeg",
    "/usr/local/bin/ffmpeg"
]

for path in possible_paths:
    if os.path.isfile(path) and os.access(path, os.X_OK):
        print(f"✅ Executable FFmpeg found at: {path}")
    else:
        print(f"❌ Not found / not executable: {path}")

print("\n-----------------------------\n")

# 3️⃣ Version check (agar run ho sake)
try:
    result = subprocess.run(
        ["ffmpeg", "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print("🎥 FFmpeg Version Info:\n")
    print(result.stdout.split("\n")[0])
except Exception as e:
    print("❌ FFmpeg execution failed:")
    print(e)
