"""
Only Bloom Studio — Web Interface v2
=====================================
- Genera imágenes con el LoRA de Lolla via FAL.ai
- Sube imágenes de referencia (pose, lighting, composición)
- Agrega links de modelos con notas de qué tomar de referencia
"""
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
import fal_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB max

FAL_KEY = os.getenv("FAL_KEY")
LOLLA_LORA_URL = os.getenv("LOLLA_LORA_URL", "")
os.environ["FAL_KEY"] = FAL_KEY or ""

# ─── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Only Bloom Studio</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Montserrat:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --cream:#faf7f4; --warm:#f0ebe4; --blush:#e8d5c4;
    --rose:#c9907a; --deep:#2a1f1a; --muted:#8a7060;
    --border:rgba(42,31,26,0.12);
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:var(--cream);color:var(--deep);font-family:'Montserrat',sans-serif;font-weight:300;min-height:100vh;}

  header{padding:1.4rem 2.5rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--cream);position:sticky;top:0;z-index:100;}
  .logo{font-family:'Cormorant Garamond',serif;font-size:1.65rem;font-weight:300;letter-spacing:0.15em;}
  .logo span{color:var(--rose);font-style:italic;}
  .status-dot{width:8px;height:8px;border-radius:50%;background:#5cb85c;display:inline-block;margin-right:0.5rem;animation:pulse 2s infinite;}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
  .status-text{font-size:0.7rem;color:var(--muted);letter-spacing:0.05em;}

  .main{display:grid;grid-template-columns:420px 1fr;min-height:calc(100vh - 61px);}

  .panel-left{border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto;max-height:calc(100vh - 61px);}
  .panel-left::-webkit-scrollbar{width:4px;}
  .panel-left::-webkit-scrollbar-thumb{background:var(--blush);border-radius:2px;}

  .section{padding:1.4rem 2rem;border-bottom:1px solid var(--border);}
  .section-title{font-size:0.6rem;letter-spacing:0.22em;text-transform:uppercase;color:var(--muted);margin-bottom:0.7rem;}

  textarea,input.text-in{width:100%;background:var(--warm);border:1px solid var(--border);border-radius:4px;padding:0.8rem 0.9rem;font-family:'Montserrat',sans-serif;font-size:0.82rem;font-weight:300;color:var(--deep);outline:none;transition:border-color 0.2s;}
  textarea{resize:vertical;min-height:88px;line-height:1.6;}
  textarea:focus,input.text-in:focus{border-color:var(--rose);}
  textarea::placeholder,input.text-in::placeholder{color:var(--muted);font-size:0.76rem;}

  .chips{display:flex;flex-wrap:wrap;gap:0.4rem;margin-top:0.7rem;}
  .chip{padding:0.28rem 0.62rem;background:var(--warm);border:1px solid var(--border);border-radius:20px;font-size:0.67rem;cursor:pointer;transition:all 0.15s;color:var(--muted);user-select:none;}
  .chip:hover{background:var(--blush);border-color:var(--rose);color:var(--deep);}

  /* dropzone */
  .dropzone{border:1.5px dashed var(--blush);border-radius:6px;padding:1.1rem;text-align:center;cursor:pointer;transition:all 0.2s;background:var(--warm);position:relative;}
  .dropzone:hover,.dropzone.dragover{border-color:var(--rose);background:#f5ede8;}
  .dropzone input[type="file"]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;}
  .dz-icon{font-size:1.3rem;opacity:0.45;margin-bottom:0.25rem;}
  .dz-text{font-size:0.7rem;color:var(--muted);line-height:1.5;}
  .dz-text strong{color:var(--rose);font-weight:400;}

  .ref-grid{display:flex;gap:0.45rem;flex-wrap:wrap;margin-top:0.65rem;}
  .ref-item{position:relative;width:70px;height:70px;border-radius:4px;overflow:hidden;border:1px solid var(--border);}
  .ref-item img{width:100%;height:100%;object-fit:cover;}
  .ref-item.ready{border-color:var(--rose);box-shadow:0 0 0 2px rgba(201,144,122,0.25);}
  .ref-remove{position:absolute;top:2px;right:2px;width:17px;height:17px;background:rgba(42,31,26,0.75);color:#fff;border:none;border-radius:50%;font-size:0.55rem;cursor:pointer;display:flex;align-items:center;justify-content:center;}
  .primary-badge{position:absolute;bottom:2px;left:2px;background:var(--rose);color:#fff;font-size:0.48rem;letter-spacing:0.04em;padding:1px 4px;border-radius:2px;text-transform:uppercase;}

  .strength-row{display:flex;align-items:center;gap:0.7rem;margin-top:0.65rem;}
  .str-label{font-size:0.66rem;color:var(--muted);white-space:nowrap;}
  input[type="range"]{flex:1;accent-color:var(--rose);cursor:pointer;}
  .str-val{font-size:0.68rem;color:var(--rose);width:2.2rem;text-align:right;font-weight:400;}
  .str-hint{font-size:0.6rem;color:var(--muted);margin-top:0.3rem;line-height:1.4;}

  /* links */
  .link-add-row{display:flex;gap:0.45rem;margin-bottom:0.6rem;}
  .add-btn{padding:0.6rem 0.8rem;background:var(--deep);color:var(--cream);border:none;border-radius:4px;font-family:'Montserrat',sans-serif;font-size:0.7rem;letter-spacing:0.07em;cursor:pointer;transition:background 0.15s;white-space:nowrap;}
  .add-btn:hover{background:var(--rose);}

  .aspect-chips{display:flex;flex-wrap:wrap;gap:0.35rem;margin-bottom:0.55rem;}
  .a-chip{padding:0.25rem 0.58rem;background:var(--warm);border:1px solid var(--border);border-radius:12px;font-size:0.64rem;cursor:pointer;color:var(--muted);transition:all 0.15s;user-select:none;}
  .a-chip.sel{background:var(--blush);border-color:var(--rose);color:var(--deep);}

  .links-list{display:flex;flex-direction:column;gap:0.45rem;}
  .link-card{background:var(--warm);border:1px solid var(--border);border-radius:4px;padding:0.6rem 0.7rem;}
  .lc-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:0.3rem;}
  .lc-url{font-size:0.66rem;color:var(--rose);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:240px;}
  .lc-rm{background:none;border:none;cursor:pointer;color:var(--muted);font-size:0.72rem;padding:0 0.2rem;transition:color 0.15s;}
  .lc-rm:hover{color:#c0392b;}
  .lc-badges{display:flex;flex-wrap:wrap;gap:0.28rem;}
  .badge{background:var(--blush);color:var(--deep);font-size:0.56rem;letter-spacing:0.04em;padding:0.12rem 0.42rem;border-radius:10px;text-transform:uppercase;}
  .lc-note{font-size:0.63rem;color:var(--muted);font-style:italic;margin-top:0.18rem;}
  .no-links{font-size:0.68rem;color:var(--muted);font-style:italic;text-align:center;padding:0.5rem 0;}

  /* controls */
  .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:0.7rem;}
  select{width:100%;background:var(--warm);border:1px solid var(--border);border-radius:4px;padding:0.62rem 0.8rem;font-family:'Montserrat',sans-serif;font-size:0.76rem;font-weight:300;color:var(--deep);cursor:pointer;outline:none;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%238a7060'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 0.7rem center;}
  select:focus{border-color:var(--rose);}
  .sel-label{font-size:0.6rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted);margin-bottom:0.3rem;}

  /* generate */
  .gen-section{padding:1.1rem 2rem;position:sticky;bottom:0;background:var(--cream);border-top:1px solid var(--border);}
  .gen-btn{width:100%;padding:0.88rem;background:var(--deep);color:var(--cream);border:none;border-radius:4px;font-family:'Montserrat',sans-serif;font-size:0.77rem;font-weight:400;letter-spacing:0.18em;text-transform:uppercase;cursor:pointer;transition:all 0.2s;}
  .gen-btn:hover{background:var(--rose);}
  .gen-btn:disabled{background:var(--blush);cursor:not-allowed;}
  .gen-btn.loading{background:var(--muted);animation:shimmer 1.5s infinite;}
  @keyframes shimmer{0%,100%{opacity:1}50%{opacity:0.7}}
  .err{background:#fdf0ed;border:1px solid #e8b4a0;border-radius:4px;padding:0.62rem 0.85rem;font-size:0.73rem;color:#8b3a2a;margin-bottom:0.7rem;display:none;line-height:1.5;}

  /* right panel */
  .panel-right{padding:2rem 2.5rem;display:flex;flex-direction:column;gap:1.2rem;}
  .img-area{flex:1;background:var(--warm);border:1px solid var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;min-height:440px;position:relative;overflow:hidden;}
  .img-area img{width:100%;height:100%;object-fit:contain;border-radius:6px;}
  .ph{text-align:center;color:var(--muted);}
  .ph .icon{font-size:1.8rem;opacity:0.28;margin-bottom:0.4rem;}
  .ph p{font-size:0.76rem;letter-spacing:0.04em;}
  .ph small{font-size:0.63rem;opacity:0.55;margin-top:0.2rem;display:block;}

  .loading-ov{position:absolute;inset:0;background:rgba(250,247,244,0.92);display:none;flex-direction:column;align-items:center;justify-content:center;gap:0.8rem;}
  .spinner{width:34px;height:34px;border:2px solid var(--blush);border-top-color:var(--rose);border-radius:50%;animation:spin 0.8s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg)}}
  .load-msg{font-size:0.73rem;color:var(--muted);letter-spacing:0.04em;}
  .ref-badge{font-size:0.63rem;color:var(--rose);background:var(--blush);padding:0.18rem 0.55rem;border-radius:10px;}

  .img-actions{display:flex;gap:0.6rem;}
  .act-btn{flex:1;padding:0.58rem;border:1px solid var(--border);border-radius:4px;background:transparent;font-family:'Montserrat',sans-serif;font-size:0.66rem;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;color:var(--muted);transition:all 0.15s;}
  .act-btn:hover{border-color:var(--rose);color:var(--deep);}
  .act-btn.pri{background:var(--deep);color:var(--cream);border-color:var(--deep);}
  .act-btn.pri:hover{background:var(--rose);border-color:var(--rose);}

  .prompt-box{background:var(--warm);border:1px solid var(--border);border-radius:4px;padding:0.7rem 0.9rem;font-size:0.68rem;color:var(--muted);font-style:italic;line-height:1.6;display:none;}
  .prompt-box strong{color:var(--rose);font-style:normal;font-weight:400;font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase;display:block;margin-bottom:0.2rem;}

  .history{display:flex;gap:0.45rem;overflow-x:auto;padding-bottom:0.2rem;}
  .history::-webkit-scrollbar{height:3px;}
  .history::-webkit-scrollbar-thumb{background:var(--blush);}
  .thumb{width:56px;height:56px;border-radius:3px;object-fit:cover;cursor:pointer;opacity:0.7;transition:opacity 0.15s;border:1px solid var(--border);flex-shrink:0;}
  .thumb:hover,.thumb.active{opacity:1;border-color:var(--rose);}

  @media(max-width:900px){
    .main{grid-template-columns:1fr;}
    .panel-left{border-right:none;border-bottom:1px solid var(--border);max-height:none;}
    header,.section,.panel-right,.gen-section{padding:1.2rem 1.5rem;}
  }
</style>
</head>
<body>

<header>
  <div class="logo">Only <span>Bloom</span> Studio</div>
  <div><span class="status-dot"></span><span class="status-text">LORA ACTIVO — LOLLA v2</span></div>
</header>

<div class="main">
<div class="panel-left">

  <!-- PROMPT -->
  <div class="section">
    <div class="section-title">Prompt</div>
    <textarea id="prompt" rows="5" placeholder="Describe la imagen — escena, outfit, pose, iluminación, ambiente...&#10;&#10;Ej: sentada en terraza parisina, vestido midi blanco, luz de tarde, vibe elegante casual"></textarea>
    <div class="chips">
      <span class="chip" onclick="addChip('beach at sunset, white bikini, golden hour, sand dunes')">🏖️ Playa</span>
      <span class="chip" onclick="addChip('mirror selfie hotel bathroom, elegant lingerie, soft morning light')">🪞 Hotel mirror</span>
      <span class="chip" onclick="addChip('gym selfie, sports bra leggings, post-workout glow, bright')">💪 Gym</span>
      <span class="chip" onclick="addChip('rooftop restaurant, elegant dress, city lights, night')">🌃 Rooftop</span>
      <span class="chip" onclick="addChip('cozy morning in bed, white sheets, natural window light')">☀️ Morning</span>
      <span class="chip" onclick="addChip('coffee shop, casual chic outfit, reading, warm ambient light')">☕ Café</span>
      <span class="chip" onclick="addChip('outdoor golden hour, flowing dress, soft bokeh, backlit')">✨ Golden hour</span>
      <span class="chip" onclick="addChip('boudoir, tasteful lingerie, warm dramatic lighting, artistic')">🌹 Boudoir</span>
      <span class="chip" onclick="addChip('city street, stylish outfit, candid shot, natural light')">🌆 Street</span>
      <span class="chip" onclick="addChip('pool side, colorful bikini, summer vibes, bright')">🏊 Pool</span>
    </div>
  </div>

  <!-- REF IMAGES -->
  <div class="section">
    <div class="section-title">Imágenes de referencia <span style="color:var(--rose);font-size:0.55rem;margin-left:0.3rem">máx. 3</span></div>
    <div class="dropzone" id="dropzone">
      <input type="file" id="refFile" accept="image/*" multiple onchange="handleUpload(this.files)">
      <div class="dz-icon">🖼️</div>
      <div class="dz-text"><strong>Click o arrastra</strong> para subir referencias<br>PNG · JPG · WEBP</div>
    </div>
    <div class="ref-grid" id="refGrid"></div>
    <div id="strengthWrap" style="display:none">
      <div class="strength-row">
        <span class="str-label">Influencia</span>
        <input type="range" id="refStr" min="20" max="80" value="45" oninput="document.getElementById('strVal').textContent=this.value+'%'">
        <span class="str-val" id="strVal">45%</span>
      </div>
      <div class="str-hint">Baja = Lolla sigue siendo el foco &nbsp;·&nbsp; Alta = sigue más la referencia</div>
    </div>
  </div>

  <!-- REF LINKS -->
  <div class="section">
    <div class="section-title">Links de referencia</div>
    <div class="link-add-row">
      <input class="text-in" id="linkUrl" placeholder="https://instagram.com/p/... o @modelo" onkeydown="if(event.key==='Enter')addLink()">
      <button class="add-btn" onclick="addLink()">+ Agregar</button>
    </div>
    <div style="margin-bottom:0.5rem">
      <div class="section-title" style="margin-bottom:0.38rem">¿Qué tomar de esta referencia?</div>
      <div class="aspect-chips" id="aspectChips">
        <span class="a-chip" data-v="pose" onclick="toggleAspect(this)">💃 Pose</span>
        <span class="a-chip" data-v="iluminación" onclick="toggleAspect(this)">💡 Iluminación</span>
        <span class="a-chip" data-v="outfit" onclick="toggleAspect(this)">👗 Outfit</span>
        <span class="a-chip" data-v="composición" onclick="toggleAspect(this)">📐 Composición</span>
        <span class="a-chip" data-v="ambiente" onclick="toggleAspect(this)">🌫️ Ambiente</span>
        <span class="a-chip" data-v="color palette" onclick="toggleAspect(this)">🎨 Color</span>
        <span class="a-chip" data-v="expresión" onclick="toggleAspect(this)">😏 Expresión</span>
        <span class="a-chip" data-v="locación" onclick="toggleAspect(this)">📍 Locación</span>
      </div>
    </div>
    <input class="text-in" id="linkNote" style="margin-bottom:0.7rem" placeholder="Nota extra: ej. misma posición de piernas, luz muy suave..." onkeydown="if(event.key==='Enter')addLink()">
    <div class="links-list" id="linksList"></div>
    <div class="no-links" id="noLinks">Sin links aún — agrega perfiles o posts de referencia</div>
  </div>

  <!-- SETTINGS -->
  <div class="section">
    <div class="section-title">Configuración</div>
    <div class="grid-2">
      <div><div class="sel-label">Estilo</div>
        <select id="style">
          <option value="glamour">Glamour</option>
          <option value="casual">Casual</option>
          <option value="intimate">Íntimo / Boudoir</option>
          <option value="athletic">Athletic</option>
          <option value="editorial">Editorial</option>
          <option value="sensual">Sensual</option>
        </select>
      </div>
      <div><div class="sel-label">Plataforma</div>
        <select id="platform">
          <option value="instagram">Instagram</option>
          <option value="tiktok">TikTok</option>
          <option value="twitter">Twitter/X</option>
          <option value="onlyfans">OnlyFans</option>
          <option value="telegram">Telegram</option>
        </select>
      </div>
    </div>
    <div class="grid-2" style="margin-top:0.7rem">
      <div><div class="sel-label">Ratio</div>
        <select id="ratio">
          <option value="portrait_4_3">Retrato 4:3</option>
          <option value="portrait_16_9">Retrato 16:9</option>
          <option value="square_hd">Cuadrado</option>
          <option value="landscape_4_3">Landscape</option>
        </select>
      </div>
      <div><div class="sel-label">Calidad</div>
        <select id="steps">
          <option value="28">Rápido (28)</option>
          <option value="35" selected>Estándar (35)</option>
          <option value="50">Alta (50)</option>
        </select>
      </div>
    </div>
  </div>

  <div class="gen-section">
    <div class="err" id="errMsg"></div>
    <button class="gen-btn" id="genBtn" onclick="generate()">Generar imagen</button>
  </div>
</div>

<!-- RIGHT PANEL -->
<div class="panel-right">
  <div>
    <div class="section-title">Resultado</div>
    <div class="img-area" id="imgArea">
      <div class="ph" id="ph">
        <div class="icon">◈</div>
        <p>La imagen aparecerá aquí</p>
        <small>Cmd+Enter para generar rápido</small>
      </div>
      <div class="loading-ov" id="loadOv">
        <div class="spinner"></div>
        <div class="load-msg" id="loadMsg">Generando con LoRA de Lolla...</div>
        <div class="ref-badge" id="refBadge" style="display:none">📎 Con referencia</div>
      </div>
      <img id="resultImg" style="display:none">
    </div>
  </div>
  <div class="img-actions" id="imgActions" style="display:none">
    <button class="act-btn pri" onclick="downloadImg()">↓ Descargar</button>
    <button class="act-btn" onclick="copyUrl()">Copiar URL</button>
    <button class="act-btn" onclick="generate()">Variación</button>
  </div>
  <div class="prompt-box" id="promptBox">
    <strong>Prompt enviado a FAL.ai</strong>
    <span id="promptTxt"></span>
  </div>
  <div id="histSection" style="display:none">
    <div class="section-title">Historial de sesión</div>
    <div class="history" id="history"></div>
  </div>
</div>
</div>

<script>
let currentUrl = '';
let refImages = [];
let refLinks = [];
let selAspects = [];

function addChip(t){ document.getElementById('prompt').value=t; document.getElementById('prompt').focus(); }

function toggleAspect(el){
  el.classList.toggle('sel');
  const v = el.dataset.v;
  if(el.classList.contains('sel')) selAspects.push(v);
  else selAspects = selAspects.filter(a=>a!==v);
}

// ── IMAGE UPLOAD ──
async function handleUpload(files){
  const toAdd = Array.from(files).slice(0, 3-refImages.length);
  for(const file of toAdd){
    if(refImages.length>=3) break;
    const local = URL.createObjectURL(file);
    const idx = refImages.length;
    refImages.push({local, fal_url:null, file});
    renderRefImg(idx, local, false);
    // upload
    try{
      const fd = new FormData();
      fd.append('image', file);
      const res = await fetch('/upload', {method:'POST', body:fd});
      const d = await res.json();
      if(d.success){
        refImages[idx].fal_url = d.fal_url;
        document.querySelectorAll('.ref-item')[idx]?.classList.add('ready');
      }
    }catch(e){ console.error(e); }
  }
  document.getElementById('strengthWrap').style.display = refImages.length>0 ? 'block' : 'none';
  document.getElementById('refFile').value='';
}

function renderRefImg(idx, url, ready){
  const grid = document.getElementById('refGrid');
  const el = document.createElement('div');
  el.className = 'ref-item' + (ready?' ready':'');
  el.innerHTML = `<img src="${url}" alt="ref">
    ${idx===0?'<span class="primary-badge">Principal</span>':''}
    <button class="ref-remove" onclick="removeRef(${idx})">✕</button>`;
  grid.appendChild(el);
}

function removeRef(idx){
  refImages.splice(idx,1);
  document.getElementById('refGrid').innerHTML='';
  refImages.forEach((r,i)=>renderRefImg(i,r.local,!!r.fal_url));
  document.getElementById('strengthWrap').style.display = refImages.length>0?'block':'none';
}

const dz = document.getElementById('dropzone');
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('dragover');});
dz.addEventListener('dragleave',()=>dz.classList.remove('dragover'));
dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('dragover');handleUpload(e.dataTransfer.files);});

// ── LINKS ──
function addLink(){
  const url = document.getElementById('linkUrl').value.trim();
  if(!url) return;
  refLinks.push({url, aspects:[...selAspects], note: document.getElementById('linkNote').value.trim()});
  renderLinks();
  document.getElementById('linkUrl').value='';
  document.getElementById('linkNote').value='';
  document.querySelectorAll('.a-chip').forEach(c=>c.classList.remove('sel'));
  selAspects=[];
}
function removeLink(i){ refLinks.splice(i,1); renderLinks(); }
function renderLinks(){
  const list = document.getElementById('linksList');
  const msg = document.getElementById('noLinks');
  list.innerHTML='';
  if(!refLinks.length){ msg.style.display='block'; return; }
  msg.style.display='none';
  refLinks.forEach((l,i)=>{
    const el=document.createElement('div');
    el.className='link-card';
    el.innerHTML=`<div class="lc-header">
      <span class="lc-url">${l.url}</span>
      <button class="lc-rm" onclick="removeLink(${i})">✕</button>
    </div>
    <div class="lc-badges">${l.aspects.map(a=>`<span class="badge">${a}</span>`).join('')}</div>
    ${l.note?`<div class="lc-note">"${l.note}"</div>`:''}`;
    list.appendChild(el);
  });
}

// ── GENERATE ──
async function generate(){
  const prompt = document.getElementById('prompt').value.trim();
  if(!prompt){ showErr('Escribe un prompt primero.'); return; }
  const pri = refImages.find(r=>r.fal_url);
  const hasRef = !!pri;
  setLoading(true, hasRef);
  hideErr();
  try{
    const res = await fetch('/generate',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        prompt,
        style: document.getElementById('style').value,
        platform: document.getElementById('platform').value,
        ratio: document.getElementById('ratio').value,
        steps: parseInt(document.getElementById('steps').value),
        ref_image_url: hasRef ? pri.fal_url : null,
        ref_strength: hasRef ? parseInt(document.getElementById('refStr').value)/100 : null,
        ref_links: refLinks,
      })
    });
    const d = await res.json();
    if(d.success){
      showImg(d.image_url);
      addHistory(d.image_url, prompt);
      if(d.prompt_used){
        document.getElementById('promptTxt').textContent=d.prompt_used;
        document.getElementById('promptBox').style.display='block';
      }
    } else { showErr(d.error||'Error generando imagen.'); }
  }catch(e){ showErr('Error de conexión.'); }
  finally{ setLoading(false); }
}

function setLoading(on, hasRef){
  const btn=document.getElementById('genBtn'),ov=document.getElementById('loadOv');
  const msgs=['Generando con LoRA de Lolla...','Aplicando referencias...','Procesando detalles...','Casi listo...'];
  if(on){
    btn.disabled=true; btn.classList.add('loading'); btn.textContent='Generando...';
    ov.style.display='flex';
    document.getElementById('refBadge').style.display = hasRef?'inline-block':'none';
    let i=0; window._li=setInterval(()=>{ i=(i+1)%msgs.length; document.getElementById('loadMsg').textContent=msgs[i]; },3500);
  }else{
    btn.disabled=false; btn.classList.remove('loading'); btn.textContent='Generar imagen';
    ov.style.display='none'; clearInterval(window._li);
  }
}
function showImg(url){
  currentUrl=url;
  document.getElementById('ph').style.display='none';
  const img=document.getElementById('resultImg');
  img.src=url; img.style.display='block';
  document.getElementById('imgActions').style.display='flex';
}
function addHistory(url, p){
  document.getElementById('histSection').style.display='block';
  const img=document.createElement('img');
  img.src=url; img.className='thumb active'; img.title=p;
  img.onclick=()=>{ document.querySelectorAll('.thumb').forEach(t=>t.classList.remove('active')); img.classList.add('active'); showImg(url); };
  document.querySelectorAll('.thumb').forEach(t=>t.classList.remove('active'));
  document.getElementById('history').prepend(img);
}
function downloadImg(){
  if(!currentUrl) return;
  const a=document.createElement('a'); a.href=currentUrl; a.download=`lolla_${Date.now()}.jpg`; a.target='_blank'; a.click();
}
function copyUrl(){
  if(!currentUrl) return;
  navigator.clipboard.writeText(currentUrl).then(()=>{ const b=event.target; b.textContent='✓ Copiado'; setTimeout(()=>b.textContent='Copiar URL',2000); });
}
function showErr(m){ const e=document.getElementById('errMsg'); e.textContent=m; e.style.display='block'; }
function hideErr(){ document.getElementById('errMsg').style.display='none'; }
document.addEventListener('keydown',e=>{ if(e.key==='Enter'&&e.metaKey) generate(); });
</script>
</body>
</html>"""


# ─── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/upload", methods=["POST"])
def upload_image():
    """Upload reference image to FAL storage, return CDN URL."""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image provided"})
    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "Empty file"})
    try:
        suffix = Path(file.filename).suffix.lower() or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        fal_url = fal_client.upload_file(tmp_path)
        try:
            os.unlink(tmp_path)
        except:
            pass
        return jsonify({"success": True, "fal_url": fal_url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    user_prompt   = data.get("prompt", "").strip()
    style         = data.get("style", "glamour")
    platform      = data.get("platform", "instagram")
    ratio         = data.get("ratio", "portrait_4_3")
    steps         = int(data.get("steps", 35))
    ref_image_url = data.get("ref_image_url")
    ref_strength  = data.get("ref_strength", 0.45)
    ref_links     = data.get("ref_links", [])

    if not user_prompt:
        return jsonify({"success": False, "error": "Prompt vacío"})
    if not LOLLA_LORA_URL:
        return jsonify({"success": False, "error": "LOLLA_LORA_URL no configurado"})

    style_boosters = {
        "glamour":   "professional studio lighting, elegant sophisticated pose, magazine quality",
        "casual":    "natural daylight, relaxed candid vibe, authentic lifestyle photography",
        "intimate":  "warm ambient light, soft romantic atmosphere, tasteful boudoir",
        "athletic":  "bright energetic light, dynamic pose, fitness photography",
        "editorial": "dramatic editorial lighting, high fashion, creative composition",
        "sensual":   "cinematic lighting, alluring confident pose, classy not trashy",
    }
    platform_boost = {
        "instagram": "instagram aesthetic, clean balanced composition",
        "tiktok":    "vertical format, vibrant eye-catching composition",
        "twitter":   "bold attention-grabbing, strong visual impact",
        "onlyfans":  "intimate exclusive feeling, premium quality",
        "telegram":  "personal warm feeling",
    }

    # Compile link context
    link_parts = []
    for lnk in ref_links:
        aspects = lnk.get("aspects", [])
        note    = lnk.get("note", "")
        parts   = []
        if aspects:
            parts.append("same " + " and ".join(aspects))
        if note:
            parts.append(note)
        if parts:
            link_parts.append(", ".join(parts))
    link_context = ("inspired by: " + "; ".join(link_parts)) if link_parts else ""

    # Photorealism boosters
    realism = (
        "shot on Sony A7R V, 85mm f1.4 lens, shallow depth of field, "
        "natural skin texture, subsurface scattering, pores visible, "
        "photorealistic, 8K, RAW photo, cinematic"
    )

    safety = platform not in ("onlyfans", "twitter")

    full_prompt = ", ".join(filter(None, [
        "LOLLA_REAL",
        user_prompt,
        style_boosters.get(style, ""),
        platform_boost.get(platform, ""),
        link_context,
        realism,
    ]))

    negative = (
        "different person, wrong face, other woman, bad anatomy, "
        "deformed, ugly, blurry, low quality, cartoon, watermark, "
        "text, oversaturated, plastic skin, doll-like, ai-looking"
    )

    try:
        # FLUX.2 [dev] LoRA — mejor skin texture, mantiene LoRA de Lolla
        endpoint = "fal-ai/flux-2/lora/image-to-image" if ref_image_url else "fal-ai/flux-2/lora"
        arguments = {
            "prompt":                full_prompt,
            "negative_prompt":       negative,
            "loras":                 [{"path": LOLLA_LORA_URL, "scale": 0.9}],
            "image_size":            ratio,
            "num_inference_steps":   steps,
            "guidance_scale":        3.5,
            "num_images":            1,
            "enable_safety_checker": safety,
        }
        if ref_image_url:
            arguments["image_url"] = ref_image_url
            arguments["strength"]  = float(ref_strength)

        result = fal_client.subscribe(endpoint, arguments=arguments)

        if result and result.get("images"):
            url = result["images"][0]["url"]
            try:
                log_path = Path("data/image_log.json")
                log_path.parent.mkdir(exist_ok=True)
                logs = json.loads(log_path.read_text()) if log_path.exists() else []
                logs.append({
                    "ts": datetime.now().isoformat(),
                    "prompt": user_prompt, "style": style,
                    "platform": platform,
                    "ref_image": bool(ref_image_url),
                    "ref_links": len(ref_links),
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
    return jsonify({"status": "ok", "lora": bool(LOLLA_LORA_URL), "fal": bool(FAL_KEY), "version": "2.0"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
