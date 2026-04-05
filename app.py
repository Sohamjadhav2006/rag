# import os
# import pandas as pd 
# from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np 
# import joblib 
# import requests
# from google import genai
# # from config import api_key

# client = genai.Client(api_key="AIzaSyCCLYhPFsbmjSpfUnBJCPsAKO0MxySkKJk")


# def create_embedding(text_list):
#     # https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings
#     r = requests.post("http://localhost:11434/api/embed", json={
#         "model": "bge-m3",
#         "input": text_list
#     })

#     embedding = r.json()["embeddings"] 
#     return embedding

# def inference(prompt):
#     r = requests.post("http://localhost:11434/api/generate", json={
#         # "model": "deepseek-r1",
#         "model": "llama3.2",
#         "prompt": prompt,
#         "stream": False
#     })

#     response = r.json()
#     print(response)
#     return response

# def inference_openai(prompt):
#     print("Thinking...")
#     response = client.models.generate_content(
#     model="gemini-2.5-flash",
#     contents=prompt
#     )

#     return response.text
 



# df = joblib.load('embeddings.joblib')


# incoming_query = input("Ask a Question: ")
# question_embedding = create_embedding([incoming_query])[0] 

# # Find similarities of question_embedding with other embeddings
# # print(np.vstack(df['embedding'].values))
# # print(np.vstack(df['embedding']).shape)
# similarities = cosine_similarity(np.vstack(df['embedding']), [question_embedding]).flatten()
# # print(similarities)
# top_results = 5
# max_indx = similarities.argsort()[::-1][0:top_results]
# # print(max_indx)
# new_df = df.loc[max_indx] 
# # print(new_df[["title", "number", "text"]])

# prompt = f'''I am teaching web development in my Sigma web development course. Here are video subtitle chunks containing video title, video number, start time in seconds, end time in seconds, the text at that time:

# {new_df[["title", "number", "start", "end", "text"]].to_json(orient="records")}
# ---------------------------------
# "{incoming_query}"
# User asked this question related to the video chunks, you have to answer in a human way (dont mention the above format, its just for you) where and how much content is taught in which video (in which video and at what timestamp) and guide the user to go to that particular video. If user asks unrelated question, tell him that you can only answer questions related to the course 
# '''
# with open("prompt.txt", "w") as f:
#     f.write(prompt)

# # response = inference(prompt)["response"]
# # print(response)

# response = inference_openai(prompt)
# print(response)

# with open("response.txt", "w", encoding="utf-8") as f:
#     f.write(response)
# # for index, item in new_df.iterrows():
# #     print(index, item["title"], item["number"], item["text"], item["start"], item["end"])




#SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS
# import os
# import json
# import joblib
# import requests
# import numpy as np
# from flask import Flask, request, jsonify, make_response, render_template_string
# from sklearn.metrics.pairwise import cosine_similarity
# import google.genai as genai

# # ------------------------
# # Configuration
# # ------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EMBEDDINGS_FILE = os.path.join(BASE_DIR, "embeddings.joblib")
# LOCAL_EMBED_ENDPOINT = "http://localhost:11434/api/embed"
# OLLAMA_GEN_ENDPOINT = "http://localhost:11434/api/generate"
# GENAI_MODEL = "gemini-2.5-flash"
# OLLAMA_MODEL = "llama3.2"
# TOP_K = 5

# # Put your API key here (development only)
# DIRECT_GENAI_API_KEY = "wAIzaSyBwEfa2bbbZ0GB6w_hA5JckWIFd9-TJMMg"

# # ------------------------
# # Initialize
# # ------------------------
# app = Flask(__name__)
# client = genai.Client(api_key=DIRECT_GENAI_API_KEY)

# if not os.path.exists(EMBEDDINGS_FILE):
#     raise FileNotFoundError(f"{EMBEDDINGS_FILE} not found. Place embeddings.joblib next to this file.")
# df = joblib.load(EMBEDDINGS_FILE)

# if "embedding" not in df.columns:
#     raise ValueError("embeddings.joblib must contain an 'embedding' column.")
# if "youtube_link" not in df.columns:
#     print("Warning: 'youtube_link' column missing. Links will be None in responses.")

# # ------------------------
# # Simple embedded frontend (includes STT + TTS JS)
# # ------------------------
# INDEX_HTML = '''
# <!doctype html>
# <html lang="en">
# <head>
# <meta charset="utf-8"/>
# <meta name="viewport" content="width=device-width,initial-scale=1"/>
# <title>Sigma WebDev — Voice Q&A</title>
# <style>
# :root{--bg-1:#071124;--bg-2:#0b1728;--accent:#06b6d4;--muted:#9fc5ff}
# *{box-sizing:border-box}html,body{height:100%;margin:0;background:linear-gradient(180deg,var(--bg-2),var(--bg-1));color:#e6eef8;font-family:Inter,system-ui,Segoe UI,Roboto,Arial}
# .wrap{max-width:980px;margin:28px auto;padding:20px}
# .card{background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01));padding:18px;border-radius:12px;box-shadow:0 8px 30px rgba(2,6,23,0.6)}
# .header-row{display:flex;align-items:center;gap:12px}
# h1{margin:0 0 6px;font-size:22px}p.lead{margin:0 0 12px;color:var(--muted)}
# textarea{width:100%;min-height:88px;padding:12px;border-radius:8px;border:1px solid rgba(255,255,255,0.04);background:transparent;color:inherit;resize:vertical}
# .controls{display:flex;gap:8px;margin-top:10px;align-items:center}
# button{padding:9px 12px;border-radius:10px;border:none;cursor:pointer;font-weight:700}
# .btn-primary{background:linear-gradient(90deg,var(--accent),#04a7c9);color:#022}
# .btn-ghost{background:transparent;border:1px solid rgba(255,255,255,0.04);color:var(--muted)}
# .mic-btn{width:44px;height:44px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:700}
# .mic-listening{box-shadow:0 0 18px rgba(6,182,212,0.25);transform:scale(1.03)}
# .spinner{margin-left:8px;color:var(--muted)}
# .results{margin-top:18px;display:flex;flex-direction:column;gap:12px}
# .alert{background:#3b2b1a;color:#fff;padding:8px;border-radius:8px;margin-bottom:8px}
# .answer{white-space:pre-wrap;padding:12px;border-radius:10px}
# .chunk{padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
# a.yt{color:var(--accent);text-decoration:none;font-weight:600}
# footer{margin-top:12px;color:var(--muted);font-size:13px}
# kbd{background:#0b1220;border-radius:6px;padding:2px 6px}
# .small{font-size:13px;color:var(--muted)}
# </style>
# </head>
# <body>
# <div class="wrap">
#   <div id="fallbackBanner" style="display:none" class="alert"></div>

#   <div class="card">
#     <div class="header-row">
#       <div style="flex:1">
#         <h1>Sigma WebDev — Voice Q&A</h1>
#         <p class="lead">Ask about the course by typing or speaking. Listen to answers with one tap.</p>
#       </div>
#       <div style="text-align:right">
#         <div class="small">Speech: <span id="sttSupport">...</span></div>
#         <div class="small">TTS: <span id="ttsSupport">...</span></div>
#       </div>
#     </div>

#     <textarea id="question" placeholder="Type a question or use the microphone..."></textarea>

#     <div class="controls">
#       <button id="askBtn" class="btn-primary">Ask</button>
#       <button id="clearBtn" class="btn-ghost">Clear</button>
#       <button id="micBtn" class="mic-btn btn-ghost" title="Speak" aria-pressed="false">🎤</button>
#       <label class="small"><input id="ttsToggle" type="checkbox" checked/> Speak answer</label>
#       <button id="playBtn" class="btn-ghost" style="display:none">🔊 Play</button>
#       <div id="spinner" class="spinner" style="display:none">Thinking…</div>
#     </div>

#     <div style="margin-top:10px;color:var(--muted)">Tip: <kbd>Ctrl</kbd>+<kbd>Enter</kbd> to submit. Use microphone for quick voice input.</div>
#   </div>

#   <div id="results" class="results" hidden>
#     <div class="card">
#       <h3>Answer</h3>
#       <div id="answer" class="answer"></div>
#     </div>

#     <div id="chunksCard" class="card" hidden>
#       <h3>Relevant video chunks</h3>
#       <div id="chunksList"></div>
#     </div>
#   </div>

#   <footer>Uses local embedding server + GenAI/Ollama. Make sure <code>embeddings.joblib</code> is present.</footer>
# </div>

# <script>
# const askBtn = document.getElementById('askBtn');
# const clearBtn = document.getElementById('clearBtn');
# const micBtn = document.getElementById('micBtn');
# const qEl = document.getElementById('question');
# const spinner = document.getElementById('spinner');
# const results = document.getElementById('results');
# const answerDiv = document.getElementById('answer');
# const chunksCard = document.getElementById('chunksCard');
# const chunksList = document.getElementById('chunksList');
# const fallbackBanner = document.getElementById('fallbackBanner');
# const ttsToggle = document.getElementById('ttsToggle');
# const playBtn = document.getElementById('playBtn');
# const sttSupportEl = document.getElementById('sttSupport');
# const ttsSupportEl = document.getElementById('ttsSupport');

# let recognition = null;
# let isListening = false;
# let lastAnswerText = "";
# let usedModel = null;

# const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;
# if (SpeechRecognition) {
#   sttSupportEl.textContent = 'Available';
#   recognition = new SpeechRecognition();
#   recognition.lang = 'en-US';
#   recognition.interimResults = false;
#   recognition.maxAlternatives = 1;

#   recognition.addEventListener('result', (e) => {
#     const text = Array.from(e.results).map(r => r[0].transcript).join('');
#     qEl.value = (qEl.value ? qEl.value + ' ' : '') + text;
#   });

#   recognition.addEventListener('end', () => {
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#     isListening = false;
#   });

#   recognition.addEventListener('error', (ev) => {
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#     isListening = false;
#     alert('Speech recognition error: ' + ev.error);
#   });
# } else {
#   sttSupportEl.textContent = 'Not supported';
#   micBtn.title = 'Speech recognition not supported';
#   micBtn.disabled = true;
# }

# const ttsSupported = ('speechSynthesis' in window);
# ttsSupportEl.textContent = ttsSupported ? 'Available' : 'Not supported';
# if (!ttsSupported) {
#   ttsToggle.disabled = true;
#   playBtn.style.display = 'none';
# }

# function speak(text) {
#   if (!ttsSupported) return;
#   if (!text) return;
#   window.speechSynthesis.cancel();
#   const utter = new SpeechSynthesisUtterance(text);
#   utter.rate = 1.0;
#   utter.pitch = 1.0;
#   const voices = window.speechSynthesis.getVoices();
#   if (voices && voices.length) {
#     const v = voices.find(v => v.lang && v.lang.startsWith('en')) || voices[0];
#     if (v) utter.voice = v;
#   }
#   utter.onend = () => {
#     playBtn.textContent = '🔊 Play';
#   };
#   window.speechSynthesis.speak(utter);
#   playBtn.textContent = '⏸️ Stop';
# }

# micBtn.addEventListener('click', () => {
#   if (!recognition) return;
#   if (!isListening) {
#     try {
#       recognition.start();
#       isListening = true;
#       micBtn.classList.add('mic-listening');
#       micBtn.setAttribute('aria-pressed', 'true');
#     } catch (e) {}
#   } else {
#     recognition.stop();
#     isListening = false;
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#   }
# });

# playBtn.addEventListener('click', () => {
#   if (!ttsSupported) return;
#   if (window.speechSynthesis.speaking) {
#     window.speechSynthesis.cancel();
#     playBtn.textContent = '🔊 Play';
#   } else {
#     speak(lastAnswerText);
#   }
# });

# function setLoading(on){
#   spinner.style.display = on ? 'inline' : 'none';
#   askBtn.disabled = on;
#   clearBtn.disabled = on;
#   micBtn.disabled = on || !recognition;
# }

# function formatSec(s){
#   s = Number(s)||0; const h=Math.floor(s/3600); const m=Math.floor((s%3600)/60); const sec=Math.floor(s%60);
#   if(h>0) return `${h}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; return `${m}:${String(sec).padStart(2,'0')}`;
# }

# async function ask(){
#   const q = qEl.value.trim(); if(!q) return alert('Please type or speak a question first.');
#   setLoading(true); results.hidden=true; answerDiv.textContent=''; chunksList.innerHTML=''; chunksCard.hidden=true; fallbackBanner.style.display='none';
#   try{
#     const res = await fetch('/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
#     const data = await res.json();
#     if(!res.ok){
#       answerDiv.textContent = data.error || 'Server error';
#       results.hidden = false;
#       return;
#     }
#     usedModel = data.used_model || null;
#     if(usedModel && usedModel.toLowerCase().includes('ollama')){
#       fallbackBanner.style.display='block';
#       fallbackBanner.textContent = '⚠️ Gemini unavailable — answered by Ollama (local).';
#     } else if (usedModel === 'none'){
#       fallbackBanner.style.display='block';
#       fallbackBanner.textContent = '⚠️ Both Gemini and Ollama failed. See details in response.';
#     } else {
#       fallbackBanner.style.display='none';
#     }
#     lastAnswerText = data.response || '';
#     answerDiv.innerHTML = data.html_response || (data.response || '');
#     if (ttsSupported && ttsToggle.checked && lastAnswerText){
#       playBtn.style.display = 'inline-block';
#       speak(lastAnswerText);
#     } else {
#       playBtn.style.display = 'none';
#     }
#     const chunks = data.chunks || [];
#     if(chunks.length>0){
#       chunksCard.hidden=false;
#       chunksList.innerHTML='';
#       for(const c of chunks){
#         const el = document.createElement('div'); el.className='chunk';
#         const left = document.createElement('div'); left.style.flex='1 1 auto';
#         const meta = document.createElement('div'); meta.style.fontSize='13px'; meta.style.color='#9fc5ff';
#         meta.textContent = `${c.title || 'Video'} ${c.number || ''} • ${formatSec(c.start)} - ${formatSec(c.end)}`;
#         const txt = document.createElement('div'); txt.textContent = c.text || '';
#         left.appendChild(meta); left.appendChild(txt);
#         const right = document.createElement('div');
#         const a = document.createElement('a'); a.className='yt'; a.target='_blank'; a.rel='noopener noreferrer';
#         a.href = c.youtube_link || '#'; a.textContent = 'Open timestamp';
#         right.appendChild(a);
#         el.appendChild(left); el.appendChild(right);
#         chunksList.appendChild(el);
#       }
#     }
#     results.hidden = false;
#   } catch(err){
#     answerDiv.textContent = 'Network/server error: ' + (err.message || err);
#     results.hidden = false;
#   } finally {
#     setLoading(false);
#   }
# }

# askBtn.addEventListener('click', ask);
# clearBtn.addEventListener('click', ()=>{ qEl.value=''; results.hidden=true; chunksList.innerHTML=''; lastAnswerText=''; playBtn.style.display='none'; });
# qEl.addEventListener('keydown', (e)=>{ if((e.ctrlKey||e.metaKey) && e.key==='Enter') ask(); });
# window.addEventListener('load', ()=> qEl.focus());
# </script>
# </body>
# </html>
# '''

# # ------------------------
# # Backend helpers
# # ------------------------
# def create_embedding_local(text_list):
#     try:
#         r = requests.post(LOCAL_EMBED_ENDPOINT, json={"model": "bge-m3", "input": text_list}, timeout=30)
#         r.raise_for_status()
#         res = r.json()
#     except requests.exceptions.RequestException as exc:
#         raise RuntimeError(f"Local embedder error: {exc}")
#     if "embeddings" in res:
#         return res["embeddings"]
#     if "data" in res and isinstance(res["data"], list):
#         return [item.get("embedding") for item in res["data"]]
#     raise ValueError("Unexpected embedding response structure from local embedder")

# def is_genai_response_ok(resp):
#     try:
#         if hasattr(resp, "text"):
#             txt = getattr(resp, "text")
#             if txt and str(txt).strip():
#                 return True, str(txt), None
#             return False, None, "empty_text"
#     except Exception:
#         pass
#     if isinstance(resp, dict):
#         if resp.get("error") or resp.get("errors"):
#             return False, None, json.dumps(resp.get("error") or resp.get("errors"))
#         if "candidates" in resp and isinstance(resp["candidates"], list) and resp["candidates"]:
#             cand = resp["candidates"][0]
#             if isinstance(cand, dict):
#                 if "text" in cand and cand["text"]:
#                     return True, str(cand["text"]), None
#                 if "content" in cand and isinstance(cand["content"], list):
#                     for piece in cand["content"]:
#                         if isinstance(piece, dict) and "text" in piece and piece["text"]:
#                             return True, str(piece["text"]), None
#         for k in ("output", "response", "message", "result"):
#             if k in resp and resp[k]:
#                 return True, str(resp[k]), None
#         return False, None, "unknown_dict_shape"
#     return False, None, "unknown_response_type"

# def genai_call(prompt):
#     try:
#         resp = client.models.generate_content(model=GENAI_MODEL, contents=prompt)
#     except Exception as e:
#         raise RuntimeError(f"GenAI SDK raised: {e}")
#     ok, text, err = is_genai_response_ok(resp)
#     if ok:
#         return "genai", text
#     raise RuntimeError(f"GenAI returned invalid/empty response ({err})")

# def ollama_call(prompt):
#     try:
#         r = requests.post(OLLAMA_GEN_ENDPOINT, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=60)
#         r.raise_for_status()
#         data = r.json()
#     except requests.exceptions.RequestException as exc:
#         raise RuntimeError(f"Ollama call failed: {exc}")
#     if isinstance(data, dict):
#         for k in ("response", "text", "output"):
#             if k in data and data[k]:
#                 return "ollama", data[k]
#         if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
#             ch = data["choices"][0]
#             if isinstance(ch, dict):
#                 if "message" in ch and isinstance(ch["message"], dict) and "content" in ch["message"]:
#                     return "ollama", ch["message"]["content"]
#                 if "text" in ch:
#                     return "ollama", ch["text"]
#     return "ollama", json.dumps(data)

# def inference_with_fallback(prompt):
#     try:
#         used, text = genai_call(prompt)
#         return used, text
#     except Exception as gen_err:
#         print(f"[WARN] GenAI failed: {gen_err}. Falling back to Ollama...")
#         try:
#             used2, text2 = ollama_call(prompt)
#             return used2, text2
#         except Exception as oll_err:
#             err_msg = f"GenAI error: {gen_err} | Ollama error: {oll_err}"
#             print(f"[ERROR] {err_msg}")
#             return "none", f"Both GenAI and Ollama failed. Details: {err_msg}"

# # ------------------------
# # Routes
# # ------------------------
# @app.route("/", methods=["GET"])
# def index():
#     resp = make_response(render_template_string(INDEX_HTML))
#     resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     resp.headers["Pragma"] = "no-cache"
#     resp.headers["Expires"] = "0"
#     return resp

# @app.route("/ask", methods=["POST"])
# def ask():
#     payload = request.get_json(force=True)
#     question = payload.get("question", "").strip()
#     if not question:
#         return jsonify({"error": "question required"}), 400
#     try:
#         q_emb = create_embedding_local([question])[0]
#         all_emb = np.vstack(df["embedding"])
#         sims = cosine_similarity(all_emb, [q_emb]).flatten()
#         top_idx = sims.argsort()[::-1][:TOP_K]
#         top_df = df.loc[top_idx].copy()
#         if "youtube_link" not in top_df.columns:
#             top_df["youtube_link"] = [None] * len(top_df)
#         context_json = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_json(orient="records")
#         prompt = f"""'I am teaching web development in my Sigma web development course. Here are video subtitle chunks containing video title, video number, start time in seconds, end time in seconds, the text at that time: {top_df[["title", "number", "start", "end", "text"]].to_json(orient="records")}

# Context:
# {context_json}

# User question: "{question}"

# User asked this question related to the video chunks, you have to answer in a human way (dont mention the above format, its just for you) where and how much content is taught in which video (in which video and at what timestamp) and guide the user to go to that particular video. If user asks unrelated question, tell him that you can only answer questions related to the course.
# """
#         used_model, answer_text = inference_with_fallback(prompt)
#         html_snips = []
#         for _, row in top_df.iterrows():
#             yt = row.get("youtube_link") or ""
#             title = row.get("title", "Video")
#             number = row.get("number", "")
#             start = int(row.get("start") or 0)
#             if yt:
#                 link_html = f'<a href="{yt}" target="_blank" rel="noopener noreferrer">Open at {start}s</a>'
#             else:
#                 link_html = f"{start}s"
#             html_snips.append(f"<p><b>{title}</b> (Video {number}) • {link_html}</p>")
#         html_output = f"<div><p>{answer_text}</p><hr><h4>Relevant video chunks:</h4>{''.join(html_snips)}</div>"
#         return jsonify({
#             "response": answer_text,
#             "html_response": html_output,
#             "top_k": min(TOP_K, len(top_df)),
#             "chunks": top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_dict(orient="records"),
#             "used_model": used_model
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ------------------------
# # Entrypoint
# # ------------------------
# if __name__ == "__main__":
#     print("Starting app on http://127.0.0.1:5000")
#     app.run(host="127.0.0.1", port=5000, debug=True)

# ___________________________________________________________________________________________________


# app.py
# Flask app with embedding search + GenAI -> Ollama fallback, STT/TTS frontend,
# and "Download answer as PDF" feature (server-side PDF generation using ReportLab).

# Requirements:
#   pip install flask joblib scikit-learn pandas requests google-genai reportlab

# Run:
#   python app.py
#ssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss
# import os
# import io
# import json
# import joblib
# import textwrap
# import requests
# import numpy as np
# from flask import (
#     Flask,
#     request,
#     jsonify,
#     make_response,
#     render_template_string,
#     send_file,
# )
# from sklearn.metrics.pairwise import cosine_similarity
# import google.genai as genai
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter
# from reportlab.lib.units import inch

# # ------------------------
# # Configuration
# # ------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EMBEDDINGS_FILE = os.path.join(BASE_DIR, "embeddings.joblib")
# LOCAL_EMBED_ENDPOINT = "http://localhost:11434/api/embed"
# OLLAMA_GEN_ENDPOINT = "http://localhost:11434/api/generate"
# GENAI_MODEL = "gemini-2.5-flash"
# OLLAMA_MODEL = "llama3.2"
# TOP_K = 5

# # Put your API key here (development only)
# DIRECT_GENAI_API_KEY = "AIzaSyCCLYhPFsbmjSpfUnBJCPsAKO0MxySkKJk"

# # ------------------------
# # Initialize
# # ------------------------
# app = Flask(__name__)
# client = genai.Client(api_key=DIRECT_GENAI_API_KEY)

# if not os.path.exists(EMBEDDINGS_FILE):
#     raise FileNotFoundError(f"{EMBEDDINGS_FILE} not found. Place embeddings.joblib next to this file.")
# df = joblib.load(EMBEDDINGS_FILE)

# if "embedding" not in df.columns:
#     raise ValueError("embeddings.joblib must contain an 'embedding' column.")
# if "youtube_link" not in df.columns:
#     print("Warning: 'youtube_link' column missing. Links will be None in responses.")

# # ------------------------
# # Frontend HTML (keeps STT/TTS, adds Download PDF button)
# # ------------------------
# INDEX_HTML = '''
# <!doctype html>
# <html lang="en">
# <head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
# <title>Sigma WebDev — Voice Q&A (PDF)</title>
# <style>
# :root{--bg-1:#071124;--bg-2:#0b1728;--accent:#06b6d4;--muted:#9fc5ff}
# *{box-sizing:border-box}html,body{height:100%;margin:0;background:linear-gradient(180deg,var(--bg-2),var(--bg-1));color:#e6eef8;font-family:Inter,system-ui,Segoe UI,Roboto,Arial}
# .wrap{max-width:980px;margin:28px auto;padding:20px}
# .card{background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01));padding:18px;border-radius:12px;box-shadow:0 8px 30px rgba(2,6,23,0.6)}
# .header-row{display:flex;align-items:center;gap:12px}
# h1{margin:0 0 6px;font-size:22px}p.lead{margin:0 0 12px;color:var(--muted)}
# textarea{width:100%;min-height:88px;padding:12px;border-radius:8px;border:1px solid rgba(255,255,255,0.04);background:transparent;color:inherit;resize:vertical}
# .controls{display:flex;gap:8px;margin-top:10px;align-items:center}
# button{padding:9px 12px;border-radius:10px;border:none;cursor:pointer;font-weight:700}
# .btn-primary{background:linear-gradient(90deg,var(--accent),#04a7c9);color:#022}
# .btn-ghost{background:transparent;border:1px solid rgba(255,255,255,0.04);color:var(--muted)}
# .mic-btn{width:44px;height:44px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:700}
# .mic-listening{box-shadow:0 0 18px rgba(6,182,212,0.25);transform:scale(1.03)}
# .spinner{margin-left:8px;color:var(--muted)}
# .results{margin-top:18px;display:flex;flex-direction:column;gap:12px}
# .alert{background:#3b2b1a;color:#fff;padding:8px;border-radius:8px;margin-bottom:8px}
# .answer{white-space:pre-wrap;padding:12px;border-radius:10px}
# .chunk{padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
# a.yt{color:var(--accent);text-decoration:none;font-weight:600}
# footer{margin-top:12px;color:var(--muted);font-size:13px}
# kbd{background:#0b1220;border-radius:6px;padding:2px 6px}
# .small{font-size:13px;color:var(--muted)}
# </style>
# </head>
# <body>
# <div class="wrap">
#   <div id="fallbackBanner" style="display:none" class="alert"></div>

#   <div class="card">
#     <div class="header-row">
#       <div style="flex:1">
#         <h1>Sigma WebDev — Voice Q&A (PDF)</h1>
#         <p class="lead">Ask by typing or speaking. You can download the answer as PDF.</p>
#       </div>
#       <div style="text-align:right">
#         <div class="small">Speech: <span id="sttSupport">...</span></div>
#         <div class="small">TTS: <span id="ttsSupport">...</span></div>
#       </div>
#     </div>

#     <textarea id="question" placeholder="Type a question or use the microphone..."></textarea>

#     <div class="controls">
#       <button id="askBtn" class="btn-primary">Ask</button>
#       <button id="downloadBtn" class="btn-ghost" style="display:none">Download PDF</button>
#       <button id="clearBtn" class="btn-ghost">Clear</button>
#       <button id="micBtn" class="mic-btn btn-ghost" title="Speak" aria-pressed="false">🎤</button>
#       <label class="small"><input id="ttsToggle" type="checkbox" checked/> Speak answer</label>
#       <button id="playBtn" class="btn-ghost" style="display:none">🔊 Play</button>
#       <div id="spinner" class="spinner" style="display:none">Thinking…</div>
#     </div>

#     <div style="margin-top:10px;color:var(--muted)">Tip: <kbd>Ctrl</kbd>+<kbd>Enter</kbd> to submit. Use microphone for quick voice input.</div>
#   </div>

#   <div id="results" class="results" hidden>
#     <div class="card">
#       <h3>Answer</h3>
#       <div id="answer" class="answer"></div>
#     </div>

#     <div id="chunksCard" class="card" hidden>
#       <h3>Relevant video chunks</h3>
#       <div id="chunksList"></div>
#     </div>
#   </div>

#   <footer>Uses local embedding server + GenAI/Ollama. Make sure <code>embeddings.joblib</code> is present.</footer>
# </div>

# <script>
# const askBtn = document.getElementById('askBtn');
# const downloadBtn = document.getElementById('downloadBtn');
# const clearBtn = document.getElementById('clearBtn');
# const micBtn = document.getElementById('micBtn');
# const qEl = document.getElementById('question');
# const spinner = document.getElementById('spinner');
# const results = document.getElementById('results');
# const answerDiv = document.getElementById('answer');
# const chunksCard = document.getElementById('chunksCard');
# const chunksList = document.getElementById('chunksList');
# const fallbackBanner = document.getElementById('fallbackBanner');
# const ttsToggle = document.getElementById('ttsToggle');
# const playBtn = document.getElementById('playBtn');
# const sttSupportEl = document.getElementById('sttSupport');
# const ttsSupportEl = document.getElementById('ttsSupport');

# let recognition = null;
# let isListening = false;
# let lastAnswerText = "";
# let usedModel = null;

# const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;
# if (SpeechRecognition) {
#   sttSupportEl.textContent = 'Available';
#   recognition = new SpeechRecognition();
#   recognition.lang = 'en-US';
#   recognition.interimResults = false;
#   recognition.maxAlternatives = 1;

#   recognition.addEventListener('result', (e) => {
#     const text = Array.from(e.results).map(r => r[0].transcript).join('');
#     qEl.value = (qEl.value ? qEl.value + ' ' : '') + text;
#   });

#   recognition.addEventListener('end', () => {
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#     isListening = false;
#   });

#   recognition.addEventListener('error', (ev) => {
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#     isListening = false;
#     alert('Speech recognition error: ' + ev.error);
#   });
# } else {
#   sttSupportEl.textContent = 'Not supported';
#   micBtn.title = 'Speech recognition not supported';
#   micBtn.disabled = true;
# }

# const ttsSupported = ('speechSynthesis' in window);
# ttsSupportEl.textContent = ttsSupported ? 'Available' : 'Not supported';
# if (!ttsSupported) {
#   ttsToggle.disabled = true;
#   playBtn.style.display = 'none';
# }

# function speak(text) {
#   if (!ttsSupported) return;
#   if (!text) return;
#   window.speechSynthesis.cancel();
#   const utter = new SpeechSynthesisUtterance(text);
#   utter.rate = 1.0;
#   utter.pitch = 1.0;
#   const voices = window.speechSynthesis.getVoices();
#   if (voices && voices.length) {
#     const v = voices.find(v => v.lang && v.lang.startsWith('en')) || voices[0];
#     if (v) utter.voice = v;
#   }
#   utter.onend = () => {
#     playBtn.textContent = '🔊 Play';
#   };
#   window.speechSynthesis.speak(utter);
#   playBtn.textContent = '⏸️ Stop';
# }

# micBtn.addEventListener('click', () => {
#   if (!recognition) return;
#   if (!isListening) {
#     try {
#       recognition.start();
#       isListening = true;
#       micBtn.classList.add('mic-listening');
#       micBtn.setAttribute('aria-pressed', 'true');
#     } catch (e) {}
#   } else {
#     recognition.stop();
#     isListening = false;
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#   }
# });

# playBtn.addEventListener('click', () => {
#   if (!ttsSupported) return;
#   if (window.speechSynthesis.speaking) {
#     window.speechSynthesis.cancel();
#     playBtn.textContent = '🔊 Play';
#   } else {
#     speak(lastAnswerText);
#   }
# });

# function setLoading(on){
#   spinner.style.display = on ? 'inline' : 'none';
#   askBtn.disabled = on;
#   clearBtn.disabled = on;
#   micBtn.disabled = on || !recognition;
#   downloadBtn.disabled = on;
# }

# function formatSec(s){
#   s = Number(s)||0; const h=Math.floor(s/3600); const m=Math.floor((s%3600)/60); const sec=Math.floor(s%60);
#   if(h>0) return `${h}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; return `${m}:${String(sec).padStart(2,'0')}`;
# }

# async function ask(){
#   const q = qEl.value.trim(); if(!q) return alert('Please type or speak a question first.');
#   setLoading(true); results.hidden=true; answerDiv.textContent=''; chunksList.innerHTML=''; chunksCard.hidden=true; fallbackBanner.style.display='none';
#   downloadBtn.style.display = 'none';
#   try{
#     const res = await fetch('/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
#     const data = await res.json();
#     if(!res.ok){
#       answerDiv.textContent = data.error || 'Server error';
#       results.hidden = false;
#       return;
#     }
#     usedModel = data.used_model || null;
#     if(usedModel && usedModel.toLowerCase().includes('ollama')){
#       fallbackBanner.style.display='block';
#       fallbackBanner.textContent = '⚠️ Gemini unavailable — answered by Ollama (local).';
#     } else if (usedModel === 'none'){
#       fallbackBanner.style.display='block';
#       fallbackBanner.textContent = '⚠️ Both Gemini and Ollama failed. See details in response.';
#     } else {
#       fallbackBanner.style.display='none';
#     }
#     lastAnswerText = data.response || '';
#     answerDiv.innerHTML = data.html_response || (data.response || '');
#     if (ttsSupported && ttsToggle.checked && lastAnswerText){
#       playBtn.style.display = 'inline-block';
#       speak(lastAnswerText);
#     } else {
#       playBtn.style.display = 'none';
#     }
#     const chunks = data.chunks || [];
#     if(chunks.length>0){
#       chunksCard.hidden=false;
#       chunksList.innerHTML='';
#       for(const c of chunks){
#         const el = document.createElement('div'); el.className='chunk';
#         const left = document.createElement('div'); left.style.flex='1 1 auto';
#         const meta = document.createElement('div'); meta.style.fontSize='13px'; meta.style.color='#9fc5ff';
#         meta.textContent = `${c.title || 'Video'} ${c.number || ''} • ${formatSec(c.start)} - ${formatSec(c.end)}`;
#         const txt = document.createElement('div'); txt.textContent = c.text || '';
#         left.appendChild(meta); left.appendChild(txt);
#         const right = document.createElement('div');
#         const a = document.createElement('a'); a.className='yt'; a.target='_blank'; a.rel='noopener noreferrer';
#         a.href = c.youtube_link || '#'; a.textContent = 'Open timestamp';
#         right.appendChild(a);
#         el.appendChild(left); el.appendChild(right);
#         chunksList.appendChild(el);
#       }
#       // show download button once we have an answer and chunks
#       downloadBtn.style.display = 'inline-block';
#     }
#     results.hidden = false;
#   } catch(err){
#     answerDiv.textContent = 'Network/server error: ' + (err.message || err);
#     results.hidden = false;
#   } finally {
#     setLoading(false);
#   }
# }

# async function downloadPDF(){
#   const q = qEl.value.trim(); if(!q) return alert('No question to download.');
#   setLoading(true);
#   try{
#     const res = await fetch('/download', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
#     if(!res.ok){
#       const err = await res.json().catch(()=>({error:'download failed'}));
#       alert('PDF generation failed: ' + (err.error || JSON.stringify(err)));
#       return;
#     }
#     const blob = await res.blob();
#     const url = URL.createObjectURL(blob);
#     const a = document.createElement('a');
#     a.href = url;
#     a.download = 'sigma_answer.pdf';
#     document.body.appendChild(a);
#     a.click();
#     a.remove();
#     URL.revokeObjectURL(url);
#   } catch(e){
#     alert('Download failed: ' + e.message);
#   } finally {
#     setLoading(false);
#   }
# }

# askBtn.addEventListener('click', ask);
# downloadBtn.addEventListener('click', downloadPDF);
# clearBtn.addEventListener('click', ()=>{ qEl.value=''; results.hidden=true; chunksList.innerHTML=''; lastAnswerText=''; playBtn.style.display='none'; downloadBtn.style.display='none'; });
# qEl.addEventListener('keydown', (e)=>{ if((e.ctrlKey||e.metaKey) && e.key==='Enter') ask(); });
# window.addEventListener('load', ()=> qEl.focus());
# </script>
# </body>
# </html>
# '''

# # ------------------------
# # Backend helpers
# # ------------------------
# def create_embedding_local(text_list):
#     try:
#         r = requests.post(LOCAL_EMBED_ENDPOINT, json={"model": "bge-m3", "input": text_list}, timeout=30)
#         r.raise_for_status()
#         res = r.json()
#     except requests.exceptions.RequestException as exc:
#         raise RuntimeError(f"Local embedder error: {exc}")
#     if "embeddings" in res:
#         return res["embeddings"]
#     if "data" in res and isinstance(res["data"], list):
#         return [item.get("embedding") for item in res["data"]]
#     raise ValueError("Unexpected embedding response structure from local embedder")

# def is_genai_response_ok(resp):
#     try:
#         if hasattr(resp, "text"):
#             txt = getattr(resp, "text")
#             if txt and str(txt).strip():
#                 return True, str(txt), None
#             return False, None, "empty_text"
#     except Exception:
#         pass
#     if isinstance(resp, dict):
#         if resp.get("error") or resp.get("errors"):
#             return False, None, json.dumps(resp.get("error") or resp.get("errors"))
#         if "candidates" in resp and isinstance(resp["candidates"], list) and resp["candidates"]:
#             cand = resp["candidates"][0]
#             if isinstance(cand, dict):
#                 if "text" in cand and cand["text"]:
#                     return True, str(cand["text"]), None
#                 if "content" in cand and isinstance(cand["content"], list):
#                     for piece in cand["content"]:
#                         if isinstance(piece, dict) and "text" in piece and piece["text"]:
#                             return True, str(piece["text"]), None
#         for k in ("output", "response", "message", "result"):
#             if k in resp and resp[k]:
#                 return True, str(resp[k]), None
#         return False, None, "unknown_dict_shape"
#     return False, None, "unknown_response_type"

# def genai_call(prompt):
#     try:
#         resp = client.models.generate_content(model=GENAI_MODEL, contents=prompt)
#     except Exception as e:
#         raise RuntimeError(f"GenAI SDK raised: {e}")
#     ok, text, err = is_genai_response_ok(resp)
#     if ok:
#         return "genai", text
#     raise RuntimeError(f"GenAI returned invalid/empty response ({err})")

# def ollama_call(prompt):
#     try:
#         r = requests.post(OLLAMA_GEN_ENDPOINT, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=60)
#         r.raise_for_status()
#         data = r.json()
#     except requests.exceptions.RequestException as exc:
#         raise RuntimeError(f"Ollama call failed: {exc}")
#     if isinstance(data, dict):
#         for k in ("response", "text", "output"):
#             if k in data and data[k]:
#                 return "ollama", data[k]
#         if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
#             ch = data["choices"][0]
#             if isinstance(ch, dict):
#                 if "message" in ch and isinstance(ch["message"], dict) and "content" in ch["message"]:
#                     return "ollama", ch["message"]["content"]
#                 if "text" in ch:
#                     return "ollama", ch["text"]
#     return "ollama", json.dumps(data)

# def inference_with_fallback(prompt):
#     try:
#         used, text = genai_call(prompt)
#         return used, text
#     except Exception as gen_err:
#         print(f"[WARN] GenAI failed: {gen_err}. Falling back to Ollama...")
#         try:
#             used2, text2 = ollama_call(prompt)
#             return used2, text2
#         except Exception as oll_err:
#             err_msg = f"GenAI error: {gen_err} | Ollama error: {oll_err}"
#             print(f"[ERROR] {err_msg}")
#             return "none", f"Both GenAI and Ollama failed. Details: {err_msg}"

# # ------------------------
# # PDF generation helper
# # ------------------------
# def generate_pdf_bytes(question, answer_text, chunks, used_model):
#     """
#     Create a PDF with the question, answer_text, and a list of chunks.
#     Returns BytesIO ready to send.
#     """
#     buffer = io.BytesIO()
#     c = canvas.Canvas(buffer, pagesize=letter)
#     width, height = letter
#     margin = 0.75 * inch
#     max_width = width - 2 * margin
#     x = margin
#     y = height - margin

#     # Title
#     c.setFont("Helvetica-Bold", 14)
#     c.drawString(x, y, "Sigma WebDev — Answer")
#     y -= 18

#     # metadata: model used
#     c.setFont("Helvetica", 9)
#     c.drawString(x, y, f"Used model: {used_model}")
#     y -= 14

#     # Question
#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(x, y, "Question:")
#     y -= 14
#     c.setFont("Helvetica", 10)
#     for line in textwrap.wrap(question, width=100):
#         c.drawString(x, y, line)
#         y -= 12
#         if y < margin:
#             c.showPage()
#             y = height - margin

#     y -= 6
#     # Answer
#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(x, y, "Answer:")
#     y -= 14
#     c.setFont("Helvetica", 10)
#     for paragraph in str(answer_text).split("\n"):
#         wrapped = textwrap.wrap(paragraph, width=100)
#         if not wrapped:
#             c.drawString(x, y, "")
#             y -= 12
#         for line in wrapped:
#             c.drawString(x, y, line)
#             y -= 12
#             if y < margin:
#                 c.showPage()
#                 y = height - margin

#     y -= 8
#     # Relevant chunks
#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(x, y, "Relevant video chunks:")
#     y -= 14
#     c.setFont("Helvetica", 10)
#     for chk in chunks:
#         title = chk.get("title", "Video")
#         number = chk.get("number", "")
#         start = int(chk.get("start") or 0)
#         end = int(chk.get("end") or 0)
#         youtube_link = chk.get("youtube_link") or ""
#         # line for metadata
#         meta_line = f"{title} (Video {number}) [{start}s - {end}s]"
#         for line in textwrap.wrap(meta_line, width=100):
#             c.drawString(x, y, line)
#             y -= 12
#             if y < margin:
#                 c.showPage()
#                 y = height - margin
#         # text chunk (smaller indent)
#         chunk_text = chk.get("text", "")
#         wrapped_chunk = textwrap.wrap(chunk_text, width=110)
#         for line in wrapped_chunk:
#             c.drawString(x + 12, y, line)
#             y -= 11
#             if y < margin:
#                 c.showPage()
#                 y = height - margin
#         # youtube link (on its own)
#         if youtube_link:
#             link_line = f"Link: {youtube_link}"
#             for line in textwrap.wrap(link_line, width=100):
#                 c.drawString(x + 12, y, line)
#                 y -= 11
#                 if y < margin:
#                     c.showPage()
#                     y = height - margin
#         y -= 8

#     c.showPage()
#     c.save()
#     buffer.seek(0)
#     return buffer

# # ------------------------
# # Routes
# # ------------------------
# @app.route("/", methods=["GET"])
# def index():
#     resp = make_response(render_template_string(INDEX_HTML))
#     resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     resp.headers["Pragma"] = "no-cache"
#     resp.headers["Expires"] = "0"
#     return resp

# @app.route("/ask", methods=["POST"])
# def ask():
#     payload = request.get_json(force=True)
#     question = payload.get("question", "").strip()
#     if not question:
#         return jsonify({"error": "question required"}), 400
#     try:
#         q_emb = create_embedding_local([question])[0]
#         all_emb = np.vstack(df["embedding"])
#         sims = cosine_similarity(all_emb, [q_emb]).flatten()
#         top_idx = sims.argsort()[::-1][:TOP_K]
#         top_df = df.loc[top_idx].copy()
#         if "youtube_link" not in top_df.columns:
#             top_df["youtube_link"] = [None] * len(top_df)
#         context_json = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_json(orient="records")
#         prompt = f"""I am teaching web development in my Sigma web development course. Use the following chunks to answer the user's question. Include clickable youtube links when present.

# Context:
# {context_json}

# User question: "{question}"

# Answer naturally and concisely, and when referencing a chunk include its title and youtube link or timestamp.
# """
#         used_model, answer_text = inference_with_fallback(prompt)
#         html_snips = []
#         for _, row in top_df.iterrows():
#             yt = row.get("youtube_link") or ""
#             title = row.get("title", "Video")
#             number = row.get("number", "")
#             start = int(row.get("start") or 0)
#             if yt:
#                 link_html = f'<a href="{yt}" target="_blank" rel="noopener noreferrer">Open at {start}s</a>'
#             else:
#                 link_html = f"{start}s"
#             html_snips.append(f"<p><b>{title}</b> (Video {number}) • {link_html}</p>")
#         html_output = f"<div><p>{answer_text}</p><hr><h4>Relevant video chunks:</h4>{''.join(html_snips)}</div>"
#         return jsonify({
#             "response": answer_text,
#             "html_response": html_output,
#             "top_k": min(TOP_K, len(top_df)),
#             "chunks": top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_dict(orient="records"),
#             "used_model": used_model
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route("/download", methods=["POST"])
# def download():
#     """
#     Re-run the retrieval + inference and return a PDF file with the answer and chunks.
#     Request body: {"question": "..."}
#     """
#     payload = request.get_json(force=True)
#     question = (payload.get("question") or "").strip()
#     if not question:
#         return jsonify({"error": "question required"}), 400
#     try:
#         # reuse same flow as /ask
#         q_emb = create_embedding_local([question])[0]
#         all_emb = np.vstack(df["embedding"])
#         sims = cosine_similarity(all_emb, [q_emb]).flatten()
#         top_idx = sims.argsort()[::-1][:TOP_K]
#         top_df = df.loc[top_idx].copy()
#         if "youtube_link" not in top_df.columns:
#             top_df["youtube_link"] = [None] * len(top_df)
#         context_json = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_json(orient="records")
#         prompt = f"""I am teaching web development in my Sigma web development course. Use the following chunks to answer the user's question. Include clickable youtube links when present.

# Context:
# {context_json}

# User question: "{question}"

# Answer naturally and concisely, and when referencing a chunk include its title and youtube link or timestamp.
# """
#         used_model, answer_text = inference_with_fallback(prompt)
#         chunks = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_dict(orient="records")
#         pdf_io = generate_pdf_bytes(question, answer_text, chunks, used_model)
#         # send as downloadable file
#         return send_file(
#             pdf_io,
#             as_attachment=True,
#             download_name="sigma_answer.pdf",
#             mimetype="application/pdf"
#         )
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ------------------------
# # Entrypoint
# # ------------------------
# if __name__ == "__main__":
#     print("Starting app on http://127.0.0.1:5000")
#     app.run(host="127.0.0.1", port=5000, debug=True)
#ssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss



#__________________________________________________________________________________________________

# app.py
# Flask app with embedding search + GenAI -> Ollama fallback,
# STT/TTS frontend, PDF download, and Dark/Light mode toggle.

# Requirements:
#   pip install flask joblib scikit-learn pandas requests google-genai reportlab

# Run:
#   python app.py

# import os
# import io
# import json
# import joblib
# import textwrap
# import requests
# import numpy as np
# from flask import (
#     Flask,
#     request,
#     jsonify,
#     make_response,
#     render_template_string,
#     send_file,
# )
# from sklearn.metrics.pairwise import cosine_similarity
# import google.genai as genai
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter
# from reportlab.lib.units import inch

# # ------------------------
# # Configuration
# # ------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EMBEDDINGS_FILE = os.path.join(BASE_DIR, "embeddings.joblib")
# LOCAL_EMBED_ENDPOINT = "http://localhost:11434/api/embed"
# OLLAMA_GEN_ENDPOINT = "http://localhost:11434/api/generate"
# GENAI_MODEL = "gemini-2.5-flash"
# OLLAMA_MODEL = "llama3.2"
# TOP_K = 5

# # Put your API key here (development only)
# DIRECT_GENAI_API_KEY = "2wqAIzaSyCCLYhPFsbmjSpfUnBJCPsAKO0MxySkKJk"

# # ------------------------
# # Initialize
# # ------------------------
# app = Flask(__name__)
# client = genai.Client(api_key=DIRECT_GENAI_API_KEY)

# if not os.path.exists(EMBEDDINGS_FILE):
#     raise FileNotFoundError(f"{EMBEDDINGS_FILE} not found. Place embeddings.joblib next to this file.")
# df = joblib.load(EMBEDDINGS_FILE)

# if "embedding" not in df.columns:
#     raise ValueError("embeddings.joblib must contain an 'embedding' column.")
# if "youtube_link" not in df.columns:
#     print("Warning: 'youtube_link' column missing. Links will be None in responses.")

# # ------------------------
# # Frontend HTML (Dark/Light toggle + STT/TTS + PDF)
# # ------------------------
# INDEX_HTML = '''
# <!doctype html>
# <html lang="en">
# <head>
# <meta charset="utf-8"/>
# <meta name="viewport" content="width=device-width,initial-scale=1"/>
# <title>Sigma WebDev — Voice Q&A</title>
# <style>
# :root{
#   --bg: #071124;
#   --panel: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
#   --text: #e6eef8;
#   --muted: #9fc5ff;
#   --accent: #06b6d4;
#   --card-shadow: 0 8px 30px rgba(2,6,23,0.6);
#   --radius: 12px;
#   --max-width: 1100px;
#   --ui-gap: 14px;
#   --font-sans: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
#   --header-bg: rgba(7,17,36,0.85);
# }

# /* Light mode variables (applied when .light is present on html and body) */
# html.light, body.light {
#   --bg: #f6f8fb;
#   --panel: linear-gradient(180deg, #ffffff, #f7fbff);
#   --text: #0b1926;
#   --muted: #41678a;
#   --accent: #007ea7;
#   --card-shadow: 0 8px 30px rgba(10,20,30,0.06);
#   --header-bg: rgba(255,255,255,0.92);
# }

# /* Base styles: explicitly set background-color (not only background-image),
#    and ensure html and body both pick up the variable. */
# *{box-sizing:border-box}
# html,body{
#   height:100%;
#   margin:0;
#   background-color:var(--bg); /* explicit color to avoid transparent reveal */
#   background-image: none;
#   color:var(--text);
#   font-family:var(--font-sans);
#   -webkit-font-smoothing:antialiased;
#   -moz-osx-font-smoothing:grayscale;
# }
# .container{max-width:var(--max-width);margin:32px auto;padding:20px}
# .header{
#   display:flex;
#   align-items:center;
#   justify-content:space-between;
#   gap:12px;
#   margin-bottom:18px;

#   /* sticky header */
#   position:sticky;
#   top:0;
#   z-index:1000;
#   padding:12px 20px;
#   /* reduce corner rounding so it won't reveal background edges when sticky */
#   border-radius:0 0 var(--radius) var(--radius);
#   background:var(--header-bg);
#   backdrop-filter: blur(8px);
#   -webkit-backdrop-filter: blur(8px);
#   box-shadow: 0 6px 18px rgba(0,0,0,0.12);
# }

# .title {display:flex;flex-direction:column;gap:6px}
# h1{margin:0;font-size:22px}
# .lead{margin:0;color:var(--muted);font-size:14px}

# .card{background:var(--panel);padding:18px;border-radius:var(--radius);box-shadow:var(--card-shadow);margin-bottom:var(--ui-gap)}
# .row{display:flex;gap:12px;align-items:center}
# .controls{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}
# textarea{width:100%;min-height:110px;padding:14px;border-radius:10px;border:1px solid rgba(255,255,255,0.04);background:transparent;color:inherit;resize:vertical;font-size:15px}
# button{padding:10px 14px;border-radius:10px;border:none;cursor:pointer;font-weight:700}
# .btn-primary{background:linear-gradient(90deg,var(--accent),#04a7c9);color:var(--bg);box-shadow:0 6px 18px rgba(2,6,23,0.15)}
# .btn-ghost{background:transparent;border:1px solid rgba(255,255,255,0.06);color:var(--muted)}
# .icon-btn{width:44px;height:44px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:700;border:1px solid rgba(255,255,255,0.04);background:transparent}
# .mic-listening{box-shadow:0 0 18px rgba(6,182,212,0.25);transform:scale(1.03)}
# .spinner{margin-left:8px;color:var(--muted)}
# .results{margin-top:18px;display:flex;flex-direction:column;gap:12px}
# .answer{white-space:pre-wrap;padding:12px;border-radius:10px;font-size:15px;line-height:1.5;background:rgba(0,0,0,0.02)}
# .chunk{padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.03);display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
# .meta{font-size:13px;color:var(--muted)}
# .footer{margin-top:10px;color:var(--muted);font-size:13px}

# .toggle {
#   display:inline-flex;align-items:center;gap:8px;background:transparent;border:1px solid rgba(255,255,255,0.04);padding:6px 10px;border-radius:999px;color:var(--muted)
# }
# kbd{background:rgba(0,0,0,0.12);padding:3px 6px;border-radius:6px;font-size:12px}

# /* readability tweaks */
# @media (min-width:1000px){
#   textarea{font-size:16px}
#   .answer{font-size:16px}
# }
# </style>
# </head>
# <body>
# <div class="container">
#   <div class="header">
#     <div class="title">
#       <h1>Sigma WebDev — Voice Q&A</h1>
#       <div class="lead">Ask about the course by typing or speaking. Click to download a clean PDF of answers.</div>
#     </div>

#     <div class="row">
#       <div class="toggle" id="modeToggle" title="Toggle dark / light mode">
#         <span id="modeIcon">🌙</span>
#         <strong id="modeLabel">Dark</strong>
#       </div>
#     </div>
#   </div>

#   <div class="card">
#     <div style="display:flex;gap:14px;align-items:flex-start;flex-direction:column">
#       <textarea id="question" placeholder="Type a question or use the microphone..."></textarea>

#       <div class="controls">
#         <button id="askBtn" class="btn-primary">Ask</button>
#         <button id="downloadBtn" class="btn-ghost" style="display:none">Download PDF</button>
#         <button id="clearBtn" class="btn-ghost">Clear</button>

#         <button id="micBtn" class="icon-btn" title="Speak" aria-pressed="false">🎤</button>

#         <label style="display:inline-flex;align-items:center;gap:8px;color:var(--muted)">
#           <input id="ttsToggle" type="checkbox" checked/> <span style="font-size:13px">Speak answer</span>
#         </label>

#         <button id="playBtn" class="btn-ghost" style="display:none">🔊 Play</button>

#         <div id="spinner" class="spinner" style="display:none">Thinking…</div>

#         <div style="margin-left:auto;color:var(--muted);font-size:13px">
#           Tip: <kbd>Ctrl</kbd>+<kbd>Enter</kbd> to submit.
#         </div>
#       </div>
#     </div>
#   </div>

#   <div id="results" class="results" hidden>
#     <div class="card">
#       <h3 style="margin-top:0">Answer</h3>
#       <div id="answer" class="answer"></div>
#     </div>

#     <div id="chunksCard" class="card" hidden>
#       <h3 style="margin-top:0">Relevant video chunks</h3>
#       <div id="chunksList"></div>
#     </div>
#   </div>

#   <div class="footer">Uses local embedding server + GenAI/Ollama. Make sure <code>embeddings.joblib</code> is present.</div>
# </div>

# <script>
# /* Robust theme application: set class on BOTH html and body */
# const modeToggle = document.getElementById('modeToggle');
# const modeIcon = document.getElementById('modeIcon');
# const modeLabel = document.getElementById('modeLabel');

# function applyMode(mode){
#   mode = (mode === 'light') ? 'light' : 'dark';
#   if(mode === 'light'){
#     document.documentElement.classList.add('light');
#     document.body.classList.add('light');
#     modeIcon.textContent = '☀️';
#     modeLabel.textContent = 'Light';
#   } else {
#     document.documentElement.classList.remove('light');
#     document.body.classList.remove('light');
#     modeIcon.textContent = '🌙';
#     modeLabel.textContent = 'Dark';
#   }
#   localStorage.setItem('sigma_mode', mode);
# }

# /* apply on initial load and pageshow (handles bfcache) */
# document.addEventListener('DOMContentLoaded', function(){
#   const saved = localStorage.getItem('sigma_mode') || 'dark';
#   applyMode(saved);
# });
# window.addEventListener('pageshow', () => {
#   const saved = localStorage.getItem('sigma_mode') || 'dark';
#   applyMode(saved);
# });
# modeToggle.addEventListener('click', ()=>{
#   const current = document.documentElement.classList.contains('light') ? 'light' : 'dark';
#   applyMode(current === 'light' ? 'dark' : 'light');
# });

# /* ===== Rest of frontend logic (STT/TTS, ask, download) — unchanged ===== */
# const askBtn = document.getElementById('askBtn');
# const downloadBtn = document.getElementById('downloadBtn');
# const clearBtn = document.getElementById('clearBtn');
# const micBtn = document.getElementById('micBtn');
# const qEl = document.getElementById('question');
# const spinner = document.getElementById('spinner');
# const results = document.getElementById('results');
# const answerDiv = document.getElementById('answer');
# const chunksCard = document.getElementById('chunksCard');
# const chunksList = document.getElementById('chunksList');
# const ttsToggle = document.getElementById('ttsToggle');
# const playBtn = document.getElementById('playBtn');

# let recognition = null;
# let isListening = false;
# let lastAnswerText = "";
# let usedModel = null;

# /* Speech Recognition */
# const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;
# if (SpeechRecognition) {
#   recognition = new SpeechRecognition();
#   recognition.lang = 'en-US';
#   recognition.interimResults = false;
#   recognition.maxAlternatives = 1;
#   recognition.addEventListener('result', (e) => {
#     const text = Array.from(e.results).map(r => r[0].transcript).join('');
#     qEl.value = (qEl.value ? qEl.value + ' ' : '') + text;
#   });
#   recognition.addEventListener('end', () => {
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#     isListening = false;
#   });
#   recognition.addEventListener('error', (ev) => {
#     micBtn.classList.remove('mic-listening');
#     micBtn.setAttribute('aria-pressed', 'false');
#     isListening = false;
#     alert('Speech recognition error: ' + ev.error);
#   });
# } else {
#   micBtn.disabled = true;
#   micBtn.title = 'Speech recognition not supported in this browser';
# }

# /* TTS: browser speechSynthesis */
# const ttsSupported = ('speechSynthesis' in window);
# function speak(text) {
#   if (!ttsSupported) return;
#   if (!text) return;
#   window.speechSynthesis.cancel();
#   const utter = new SpeechSynthesisUtterance(text);
#   utter.rate = 1.0; utter.pitch = 1.0;
#   const voices = window.speechSynthesis.getVoices();
#   if (voices && voices.length) {
#     const v = voices.find(v => v.lang && v.lang.startsWith('en')) || voices[0];
#     if (v) utter.voice = v;
#   }
#   utter.onend = () => { playBtn.textContent = '🔊 Play'; };
#   window.speechSynthesis.speak(utter);
#   playBtn.textContent = '⏸️ Stop';
# }

# /* Helpers and actions */
# function setLoading(on){
#   spinner.style.display = on ? 'inline' : 'none';
#   askBtn.disabled = on;
#   clearBtn.disabled = on;
#   micBtn.disabled = on || !recognition;
#   downloadBtn.disabled = on;
# }
# function formatSec(s){
#   s = Number(s)||0; const h=Math.floor(s/3600); const m=Math.floor((s%3600)/60); const sec=Math.floor(s%60);
#   if(h>0) return `${h}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; return `${m}:${String(sec).padStart(2,'0')}`;
# }

# async function ask(){
#   const q = qEl.value.trim(); if(!q) return alert('Please type or speak a question first.');
#   setLoading(true); results.hidden=true; answerDiv.textContent=''; chunksList.innerHTML=''; chunksCard.hidden=true; downloadBtn.style.display='none';
#   try{
#     const res = await fetch('/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
#     const data = await res.json();
#     if(!res.ok){
#       answerDiv.textContent = data.error || 'Server error';
#       results.hidden = false;
#       return;
#     }
#     usedModel = data.used_model || null;
#     lastAnswerText = data.response || '';
#     answerDiv.innerHTML = data.html_response || (data.response || '');
#     if (ttsSupported && ttsToggle.checked && lastAnswerText){
#       playBtn.style.display = 'inline-block';
#       speak(lastAnswerText);
#     } else {
#       playBtn.style.display = 'none';
#     }
#     const chunks = data.chunks || [];
#     if(chunks.length>0){
#       chunksCard.hidden=false;
#       chunksList.innerHTML='';
#       for(const c of chunks){
#         const el = document.createElement('div'); el.className='chunk';
#         const left = document.createElement('div'); left.style.flex='1 1 auto';
#         const meta = document.createElement('div'); meta.className='meta';
#         meta.textContent = `${c.title || 'Video'} ${c.number || ''} • ${formatSec(c.start)} - ${formatSec(c.end)}`;
#         const txt = document.createElement('div'); txt.textContent = c.text || '';
#         left.appendChild(meta); left.appendChild(txt);
#         const right = document.createElement('div');
#         const a = document.createElement('a'); a.className='yt'; a.target='_blank'; a.rel='noopener noreferrer';
#         a.href = c.youtube_link || '#'; a.textContent = 'Open timestamp';
#         right.appendChild(a);
#         el.appendChild(left); el.appendChild(right);
#         chunksList.appendChild(el);
#       }
#       downloadBtn.style.display = 'inline-block';
#     }
#     results.hidden = false;
#   } catch(err){
#     answerDiv.textContent = 'Network/server error: ' + (err.message || err);
#     results.hidden = false;
#   } finally {
#     setLoading(false);
#   }
# }

# async function downloadPDF(){
#   const q = qEl.value.trim(); if(!q) return alert('No question to download.');
#   setLoading(true);
#   try{
#     const res = await fetch('/download', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})});
#     if(!res.ok){
#       const err = await res.json().catch(()=>({error:'download failed'}));
#       alert('PDF generation failed: ' + (err.error || JSON.stringify(err)));
#       return;
#     }
#     const blob = await res.blob();
#     const url = URL.createObjectURL(blob);
#     const a = document.createElement('a');
#     a.href = url;
#     a.download = 'sigma_answer.pdf';
#     document.body.appendChild(a);
#     a.click();
#     a.remove();
#     URL.revokeObjectURL(url);
#   } catch(e){
#     alert('Download failed: ' + e.message);
#   } finally {
#     setLoading(false);
#   }
# }

# /* Wiring */
# askBtn.addEventListener('click', ask);
# downloadBtn.addEventListener('click', downloadPDF);
# clearBtn.addEventListener('click', ()=>{ qEl.value=''; results.hidden=true; chunksList.innerHTML=''; lastAnswerText=''; playBtn.style.display='none'; downloadBtn.style.display='none'; });
# micBtn.addEventListener('click', ()=>{
#   if (!recognition) return;
#   if (!isListening) {
#     try { recognition.start(); isListening = true; micBtn.classList.add('mic-listening'); micBtn.setAttribute('aria-pressed','true'); } catch(e){}
#   } else {
#     recognition.stop(); isListening = false; micBtn.classList.remove('mic-listening'); micBtn.setAttribute('aria-pressed','false');
#   }
# });
# playBtn.addEventListener('click', ()=>{ if (!ttsSupported) return; if (window.speechSynthesis.speaking){ window.speechSynthesis.cancel(); playBtn.textContent='🔊 Play'; } else { speak(lastAnswerText); } });
# qEl.addEventListener('keydown', (e)=>{ if((e.ctrlKey||e.metaKey) && e.key==='Enter') ask(); });
# window.addEventListener('load', ()=> qEl.focus());
# </script>
# </body>
# </html>
# '''

# # ------------------------
# # Backend helpers
# # ------------------------
# def create_embedding_local(text_list):
#     try:
#         r = requests.post(LOCAL_EMBED_ENDPOINT, json={"model": "bge-m3", "input": text_list}, timeout=30)
#         r.raise_for_status()
#         res = r.json()
#     except requests.exceptions.RequestException as exc:
#         raise RuntimeError(f"Local embedder error: {exc}")
#     if "embeddings" in res:
#         return res["embeddings"]
#     if "data" in res and isinstance(res["data"], list):
#         return [item.get("embedding") for item in res["data"]]
#     raise ValueError("Unexpected embedding response structure from local embedder")

# def is_genai_response_ok(resp):
#     try:
#         if hasattr(resp, "text"):
#             txt = getattr(resp, "text")
#             if txt and str(txt).strip():
#                 return True, str(txt), None
#             return False, None, "empty_text"
#     except Exception:
#         pass
#     if isinstance(resp, dict):
#         if resp.get("error") or resp.get("errors"):
#             return False, None, json.dumps(resp.get("error") or resp.get("errors"))
#         if "candidates" in resp and isinstance(resp["candidates"], list) and resp["candidates"]:
#             cand = resp["candidates"][0]
#             if isinstance(cand, dict):
#                 if "text" in cand and cand["text"]:
#                     return True, str(cand["text"]), None
#                 if "content" in cand and isinstance(cand["content"], list):
#                     for piece in cand["content"]:
#                         if isinstance(piece, dict) and "text" in piece and piece["text"]:
#                             return True, str(piece["text"]), None
#         for k in ("output", "response", "message", "result"):
#             if k in resp and resp[k]:
#                 return True, str(resp[k]), None
#         return False, None, "unknown_dict_shape"
#     return False, None, "unknown_response_type"

# def genai_call(prompt):
#     try:
#         resp = client.models.generate_content(model=GENAI_MODEL, contents=prompt)
#     except Exception as e:
#         raise RuntimeError(f"GenAI SDK raised: {e}")
#     ok, text, err = is_genai_response_ok(resp)
#     if ok:
#         return "genai", text
#     raise RuntimeError(f"GenAI returned invalid/empty response ({err})")

# def ollama_call(prompt):
#     try:
#         r = requests.post(OLLAMA_GEN_ENDPOINT, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=60)
#         r.raise_for_status()
#         data = r.json()
#     except requests.exceptions.RequestException as exc:
#         raise RuntimeError(f"Ollama call failed: {exc}")
#     if isinstance(data, dict):
#         for k in ("response", "text", "output"):
#             if k in data and data[k]:
#                 return "ollama", data[k]
#         if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
#             ch = data["choices"][0]
#             if isinstance(ch, dict):
#                 if "message" in ch and isinstance(ch["message"], dict) and "content" in ch["message"]:
#                     return "ollama", ch["message"]["content"]
#                 if "text" in ch:
#                     return "ollama", ch["text"]
#     return "ollama", json.dumps(data)

# def inference_with_fallback(prompt):
#     try:
#         used, text = genai_call(prompt)
#         return used, text
#     except Exception as gen_err:
#         print(f"[WARN] GenAI failed: {gen_err}. Falling back to Ollama...")
#         try:
#             used2, text2 = ollama_call(prompt)
#             return used2, text2
#         except Exception as oll_err:
#             err_msg = f"GenAI error: {gen_err} | Ollama error: {oll_err}"
#             print(f"[ERROR] {err_msg}")
#             return "none", f"Both GenAI and Ollama failed. Details: {err_msg}"

# # ------------------------
# # PDF generation helper
# # ------------------------
# def generate_pdf_bytes(question, answer_text, chunks, used_model):
#     buffer = io.BytesIO()
#     c = canvas.Canvas(buffer, pagesize=letter)
#     width, height = letter
#     margin = 0.75 * inch
#     x = margin
#     y = height - margin

#     c.setFont("Helvetica-Bold", 14)
#     c.drawString(x, y, "Sigma WebDev — Answer")
#     y -= 18

#     c.setFont("Helvetica", 9)
#     c.drawString(x, y, f"Used model: {used_model}")
#     y -= 14

#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(x, y, "Question:")
#     y -= 14
#     c.setFont("Helvetica", 10)
#     for line in textwrap.wrap(question, width=100):
#         c.drawString(x, y, line)
#         y -= 12
#         if y < margin:
#             c.showPage()
#             y = height - margin

#     y -= 6
#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(x, y, "Answer:")
#     y -= 14
#     c.setFont("Helvetica", 10)
#     for paragraph in str(answer_text).split("\n"):
#         wrapped = textwrap.wrap(paragraph, width=100)
#         if not wrapped:
#             c.drawString(x, y, "")
#             y -= 12
#         for line in wrapped:
#             c.drawString(x, y, line)
#             y -= 12
#             if y < margin:
#                 c.showPage()
#                 y = height - margin

#     y -= 8
#     c.setFont("Helvetica-Bold", 11)
#     c.drawString(x, y, "Relevant video chunks:")
#     y -= 14
#     c.setFont("Helvetica", 10)
#     for chk in chunks:
#         title = chk.get("title", "Video")
#         number = chk.get("number", "")
#         start = int(chk.get("start") or 0)
#         end = int(chk.get("end") or 0)
#         youtube_link = chk.get("youtube_link") or ""
#         meta_line = f"{title} (Video {number}) [{start}s - {end}s]"
#         for line in textwrap.wrap(meta_line, width=100):
#             c.drawString(x, y, line)
#             y -= 12
#             if y < margin:
#                 c.showPage()
#                 y = height - margin
#         chunk_text = chk.get("text", "")
#         wrapped_chunk = textwrap.wrap(chunk_text, width=110)
#         for line in wrapped_chunk:
#             c.drawString(x + 12, y, line)
#             y -= 11
#             if y < margin:
#                 c.showPage()
#                 y = height - margin
#         if youtube_link:
#             link_line = f"Link: {youtube_link}"
#             for line in textwrap.wrap(link_line, width=100):
#                 c.drawString(x + 12, y, line)
#                 y -= 11
#                 if y < margin:
#                     c.showPage()
#                     y = height - margin
#         y -= 8

#     c.showPage()
#     c.save()
#     buffer.seek(0)
#     return buffer

# # ------------------------
# # Routes
# # ------------------------
# @app.route("/", methods=["GET"])
# def index():
#     resp = make_response(render_template_string(INDEX_HTML))
#     resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     resp.headers["Pragma"] = "no-cache"
#     resp.headers["Expires"] = "0"
#     return resp

# @app.route("/ask", methods=["POST"])
# def ask():
#     payload = request.get_json(force=True)
#     question = payload.get("question", "").strip()
#     if not question:
#         return jsonify({"error": "question required"}), 400
#     try:
#         q_emb = create_embedding_local([question])[0]
#         all_emb = np.vstack(df["embedding"])
#         sims = cosine_similarity(all_emb, [q_emb]).flatten()
#         top_idx = sims.argsort()[::-1][:TOP_K]
#         top_df = df.loc[top_idx].copy()
#         if "youtube_link" not in top_df.columns:
#             top_df["youtube_link"] = [None] * len(top_df)
#         context_json = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_json(orient="records")
#         prompt = f"""'I am teaching web development in my Sigma web development course. Here are video subtitle chunks containing video title, video number, start time in seconds, end time in seconds, the text at that time:

# Context:
# {context_json}

# User question: "{question}"

# User asked this question related to the video chunks, you have to answer in a human way (dont mention the above format, its just for you) where and how much content is taught in which video (in which video and at what timestamp) and guide the user to go to that particular video. If user asks unrelated question, tell him that you can only answer questions related to the course.dont ask question again
# """
#         used_model, answer_text = inference_with_fallback(prompt)
#         html_snips = []
#         for _, row in top_df.iterrows():
#             yt = row.get("youtube_link") or ""
#             title = row.get("title", "Video")
#             number = row.get("number", "")
#             start = int(row.get("start") or 0)
#             if yt:
#                 link_html = f'<a href="{yt}" target="_blank" rel="noopener noreferrer">Open at {start}s</a>'
#             else:
#                 link_html = f"{start}s"
#             html_snips.append(f"<p><b>{title}</b> (Video {number}) • {link_html}</p>")
#         html_output = f"<div><p>{answer_text}</p><hr><h4>Relevant video chunks:</h4>{''.join(html_snips)}</div>"
#         return jsonify({
#             "response": answer_text,
#             "html_response": html_output,
#             "top_k": min(TOP_K, len(top_df)),
#             "chunks": top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_dict(orient="records"),
#             "used_model": used_model
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route("/download", methods=["POST"])
# def download():
#     payload = request.get_json(force=True)
#     question = (payload.get("question") or "").strip()
#     if not question:
#         return jsonify({"error": "question required"}), 400
#     try:
#         q_emb = create_embedding_local([question])[0]
#         all_emb = np.vstack(df["embedding"])
#         sims = cosine_similarity(all_emb, [q_emb]).flatten()
#         top_idx = sims.argsort()[::-1][:TOP_K]
#         top_df = df.loc[top_idx].copy()
#         if "youtube_link" not in top_df.columns:
#             top_df["youtube_link"] = [None] * len(top_df)
#         context_json = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_json(orient="records")
#         prompt = f"""I am teaching web development in my Sigma web development course. Use the following chunks to answer the user's question. Include clickable youtube links when present.

# Context:
# {context_json}

# User question: "{question}"

# Answer naturally and concisely, and when referencing a chunk include its title and youtube link or timestamp.
# """
#         used_model, answer_text = inference_with_fallback(prompt)
#         chunks = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_dict(orient="records")
#         pdf_io = generate_pdf_bytes(question, answer_text, chunks, used_model)
#         return send_file(
#             pdf_io,
#             as_attachment=True,
#             download_name="sigma_answer.pdf",
#             mimetype="application/pdf"
#         )
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # ------------------------
# # Entrypoint
# # ------------------------
# if __name__ == "__main__":
#     print("Starting app on http://127.0.0.1:5000")
#     app.run(host="127.0.0.1", port=5000, debug=True)


# --------------------------------------------------------------------------------------------------

# import os
# import json
# import joblib
# import requests
# import numpy as np
# from flask import Flask, request, jsonify, make_response, render_template
# from sklearn.metrics.pairwise import cosine_similarity
# import google.genai as genai

# # ------------------------
# # Configuration
# # ------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# EMBEDDINGS_FILE = os.path.join(BASE_DIR, "embeddings.joblib")

# LOCAL_EMBED_ENDPOINT = "http://localhost:11434/api/embed"
# OLLAMA_GEN_ENDPOINT = "http://localhost:11434/api/generate"

# GENAI_MODEL = "gemini-2.5-flash"
# OLLAMA_MODEL = "llama3.2"
# TOP_K = 5

# DIRECT_GENAI_API_KEY = "YOUR_API_KEY_HERE"

# # ------------------------
# # Initialize
# # ------------------------
# app = Flask(__name__)
# client = genai.Client(api_key=DIRECT_GENAI_API_KEY)

# df = joblib.load(EMBEDDINGS_FILE)

# # ------------------------
# # Helpers
# # ------------------------
# def create_embedding_local(text_list):
#     r = requests.post(
#         LOCAL_EMBED_ENDPOINT,
#         json={"model": "bge-m3", "input": text_list},
#         timeout=30
#     )
#     r.raise_for_status()
#     res = r.json()
#     return res.get("embeddings") or [d["embedding"] for d in res["data"]]

# def genai_call(prompt):
#     resp = client.models.generate_content(model=GENAI_MODEL, contents=prompt)
#     return "genai", resp.text

# def ollama_call(prompt):
#     r = requests.post(
#         OLLAMA_GEN_ENDPOINT,
#         json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
#         timeout=60
#     )
#     r.raise_for_status()
#     return "ollama", r.json()["response"]

# def inference_with_fallback(prompt):
#     try:
#         return genai_call(prompt)
#     except:
#         try:
#             return ollama_call(prompt)
#         except Exception as e:
#             return "none", str(e)

# # ------------------------
# # Routes
# # ------------------------
# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/ask", methods=["POST"])
# def ask():
#     q = request.json.get("question", "").strip()
#     if not q:
#         return jsonify({"error": "Question required"}), 400

#     q_emb = create_embedding_local([q])[0]
#     all_emb = np.vstack(df["embedding"])
#     sims = cosine_similarity(all_emb, [q_emb]).flatten()

#     top_idx = sims.argsort()[::-1][:TOP_K]
#     top_df = df.iloc[top_idx]

#     prompt = f"""
#     Context: {top_df["text"].to_list()}
#     Question: {q}
#     """

#     used, answer = inference_with_fallback(prompt)

#     return jsonify({
#         "response": answer,
#         "chunks": top_df[["title", "number", "start", "end", "text", "youtube_link"]]
#                     .to_dict(orient="records"),
#         "used_model": used
#     })

# # ------------------------
# # Run
# # ------------------------
# if __name__ == "__main__":
#     app.run(debug=True)

#EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE


import os
import io
import json
import joblib
import textwrap
import requests
import numpy as np
from flask import (
    Flask,
    request,
    jsonify,
    render_template, 
    send_file,
    make_response
)

from sklearn.metrics.pairwise import cosine_similarity
import google.genai as genai
#import google.generativeai as genai



from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

# ------------------------
# Configuration
# ------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBEDDINGS_FILE = os.path.join(BASE_DIR, "embeddings.joblib")
LOCAL_EMBED_ENDPOINT = "http://localhost:11434/api/embed"
OLLAMA_GEN_ENDPOINT = "http://localhost:11434/api/generate"
GENAI_MODEL = "gemini-2.5-flash"
OLLAMA_MODEL = "llama3.2"
TOP_K = 5

# Put your API key here (development only)
DIRECT_GENAI_API_KEY = "AIzaSyAwH3Y--7pWW6s9-YHkICP-qFDYJlXxMg4"

# ------------------------
# Initialize
# ------------------------
app = Flask(__name__)
client = genai.Client(api_key=DIRECT_GENAI_API_KEY)
#client = genai.GenerativeModel("gemini-pro")


if not os.path.exists(EMBEDDINGS_FILE):
    raise FileNotFoundError(f"{EMBEDDINGS_FILE} not found. Place embeddings.joblib next to this file.")
df = joblib.load(EMBEDDINGS_FILE)

if "embedding" not in df.columns:
    raise ValueError("embeddings.joblib must contain an 'embedding' column.")
if "youtube_link" not in df.columns:
    print("Warning: 'youtube_link' column missing. Links will be None in responses.")



# ------------------------
# Backend helpers
# ------------------------
def create_embedding_local(text_list):
    try:
        r = requests.post(LOCAL_EMBED_ENDPOINT, json={"model": "bge-m3", "input": text_list}, timeout=30)
        r.raise_for_status()
        res = r.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Local embedder error: {exc}")
    if "embeddings" in res:
        return res["embeddings"]
    if "data" in res and isinstance(res["data"], list):
        return [item.get("embedding") for item in res["data"]]
    raise ValueError("Unexpected embedding response structure from local embedder")

def is_genai_response_ok(resp):
    try:
        if hasattr(resp, "text"):
            txt = getattr(resp, "text")
            if txt and str(txt).strip():
                return True, str(txt), None
            return False, None, "empty_text"
    except Exception:
        pass
    if isinstance(resp, dict):
        if resp.get("error") or resp.get("errors"):
            return False, None, json.dumps(resp.get("error") or resp.get("errors"))
        if "candidates" in resp and isinstance(resp["candidates"], list) and resp["candidates"]:
            cand = resp["candidates"][0]
            if isinstance(cand, dict):
                if "text" in cand and cand["text"]:
                    return True, str(cand["text"]), None
                if "content" in cand and isinstance(cand["content"], list):
                    for piece in cand["content"]:
                        if isinstance(piece, dict) and "text" in piece and piece["text"]:
                            return True, str(piece["text"]), None
        for k in ("output", "response", "message", "result"):
            if k in resp and resp[k]:
                return True, str(resp[k]), None
        return False, None, "unknown_dict_shape"
    return False, None, "unknown_response_type"

def genai_call(prompt):
    try:
        resp = client.models.generate_content(model=GENAI_MODEL, contents=prompt)
    except Exception as e:
        raise RuntimeError(f"GenAI SDK raised: {e}")
    ok, text, err = is_genai_response_ok(resp)
    if ok:
        return "genai", text
    raise RuntimeError(f"GenAI returned invalid/empty response ({err})")

def ollama_call(prompt):
    try:
        r = requests.post(OLLAMA_GEN_ENDPOINT, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=60)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Ollama call failed: {exc}")
    if isinstance(data, dict):
        for k in ("response", "text", "output"):
            if k in data and data[k]:
                return "ollama", data[k]
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            ch = data["choices"][0]
            if isinstance(ch, dict):
                if "message" in ch and isinstance(ch["message"], dict) and "content" in ch["message"]:
                    return "ollama", ch["message"]["content"]
                if "text" in ch:
                    return "ollama", ch["text"]
    return "ollama", json.dumps(data)

def inference_with_fallback(prompt):
    try:
        used, text = genai_call(prompt)
        return used, text
    except Exception as gen_err:
        print(f"[WARN] GenAI failed: {gen_err}. Falling back to Ollama...")
        try:
            used2, text2 = ollama_call(prompt)
            return used2, text2
        except Exception as oll_err:
            err_msg = f"GenAI error: {gen_err} | Ollama error: {oll_err}"
            print(f"[ERROR] {err_msg}")
            return "none", f"Both GenAI and Ollama failed. Details: {err_msg}"

# ------------------------
# PDF generation helper
# ------------------------
def generate_pdf_bytes(question, answer_text, chunks, used_model):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 0.75 * inch
    x = margin
    y = height - margin

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Sigma WebDev — Answer")
    y -= 18

    c.setFont("Helvetica", 9)
    c.drawString(x, y, f"Used model: {used_model}")
    y -= 14

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Question:")
    y -= 14
    c.setFont("Helvetica", 10)
    for line in textwrap.wrap(question, width=100):
        c.drawString(x, y, line)
        y -= 12
        if y < margin:
            c.showPage()
            y = height - margin

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Answer:")
    y -= 14
    c.setFont("Helvetica", 10)
    for paragraph in str(answer_text).split("\n"):
        wrapped = textwrap.wrap(paragraph, width=100)
        if not wrapped:
            c.drawString(x, y, "")
            y -= 12
        for line in wrapped:
            c.drawString(x, y, line)
            y -= 12
            if y < margin:
                c.showPage()
                y = height - margin

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Relevant video chunks:")
    y -= 14
    c.setFont("Helvetica", 10)
    for chk in chunks:
        title = chk.get("title", "Video")
        number = chk.get("number", "")
        start = int(chk.get("start") or 0)
        end = int(chk.get("end") or 0)
        youtube_link = chk.get("youtube_link") or ""
        meta_line = f"{title} (Video {number}) [{start}s - {end}s]"
        for line in textwrap.wrap(meta_line, width=100):
            c.drawString(x, y, line)
            y -= 12
            if y < margin:
                c.showPage()
                y = height - margin
        chunk_text = chk.get("text", "")
        wrapped_chunk = textwrap.wrap(chunk_text, width=110)
        for line in wrapped_chunk:
            c.drawString(x + 12, y, line)
            y -= 11
            if y < margin:
                c.showPage()
                y = height - margin
        if youtube_link:
            link_line = f"Link: {youtube_link}"
            for line in textwrap.wrap(link_line, width=100):
                c.drawString(x + 12, y, line)
                y -= 11
                if y < margin:
                    c.showPage()
                    y = height - margin
        y -= 8

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    payload = request.get_json(force=True)
    question = payload.get("question", "").strip()
    if not question:
        return jsonify({"error": "question required"}), 400
    try:
        q_emb = create_embedding_local([question])[0]
        all_emb = np.vstack(df["embedding"])
        sims = cosine_similarity(all_emb, [q_emb]).flatten()
        top_idx = sims.argsort()[::-1][:TOP_K]
        top_df = df.loc[top_idx].copy()
        if "youtube_link" not in top_df.columns:
            top_df["youtube_link"] = [None] * len(top_df)
        context_json = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_json(orient="records")
        prompt = f"""'I am teaching web development in my Sigma web development course. Here are video subtitle chunks containing video title, video number, start time in seconds, end time in seconds, the text at that time:

Context:
{context_json}

User question: "{question}"

User asked this question related to the video chunks, you have to answer in a human way (dont mention the above format, its just for you) where and how much content is taught in which video (in which video and at what timestamp) and guide the user to go to that particular video. If user asks unrelated question, tell him that you can only answer questions related to the course.dont ask question again
"""
        used_model, answer_text = inference_with_fallback(prompt)
        html_snips = []
        for _, row in top_df.iterrows():
            yt = row.get("youtube_link") or ""
            title = row.get("title", "Video")
            number = row.get("number", "")
            start = int(row.get("start") or 0)
            if yt:
                link_html = f'<a href="{yt}" target="_blank" rel="noopener noreferrer">Open at {start}s</a>'
            else:
                link_html = f"{start}s"
            html_snips.append(f"<p><b>{title}</b> (Video {number}) • {link_html}</p>")
        html_output = f"<div><p>{answer_text}</p><hr><h4>Relevant video chunks:</h4>{''.join(html_snips)}</div>"
        return jsonify({
            "response": answer_text,
            "html_response": html_output,
            "top_k": min(TOP_K, len(top_df)),
            "chunks": top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_dict(orient="records"),
            "used_model": used_model
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    payload = request.get_json(force=True)
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question required"}), 400
    try:
        q_emb = create_embedding_local([question])[0]
        all_emb = np.vstack(df["embedding"])
        sims = cosine_similarity(all_emb, [q_emb]).flatten()
        top_idx = sims.argsort()[::-1][:TOP_K]
        top_df = df.loc[top_idx].copy()
        if "youtube_link" not in top_df.columns:
            top_df["youtube_link"] = [None] * len(top_df)
        context_json = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_json(orient="records")
        prompt = f"""I am teaching web development in my Sigma web development course. Use the following chunks to answer the user's question. Include clickable youtube links when present.

Context:
{context_json}

User question: "{question}"

Answer naturally and concisely, and when referencing a chunk include its title and youtube link or timestamp.
"""
        used_model, answer_text = inference_with_fallback(prompt)
        chunks = top_df[["title", "number", "start", "end", "text", "youtube_link"]].to_dict(orient="records")
        pdf_io = generate_pdf_bytes(question, answer_text, chunks, used_model)
        return send_file(
            pdf_io,
            as_attachment=True,
            download_name="sigma_answer.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------------
# Entrypoint
# ------------------------
if __name__ == "__main__":
    print("Starting app on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)



