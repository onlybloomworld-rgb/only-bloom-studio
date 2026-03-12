"""
Only Bloom Studio — Web Interface
==================================
Reemplaza el bot de Telegram con una interfaz web directa.
Genera imágenes con el LoRA de Lolla via FAL.ai.
Deploy en Railway junto con el bot existente o como servicio separado.
"""
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
import fal_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

FAL_KEY = os.getenv("FAL_KEY")
LOLLA_LORA_URL = os.getenv("LOLLA_LORA_URL", "")
os.environ["FAL_KEY"] = FAL_KEY or ""

# ─── HTML TEMPLATE ────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Only Bloom Studio</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Montserrat:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --cream: #faf7f4;
    --warm: #f0ebe4;
    --blush: #e8d5c4;
    --rose: #c9907a;
    --deep: #2a1f1a;
    --muted: #8a7060;
    --border: rgba(42,31,26,0.12);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: var(--cream);
    color: var(--deep);
    font-family: 'Montserrat', sans-serif;
    font-weight: 300;
    min-height: 100vh;
  }
  header {
    padding: 2rem 3rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--cream);
  }
  .logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.8rem;
    font-weight: 300;
    letter-spacing: 0.15em;
    color: var(--deep);
  }
  .logo span { color: var(--rose); font-style: italic; }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #5cb85c; display: inline-block;
    margin-right: 0.5rem;
    animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  .status-text { font-size: 0.75rem; color: var(--muted); letter-spacing: 0.05em; }

  .main { display: grid; grid-template-columns: 1fr 1fr; min-height: calc(100vh - 73px); }

  /* LEFT PANEL */
  .panel-left {
    padding: 2.5rem 3rem;
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }
  .section-title {
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
  }
  textarea {
    width: 100%;
    background: var(--warm);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem;
    font-family: 'Montserrat', sans-serif;
    font-size: 0.85rem;
    font-weight: 300;
    color: var(--deep);
    resize: vertical;
    min-height: 100px;
    transition: border-color 0.2s;
    outline: none;
  }
  textarea:focus { border-color: var(--rose); }
  textarea::placeholder { color: var(--muted); }

  .controls { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  select {
    width: 100%;
    background: var(--warm);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    font-family: 'Montserrat', sans-serif;
    font-size: 0.8rem;
    font-weight: 300;
    color: var(--deep);
    cursor: pointer;
    outline: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%238a7060'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 1rem center;
  }
  select:focus { border-color: var(--rose); }

  .quick-prompts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .chip {
    padding: 0.35rem 0.75rem;
    background: var(--warm);
    border: 1px solid var(--border);
    border-radius: 20px;
    font-size: 0.72rem;
    cursor: pointer;
    transition: all 0.15s;
    color: var(--muted);
  }
  .chip:hover { background: var(--blush); border-color: var(--rose); color: var(--deep); }

  .generate-btn {
    width: 100%;
    padding: 1rem;
    background: var(--deep);
    color: var(--cream);
    border: none;
    border-radius: 4px;
    font-family: 'Montserrat', sans-serif;
    font-size: 0.8rem;
    font-weight: 400;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: auto;
  }
  .generate-btn:hover { background: var(--rose); }
  .generate-btn:disabled { background: var(--blush); cursor: not-allowed; }
  .generate-btn.loading {
    background: var(--muted);
    animation: shimmer 1.5s infinite;
  }
  @keyframes shimmer { 0%,100%{opacity:1} 50%{opacity:0.7} }

  /* RIGHT PANEL */
  .panel-right { padding: 2.5rem 3rem; display: flex; flex-direction: column; gap: 1.5rem; }

  .image-area {
    flex: 1;
    background: var(--warm);
    border: 1px solid var(--border);
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    position: relative;
    overflow: hidden;
  }
  .image-area img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    border-radius: 4px;
  }
  .placeholder-text {
    text-align: center;
    color: var(--muted);
  }
  .placeholder-text .icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    opacity: 0.4;
  }
  .placeholder-text p { font-size: 0.8rem; letter-spacing: 0.05em; }

  .loading-overlay {
    position: absolute;
    inset: 0;
    background: rgba(250,247,244,0.9);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    display: none;
  }
  .spinner {
    width: 40px; height: 40px;
    border: 2px solid var(--blush);
    border-top-color: var(--rose);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-msg { font-size: 0.78rem; color: var(--muted); letter-spacing: 0.05em; }

  .image-actions {
    display: flex;
    gap: 0.75rem;
  }
  .action-btn {
    flex: 1;
    padding: 0.65rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: transparent;
    font-family: 'Montserrat', sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
    color: var(--muted);
    transition: all 0.15s;
  }
  .action-btn:hover { border-color: var(--rose); color: var(--deep); }
  .action-btn.primary { background: var(--deep); color: var(--cream); border-color: var(--deep); }
  .action-btn.primary:hover { background: var(--rose); border-color: var(--rose); }

  /* HISTORY */
  .history-strip {
    display: flex;
    gap: 0.5rem;
    overflow-x: auto;
    padding-bottom: 0.25rem;
  }
  .history-strip::-webkit-scrollbar { height: 3px; }
  .history-strip::-webkit-scrollbar-track { background: var(--warm); }
  .history-strip::-webkit-scrollbar-thumb { background: var(--blush); }
  .thumb {
    width: 60px; height: 60px;
    border-radius: 3px;
    object-fit: cover;
    cursor: pointer;
    opacity: 0.7;
    transition: opacity 0.15s;
    border: 1px solid var(--border);
    flex-shrink: 0;
  }
  .thumb:hover, .thumb.active { opacity: 1; border-color: var(--rose); }

  .error-msg {
    background: #fdf0ed;
    border: 1px solid #e8b4a0;
    border-radius: 4px;
    padding: 0.75rem 1rem;
    font-size: 0.78rem;
    color: #8b3a2a;
    display: none;
  }

  /* MOBILE */
  @media (max-width: 768px) {
    .main { grid-template-columns: 1fr; }
    .panel-left { border-right: none; border-bottom: 1px solid var(--border); }
    header { padding: 1.5rem; }
    .panel-left, .panel-right { padding: 1.5rem; }
  }
</style>
</head>
<body>

<header>
  <div class="logo">Only <span>Bloom</span> Studio</div>
  <div>
    <span class="status-dot"></span>
    <span class="status-text">LORA ACTIVO — LOLLA</span>
  </div>
</header>

<div class="main">
  <!-- LEFT: Controls -->
  <div class="panel-left">
    <div>
      <div class="section-title">Prompt</div>
      <textarea id="prompt" placeholder="Describe la imagen exactamente como la quieres — escena, outfit, pose, iluminación, ambiente...&#10;&#10;Ej: sentada en terraza de café parisino, vestido midi blanco, luz de tarde, vibe elegante casual" rows="5"></textarea>
    </div>

    <div>
      <div class="section-title">Ideas rápidas</div>
      <div class="quick-prompts">
        <span class="chip" onclick="addChip('beach at sunset, white bikini, golden hour')">🏖️ Playa sunset</span>
        <span class="chip" onclick="addChip('mirror selfie in hotel bathroom, elegant lingerie, soft morning light')">🪞 Hotel mirror</span>
        <span class="chip" onclick="addChip('gym selfie, sports bra and leggings, post-workout glow, bright light')">💪 Gym</span>
        <span class="chip" onclick="addChip('sitting at rooftop restaurant, elegant dress, city lights background, night')">🌃 Rooftop night</span>
        <span class="chip" onclick="addChip('cozy morning in bed, white sheets, natural window light, casual')">☀️ Morning bed</span>
        <span class="chip" onclick="addChip('coffee shop, casual chic outfit, reading, warm ambient light')">☕ Café</span>
        <span class="chip" onclick="addChip('outdoor golden hour, flowing dress, soft bokeh background')">✨ Golden hour</span>
        <span class="chip" onclick="addChip('boudoir, tasteful lingerie, warm dramatic lighting, artistic')">🌹 Boudoir</span>
        <span class="chip" onclick="addChip('walking in city street, stylish outfit, candid shot, natural light')">🌆 Street style</span>
        <span class="chip" onclick="addChip('pool side, colorful bikini, summer vibes, bright natural light')">🏊 Pool</span>
      </div>
    </div>

    <div class="controls">
      <div>
        <div class="section-title">Estilo</div>
        <select id="style">
          <option value="glamour">Glamour</option>
          <option value="casual">Casual</option>
          <option value="intimate">Íntimo / Boudoir</option>
          <option value="athletic">Athletic / Gym</option>
          <option value="editorial">Editorial</option>
          <option value="sensual">Sensual</option>
        </select>
      </div>
      <div>
        <div class="section-title">Plataforma</div>
        <select id="platform">
          <option value="instagram">Instagram</option>
          <option value="tiktok">TikTok</option>
          <option value="twitter">Twitter/X</option>
          <option value="onlyfans">OnlyFans</option>
          <option value="telegram">Telegram</option>
        </select>
      </div>
    </div>

    <div class="controls">
      <div>
        <div class="section-title">Ratio</div>
        <select id="ratio">
          <option value="portrait_4_3">Retrato 4:3</option>
          <option value="portrait_16_9">Retrato 16:9</option>
          <option value="square_hd">Cuadrado</option>
          <option value="landscape_4_3">Landscape</option>
        </select>
      </div>
      <div>
        <div class="section-title">Calidad</div>
        <select id="steps">
          <option value="28">Rápido (28)</option>
          <option value="35" selected>Estándar (35)</option>
          <option value="50">Alta (50)</option>
        </select>
      </div>
    </div>

    <div id="errorMsg" class="error-msg"></div>

    <button class="generate-btn" id="generateBtn" onclick="generate()">
      Generar imagen
    </button>
  </div>

  <!-- RIGHT: Output -->
  <div class="panel-right">
    <div>
      <div class="section-title">Resultado</div>
      <div class="image-area" id="imageArea">
        <div class="placeholder-text" id="placeholder">
          <div class="icon">◈</div>
          <p>La imagen aparecerá aquí</p>
        </div>
        <div class="loading-overlay" id="loadingOverlay">
          <div class="spinner"></div>
          <div class="loading-msg" id="loadingMsg">Generando con LoRA de Lolla...</div>
        </div>
        <img id="resultImage" style="display:none" />
      </div>
    </div>

    <div class="image-actions" id="imageActions" style="display:none">
      <button class="action-btn primary" onclick="downloadImage()">↓ Descargar</button>
      <button class="action-btn" onclick="copyUrl()">Copiar URL</button>
      <button class="action-btn" onclick="generateVariation()">Variación</button>
    </div>

    <div id="historySection" style="display:none">
      <div class="section-title">Historial</div>
      <div class="history-strip" id="historyStrip"></div>
    </div>
  </div>
</div>

<script>
let currentImageUrl = '';
let history = [];
let lastPrompt = '';

function addChip(text) {
  const ta = document.getElementById('prompt');
  ta.value = text;
  ta.focus();
}

async function generate() {
  const prompt = document.getElementById('prompt').value.trim();
  if (!prompt) {
    showError('Escribe un prompt primero.');
    return;
  }

  lastPrompt = prompt;
  setLoading(true);
  hideError();

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        style: document.getElementById('style').value,
        platform: document.getElementById('platform').value,
        ratio: document.getElementById('ratio').value,
        steps: parseInt(document.getElementById('steps').value),
      })
    });

    const data = await res.json();

    if (data.success) {
      showImage(data.image_url);
      addToHistory(data.image_url, prompt);
    } else {
      showError(data.error || 'Error generando imagen.');
    }
  } catch (e) {
    showError('Error de conexión. Revisa que el servidor esté activo.');
  } finally {
    setLoading(false);
  }
}

function generateVariation() {
  generate();
}

function setLoading(loading) {
  const btn = document.getElementById('generateBtn');
  const overlay = document.getElementById('loadingOverlay');
  const msgs = ['Generando con LoRA de Lolla...', 'Aplicando estilo...', 'Procesando imagen...', 'Casi listo...'];
  let i = 0;

  if (loading) {
    btn.disabled = true;
    btn.classList.add('loading');
    btn.textContent = 'Generando...';
    overlay.style.display = 'flex';

    window._loadingInterval = setInterval(() => {
      i = (i + 1) % msgs.length;
      document.getElementById('loadingMsg').textContent = msgs[i];
    }, 3000);
  } else {
    btn.disabled = false;
    btn.classList.remove('loading');
    btn.textContent = 'Generar imagen';
    overlay.style.display = 'none';
    clearInterval(window._loadingInterval);
  }
}

function showImage(url) {
  currentImageUrl = url;
  document.getElementById('placeholder').style.display = 'none';
  const img = document.getElementById('resultImage');
  img.src = url;
  img.style.display = 'block';
  document.getElementById('imageActions').style.display = 'flex';
}

function addToHistory(url, prompt) {
  history.unshift({ url, prompt });
  const strip = document.getElementById('historyStrip');
  document.getElementById('historySection').style.display = 'block';

  const img = document.createElement('img');
  img.src = url;
  img.className = 'thumb active';
  img.title = prompt;
  img.onclick = () => {
    document.querySelectorAll('.thumb').forEach(t => t.classList.remove('active'));
    img.classList.add('active');
    showImage(url);
  };

  // Remove active from others
  document.querySelectorAll('.thumb').forEach(t => t.classList.remove('active'));
  strip.prepend(img);
}

function downloadImage() {
  if (!currentImageUrl) return;
  const a = document.createElement('a');
  a.href = currentImageUrl;
  a.download = `lolla_${Date.now()}.jpg`;
  a.target = '_blank';
  a.click();
}

function copyUrl() {
  if (!currentImageUrl) return;
  navigator.clipboard.writeText(currentImageUrl).then(() => {
    const btn = event.target;
    btn.textContent = '✓ Copiado';
    setTimeout(() => btn.textContent = 'Copiar URL', 2000);
  });
}

function showError(msg) {
  const el = document.getElementById('errorMsg');
  el.textContent = msg;
  el.style.display = 'block';
}

function hideError() {
  document.getElementById('errorMsg').style.display = 'none';
}

// Enter to generate
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.metaKey) generate();
});
</script>
</body>
</html>"""


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    user_prompt = data.get("prompt", "").strip()
    style       = data.get("style", "glamour")
    platform    = data.get("platform", "instagram")
    ratio       = data.get("ratio", "portrait_4_3")
    steps       = int(data.get("steps", 35))

    if not user_prompt:
        return jsonify({"success": False, "error": "Prompt vacío"})

    if not LOLLA_LORA_URL:
        return jsonify({"success": False, "error": "LOLLA_LORA_URL no configurado en Railway"})

    # Build prompt — LOLLA_REAL ALWAYS first
    style_boosters = {
        "glamour":   "professional studio lighting, elegant sophisticated pose, magazine quality",
        "casual":    "natural daylight, relaxed candid vibe, authentic lifestyle",
        "intimate":  "warm ambient light, soft romantic atmosphere, tasteful boudoir",
        "athletic":  "bright energetic light, dynamic pose, fitness photography",
        "editorial": "dramatic editorial lighting, high fashion, creative composition",
        "sensual":   "cinematic lighting, alluring confident pose, classy not trashy",
    }

    platform_boost = {
        "instagram": "instagram aesthetic, clean composition",
        "tiktok":    "vertical format, vibrant, eye-catching",
        "twitter":   "bold, attention-grabbing",
        "onlyfans":  "intimate exclusive feeling, premium quality",
        "telegram":  "personal warm feeling",
    }

    safety = platform not in ("onlyfans", "twitter")

    full_prompt = ", ".join(filter(None, [
        "LOLLA_REAL",
        user_prompt,
        style_boosters.get(style, ""),
        platform_boost.get(platform, ""),
        "photorealistic, 4k, sharp focus, natural skin texture",
    ]))

    negative = (
        "different person, wrong face, other woman, bad anatomy, "
        "deformed, ugly, blurry, low quality, cartoon, watermark, "
        "text, oversaturated, plastic skin, doll-like"
    )

    try:
        result = fal_client.subscribe(
            "fal-ai/flux-lora",
            arguments={
                "prompt": full_prompt,
                "negative_prompt": negative,
                "loras": [{"path": LOLLA_LORA_URL, "scale": 1.0}],
                "image_size": ratio,
                "num_inference_steps": steps,
                "guidance_scale": 3.5,
                "num_images": 1,
                "enable_safety_checker": safety,
            }
        )

        if result and result.get("images"):
            url = result["images"][0]["url"]

            # Save log
            try:
                log_path = Path("data/image_log.json")
                log_path.parent.mkdir(exist_ok=True)
                logs = json.loads(log_path.read_text()) if log_path.exists() else []
                logs.append({
                    "ts": datetime.now().isoformat(),
                    "prompt": user_prompt,
                    "style": style,
                    "platform": platform,
                    "url": url,
                })
                log_path.write_text(json.dumps(logs[-200:], indent=2))
            except:
                pass

            return jsonify({"success": True, "image_url": url, "prompt_used": full_prompt})
        else:
            return jsonify({"success": False, "error": "FAL.ai no devolvió imágenes"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "lora": bool(LOLLA_LORA_URL),
        "fal": bool(FAL_KEY),
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
