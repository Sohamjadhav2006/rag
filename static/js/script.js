
// const modeToggle = document.getElementById("modeToggle");
// const modeIcon = document.getElementById("modeIcon");
// const modeLabel = document.getElementById("modeLabel");

// function applyMode(mode){
//   if(mode === "light"){
//     document.documentElement.classList.add("light");
//     document.body.classList.add("light");
//     modeIcon.textContent = "☀️";
//     modeLabel.textContent = "Light";
//   } else {
//     document.documentElement.classList.remove("light");
//     document.body.classList.remove("light");
//     modeIcon.textContent = "🌙";
//     modeLabel.textContent = "Dark";
//   }
//   localStorage.setItem("mode",""+mode);
// }

// applyMode(localStorage.getItem("mode") || "dark");

// modeToggle.onclick = () => {
//   const isLight = document.documentElement.classList.contains("light");
//   applyMode(isLight ? "dark" : "light");
// };


// const askBtn = document.getElementById("askBtn");
// const downloadBtn = document.getElementById("downloadBtn");
// const answerDiv = document.getElementById("answer");
// const qEl = document.getElementById("question");
// const results = document.getElementById("results");

// askBtn.onclick = async () => {
//   const q = qEl.value.trim();
//   if(!q) return alert("Enter a question");

//   const res = await fetch("/ask",{
//     method:"POST",
//     headers:{"Content-Type":"application/json"},
//     body:JSON.stringify({question:q})
//   });

//   const data = await res.json();
//   answerDiv.innerHTML = data.html_response;
//   results.hidden = false;
//   downloadBtn.style.display = "inline-block";
// };

// downloadBtn.onclick = async () => {
//   const q = qEl.value.trim();
//   const res = await fetch("/download",{
//     method:"POST",
//     headers:{"Content-Type":"application/json"},
//     body:JSON.stringify({question:q})
//   });

//   const blob = await res.blob();
//   const url = URL.createObjectURL(blob);
//   const a = document.createElement("a");
//   a.href = url;
//   a.download = "sigma_answer.pdf";
//   a.click();
// };


/* Robust theme application: set class on BOTH html and body */
const modeToggle = document.getElementById('modeToggle');
const modeIcon = document.getElementById('modeIcon');
const modeLabel = document.getElementById('modeLabel');

function applyMode(mode){
  mode = (mode === 'light') ? 'light' : 'dark';
  if(mode === 'light'){
    document.documentElement.classList.add('light');
    document.body.classList.add('light');
    modeIcon.textContent = '☀️';
    modeLabel.textContent = 'Light';
  } else {
    document.documentElement.classList.remove('light');
    document.body.classList.remove('light');
    modeIcon.textContent = '🌙';
    modeLabel.textContent = 'Dark';
  }
  localStorage.setItem('sigma_mode', mode);
}

/* apply on initial load and pageshow (handles bfcache) */
document.addEventListener('DOMContentLoaded', function(){
  const saved = localStorage.getItem('sigma_mode') || 'dark';
  applyMode(saved);
});
window.addEventListener('pageshow', () => {
  const saved = localStorage.getItem('sigma_mode') || 'dark';
  applyMode(saved);
});
modeToggle.addEventListener('click', ()=>{
  const current = document.documentElement.classList.contains('light') ? 'light' : 'dark';
  applyMode(current === 'light' ? 'dark' : 'light');
});

/* ===== Rest of frontend logic (STT/TTS, ask, download) — unchanged ===== */
const askBtn = document.getElementById('askBtn');
const downloadBtn = document.getElementById('downloadBtn');
const clearBtn = document.getElementById('clearBtn');
const micBtn = document.getElementById('micBtn');
const qEl = document.getElementById('question');
const spinner = document.getElementById('spinner');
const results = document.getElementById('results');
const answerDiv = document.getElementById('answer');
const chunksCard = document.getElementById('chunksCard');
const chunksList = document.getElementById('chunksList');
const ttsToggle = document.getElementById('ttsToggle');
const playBtn = document.getElementById('playBtn');

let recognition = null;
let isListening = false;
let lastAnswerText = "";
let usedModel = null;

/* Speech Recognition */
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.addEventListener('result', (e) => {
    const text = Array.from(e.results).map(r => r[0].transcript).join('');
    qEl.value = (qEl.value ? qEl.value + ' ' : '') + text;
  });
  recognition.addEventListener('end', () => {
    micBtn.classList.remove('mic-listening');
    micBtn.setAttribute('aria-pressed', 'false');
    isListening = false;
  });
  recognition.addEventListener('error', (ev) => {
    micBtn.classList.remove('mic-listening');
    micBtn.setAttribute('aria-pressed', 'false');
    isListening = false;
    alert('Speech recognition error: ' + ev.error);
  });
} else {
  micBtn.disabled = true;
  micBtn.title = 'Speech recognition not supported in this browser';
}

/* TTS: browser speechSynthesis */
const ttsSupported = ('speechSynthesis' in window);
function speak(text) {
  if (!ttsSupported) return;
  if (!text) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.0; utter.pitch = 1.0;
  const voices = window.speechSynthesis.getVoices();
  if (voices && voices.length) {
    const v = voices.find(v => v.lang && v.lang.startsWith('en')) || voices[0];
    if (v) utter.voice = v;
  }
  utter.onend = () => { playBtn.textContent = '🔊 Play'; };
  window.speechSynthesis.speak(utter);
  playBtn.textContent = '⏸️ Stop';
}

/* Helpers and actions */
function setLoading(on){
  spinner.style.display = on ? 'inline' : 'none';
  askBtn.disabled = on;
  clearBtn.disabled = on;
  micBtn.disabled = on || !recognition;
  downloadBtn.disabled = on;
}
function formatSec(s){
  s = Number(s)||0; const h=Math.floor(s/3600); const m=Math.floor((s%3600)/60); const sec=Math.floor(s%60);
  if(h>0) return `${h}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; return `${m}:${String(sec).padStart(2,'0')}`;
}

async function ask(){
  const q = qEl.value.trim(); if(!q) return alert('Please type or speak a question first.');
  setLoading(true); results.hidden=true; answerDiv.textContent=''; chunksList.innerHTML=''; chunksCard.hidden=true; downloadBtn.style.display='none';
  try{
    const res = await fetch('/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
    const data = await res.json();
    if(!res.ok){
      answerDiv.textContent = data.error || 'Server error';
      results.hidden = false;
      return;
    }
    usedModel = data.used_model || null;
    lastAnswerText = data.response || '';
    answerDiv.innerHTML = data.html_response || (data.response || '');
    if (ttsSupported && ttsToggle.checked && lastAnswerText){
      playBtn.style.display = 'inline-block';
      speak(lastAnswerText);
    } else {
      playBtn.style.display = 'none';
    }
    const chunks = data.chunks || [];
    if(chunks.length>0){
      chunksCard.hidden=false;
      chunksList.innerHTML='';
      for(const c of chunks){
        const el = document.createElement('div'); el.className='chunk';
        const left = document.createElement('div'); left.style.flex='1 1 auto';
        const meta = document.createElement('div'); meta.className='meta';
        meta.textContent = `${c.title || 'Video'} ${c.number || ''} • ${formatSec(c.start)} - ${formatSec(c.end)}`;
        const txt = document.createElement('div'); txt.textContent = c.text || '';
        left.appendChild(meta); left.appendChild(txt);
        const right = document.createElement('div');
        const a = document.createElement('a'); a.className='yt'; a.target='_blank'; a.rel='noopener noreferrer';
        a.href = c.youtube_link || '#'; a.textContent = 'Open timestamp';
        right.appendChild(a);
        el.appendChild(left); el.appendChild(right);
        chunksList.appendChild(el);
      }
      downloadBtn.style.display = 'inline-block';
    }
    results.hidden = false;
  } catch(err){
    answerDiv.textContent = 'Network/server error: ' + (err.message || err);
    results.hidden = false;
  } finally {
    setLoading(false);
  }
}

async function downloadPDF(){
  const q = qEl.value.trim(); if(!q) return alert('No question to download.');
  setLoading(true);
  try{
    const res = await fetch('/download', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
    if(!res.ok){
      const err = await res.json().catch(()=>({error:'download failed'}));
      alert('PDF generation failed: ' + (err.error || JSON.stringify(err)));
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sigma_answer.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch(e){
    alert('Download failed: ' + e.message);
  } finally {
    setLoading(false);
  }
}

/* Wiring */
askBtn.addEventListener('click', ask);
downloadBtn.addEventListener('click', downloadPDF);
clearBtn.addEventListener('click', ()=>{ qEl.value=''; results.hidden=true; chunksList.innerHTML=''; lastAnswerText=''; playBtn.style.display='none'; downloadBtn.style.display='none'; });
micBtn.addEventListener('click', ()=>{
  if (!recognition) return;
  if (!isListening) {
    try { recognition.start(); isListening = true; micBtn.classList.add('mic-listening'); micBtn.setAttribute('aria-pressed','true'); } catch(e){}
  } else {
    recognition.stop(); isListening = false; micBtn.classList.remove('mic-listening'); micBtn.setAttribute('aria-pressed','false');
  }
});
playBtn.addEventListener('click', ()=>{ if (!ttsSupported) return; if (window.speechSynthesis.speaking){ window.speechSynthesis.cancel(); playBtn.textContent='🔊 Play'; } else { speak(lastAnswerText); } });
qEl.addEventListener('keydown', (e)=>{ if((e.ctrlKey||e.metaKey) && e.key==='Enter') ask(); });
window.addEventListener('load', ()=> qEl.focus());

