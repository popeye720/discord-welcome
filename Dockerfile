# ================= STAGE 1: STATIC FFMPEG =================
FROM mwader/static-ffmpeg:6.0 AS ffmpeg

# ================= STAGE 2: PYTHON APP ====================
FROM python:3.11-slim

# ---- Copy static ffmpeg & ffprobe ----
COPY --from=ffmpeg /ffmpeg /usr/bin/ffmpeg
COPY --from=ffmpeg /ffprobe /usr/bin/ffprobe

RUN chmod +x /usr/bin/ffmpeg /usr/bin/ffprobe

# ---- Required voice libs for Discord ----
RUN apt-get update && apt-get install -y \
    libopus0 \
    libsodium23 \
    && rm -rf /var/lib/apt/lists/*

# ---- App setup ----
WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "main.py"]