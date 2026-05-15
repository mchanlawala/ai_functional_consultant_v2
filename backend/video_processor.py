"""video_processor.py — RecordDoc pipeline: ffmpeg + Whisper + LLaVA/Ollama/OpenAI."""
import base64, os, subprocess, warnings
import numpy as np
import cv2, requests
from dotenv import load_dotenv
load_dotenv()
warnings.filterwarnings("ignore")

# Configuration from environment
OLLAMA_BASE_URL    = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
TEXT_MODEL         = os.environ.get("TEXT_MODEL", "llama3.2:latest")
VISION_MODEL       = os.environ.get("VISION_MODEL", "llava:latest")
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
LLM_PROVIDER       = os.environ.get("LLM_PROVIDER", "ollama").lower()
OPENAI_API_KEY     = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL       = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

FRAMES_DIR = os.path.join(os.path.dirname(__file__), "data", "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)

def get_ffmpeg_exe():
    import shutil
    for n in ("ffmpeg", "ffmpeg.exe"):
        f = shutil.which(n)
        if f:
            return f
    try:
        import imageio_ffmpeg as ioff
        return ioff.get_ffmpeg_exe()
    except Exception:
        pass
    raise RuntimeError("ffmpeg not found. Install: sudo apt install ffmpeg")

def extract_audio(video_path, progress_cb=None):
    if progress_cb:
        progress_cb(10, "Extracting audio...")
    audio = video_path.rsplit(".", 1)[0] + ".wav"
    cmd = [get_ffmpeg_exe(), "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
           "-ar", "16000", "-ac", "1", "-loglevel", "error", audio]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg: {proc.stderr.decode(errors='replace')}")
    if not os.path.exists(audio) or os.path.getsize(audio) == 0:
        raise RuntimeError("No audio extracted")
    return audio

def transcribe_audio(audio_path, progress_cb=None):
    if progress_cb:
        progress_cb(25, f"Transcribing ({WHISPER_MODEL_SIZE})...")
    import whisper
    model = whisper.load_model(WHISPER_MODEL_SIZE)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = model.transcribe(audio_path, verbose=False, fp16=False)
    return r["text"].strip()

def extract_key_frames(video_path, progress_cb=None, interval_sec=3, max_frames=40):
    if progress_cb:
        progress_cb(40, "Extracting frames...")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    totf = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur = totf / fps
    if dur / interval_sec > max_frames:
        interval_sec = max(1, int(dur / max_frames))
    fi, thresh, fc, saved, prev, paths = int(fps * interval_sec), 35.0, 0, 0, None, []
    TARGET_W = 1280
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        if w > TARGET_W:
            frame = cv2.resize(frame, (TARGET_W, int(h * TARGET_W / w)))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        save = (fc % fi == 0)
        if not save and prev is not None and gray.shape == prev.shape:
            if np.mean(cv2.absdiff(gray, prev)) > thresh:
                save = True
        if save:
            ts = f"{int((fc / fps) // 60):02d}:{int((fc / fps) % 60):02d}"
            fn = f"frame_{saved:04d}_{ts.replace(':', '-')}.jpg"
            fp = os.path.join(FRAMES_DIR, fn)
            cv2.imwrite(fp, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            paths.append((ts, fp))
            saved += 1
        prev = gray
        fc += 1
    cap.release()
    return paths

def describe_frame(image_path, timestamp):
    """Describe frame using either Ollama vision or OpenAI vision."""
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        prompt = ("Analyze this frame from a customer interview screen recording.\n"
                  "Describe: which application is open, visible content (text/data/diagrams), "
                  "what is being discussed/shown. Be specific. 2-4 sentences.")
        # Use OpenAI if provider is openai and vision model is not a local Ollama model
        if LLM_PROVIDER == "openai" and not VISION_MODEL.startswith("llama") and not VISION_MODEL.startswith("qwen"):
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing screen recordings."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}
                ],
                max_tokens=300,
                temperature=0.1
            )
            description = response.choices[0].message.content.strip()
            return f"[{timestamp}] {description}"
        else:
            # Fallback to Ollama vision (llava, etc.)
            r = requests.post(f"{OLLAMA_BASE_URL}/api/generate",
                              json={"model": VISION_MODEL, "prompt": prompt, "images": [b64], "stream": False,
                                    "options": {"temperature": 0.1, "num_predict": 300}}, timeout=120)
            if r.status_code == 200:
                return f"[{timestamp}] {r.json().get('response', '').strip()}"
    except Exception as e:
        print(f"Frame analysis error: {e}")
    return f"[{timestamp}] (frame analysis unavailable)"

def analyze_frames(frame_paths, progress_cb=None, use_vision=True):
    descs, total = [], len(frame_paths)
    for i, (ts, fp) in enumerate(frame_paths):
        if progress_cb:
            pct = 45 + int((i / max(total, 1)) * 20)
            progress_cb(pct, f"Screen analysis ({i+1}/{total})...")
        descs.append(describe_frame(fp, ts) if use_vision else f"[{ts}] Frame {i+1}/{total}")
        try:
            os.remove(fp)
        except Exception:
            pass
    return descs

def generate_text(prompt, system="", max_tokens=8192):
    """Generate text using either OpenAI or Ollama based on LLM_PROVIDER."""
    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=OPENAI_MODEL,
            temperature=0.2,
            max_tokens=max_tokens,
            api_key=OPENAI_API_KEY
        )
        messages = []
        if system:
            messages.append(("system", system))
        messages.append(("human", prompt))
        try:
            response = llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"OpenAI error: {e}")
            return f"Error: OpenAI failed - {e}"
    else:
        # Ollama path
        payload = {
            "model": TEXT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": max_tokens}
        }
        if system:
            payload["system"] = system
        try:
            r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=600)
            if r.status_code == 200:
                return r.json().get("response", "").strip()
            return f"Error: Ollama {r.status_code}"
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama. Run: ollama serve"
        except Exception as e:
            return f"Error: {e}"

def check_ollama():
    try:
        return requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5).status_code == 200
    except Exception:
        return False

def get_ollama_models():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []

def process_video(video_path, progress_cb=None, use_vision=True):
    audio = extract_audio(video_path, progress_cb)
    transcript = transcribe_audio(audio, progress_cb)
    try:
        os.remove(audio)
    except Exception:
        pass
    frames = extract_key_frames(video_path, progress_cb)
    descs = analyze_frames(frames, progress_cb, use_vision)
    return {"transcript": transcript, "screen_descriptions": descs, "frame_count": len(descs)}