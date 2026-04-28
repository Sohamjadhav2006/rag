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



