# Deploying Helix online (free) — Vercel + Hugging Face Spaces

Goal: a permanent public URL your teammates can use anytime.
- **Backend** (FastAPI + ML) → **Hugging Face Spaces** (Docker, free, 16 GB RAM)
- **Frontend** (Next.js Studio) → **Vercel** (free)

You need 3 free accounts: **GitHub**, **Hugging Face**, **Vercel**.

---

## Step 0 — Put the code on GitHub
(Already initialized locally with a commit — just create a repo and push.)
```powershell
# create an EMPTY repo on github.com first (e.g. "helix"), then:
git remote add origin https://github.com/<you>/helix.git
git branch -M main
git push -u origin main
```

---

## Step 1 — Backend → Hugging Face Spaces  (do this first to get the URL)

1. Go to **huggingface.co → New → Space**.
   - Owner: you · Space name: `helix-backend`
   - **SDK: Docker** · Template: **Blank** · Hardware: **CPU basic (free)** · Visibility: Public
2. Put the backend code into the Space (it's its own git repo):
   ```powershell
   git clone https://huggingface.co/spaces/<you>/helix-backend hf-space
   Copy-Item backend\Dockerfile, backend\requirements.txt, backend\README.md hf-space\
   Copy-Item backend\app hf-space\app -Recurse
   cd hf-space
   git add .
   git commit -m "Helix backend"
   git push       # username = your HF name, password = an HF access token (Settings → Access Tokens)
   cd ..
   ```
   *(Or use the Space's **Files → Add file** in the browser to upload `Dockerfile`, `requirements.txt`, `README.md`, and the `app/` folder.)*
3. The Space builds (~10–15 min the first time). When it's "Running", your backend URL is:
   `https://<you>-helix-backend.hf.space`  → test it: open `…/health` (should return `{"status":"ok"}`).
4. In the Space **Settings → Variables and secrets**, add:
   | Type | Name | Value |
   |------|------|-------|
   | Variable | `HELIX_CORS_ORIGINS` | `*` |
   | Secret | `HELIX_LLM_API_KEY` | your free Groq key (optional, for real LLM narration) |
   | Variable | `HELIX_LLM_BASE_URL` | `https://api.groq.com/openai/v1` (only if you set a key) |
   | Variable | `HELIX_LLM_MODEL` | `llama-3.3-70b-versatile` (only if you set a key) |
   | Secret | `E2B_API_KEY` | *optional* — run agent code in an **E2B microVM** (hardened isolation) instead of RestrictedPython · key from [e2b.dev](https://e2b.dev) |
   Then **Restart** the Space.

---

## Step 2 — Frontend → Vercel

1. Go to **vercel.com → Add New → Project** → import your GitHub repo.
2. In the import screen:
   - **Root Directory** → set to **`frontend`**  *(important)*
   - Framework Preset → **Next.js** (auto-detected)
   - **Environment Variables** → add:
     `NEXT_PUBLIC_API_URL` = `https://<you>-helix-backend.hf.space`  *(your HF URL from Step 1)*
3. **Deploy.** In ~2 min you get a public URL like `https://helix-<you>.vercel.app`.

---

## Step 3 — Share & test
Send teammates the **Vercel URL**. Open `/studio`, upload any CSV, run. The badge should read 🟢 **live · api**.

**Heads-up for testers:**
- The free HF backend **sleeps when idle** → the first request after a quiet spell takes ~30–60 s to wake (and downloads an 80 MB embedding model once). Subsequent runs are fast.
- Without a Groq key it runs **real ML + sandboxed self-correction** with offline mock narration; add the key for real agent text.
- Don't upload sensitive data — it's processed on your public backend.

---

## Local alternative — Docker Compose
```bash
docker compose up --build      # frontend :3000 · backend :8000
```

## Instant share alternative — Colab
Open `colab/Helix_RealData_Colab.ipynb` → Run all → share the printed `…gradio.live` link (the Gradio UI; link lasts ~72 h).
