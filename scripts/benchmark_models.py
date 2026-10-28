"""Multi-Model Free Image Generation Benchmark (`scripts/benchmark_models.py`).

Tests all 9 free image generation models discussed for the Serial Recap Bot on the exact
scene prompts from `Pati Brahmachari | Full Episode 453 (UW9UwzeFVEk)` (or any YouTube episode
analyzed live via `GEMINI_API_KEY`).

Generates:
1. Individual images per model (`output/<model_key>/scene_XX_<type>.jpg`)
2. Per-scene side-by-side comparison contact sheets (`output/comparisons/scene_XX_<type>_comparison.jpg`)
3. A master visual grid across all scenes & models (`output/ALL_MODELS_COMPARISON_GRID.jpg`)
4. A benchmark timing & success report (`output/BENCHMARK_REPORT.md` & `output/benchmark_results.json`)
"""
import base64, io, json, os, shutil, sys, time, urllib.parse, zlib, requests
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JSON = os.path.join(BASE_DIR, "data", "episode_UW9UwzeFVEk_prompts.json")
OUT_DIR = os.path.join(BASE_DIR, "output")

STYLE_SUFFIX = (
    "graphic novel illustration, dramatic cinematic lighting, rich saturated colors, painterly, "
    "Indian family drama, expressive faces, wide shot, family friendly, no text, no letters, no watermark, no gore"
)

# ==============================================================================
# 1. OPTIONAL LIVE GEMINI ANALYSIS (When a custom YouTube URL is provided)
# ==============================================================================

GEMINI_PROMPT = """आप एक हिंदी टीवी-सीरियल रिकैप राइटर हैं। यह वीडियो एक पूरा सीरियल-एपिसोड है। इसे ध्यान से देखें-सुनें और इसकी कहानी पर तेज़ रफ़्तार, 2-3 मिनट के YouTube वीडियो की स्क्रिप्ट बनाएँ।
शैली (बहुत ज़रूरी):
- पहले 5 सेकंड में चौंकाने वाला hook: एपिसोड का सबसे बड़ा ट्विस्ट सबसे पहले (सस्पेंस के साथ, पूरा राज़ खोले बिना)। hook 12-16 शब्द का।
- फिर कहानी सस्पेंस के क्रम में समझाएँ (\"लेकिन यह शुरू कैसे हुआ?\" जैसे मोड़ से), छोटे-छोटे वाक्य, भावनात्मक लहजा, लगातार जिज्ञासा।
- बीच के दृश्यों की narration में 2-3 सस्पेंस सवाल रखें (जैसे \"आख़िर उसने ऐसा क्यों किया?\")।
- narration तेज़, रोचक और high-retention हो; कोई भूमिका या लंबा वर्णन नहीं।
- 10 से 12 दृश्य, हर दृश्य की narration 20-28 शब्द। कुल (hook, दृश्य, cliffhanger, prediction) लगभग 330-390 शब्द।
सच्चाई के नियम:
- सारा हिंदी टेक्स्ट सिर्फ़ देवनागरी में (अंग्रेज़ी शब्द/संक्षेप भी देवनागरी में); सिर्फ़ image_prompt और closeup_prompt अंग्रेज़ी में।
- सिर्फ़ वही लिखें जो एपिसोड में सचमुच हुआ/कहा गया; ट्विस्ट को बढ़ा-चढ़ाकर झूठ न बनाएँ। पात्रों के नाम वही रखें जो संवादों में बोले गए हों; पक्का न हो तो \"बहू\", \"दादी\" जैसे रिश्ते। कलाकारों के असली नाम कभी न लिखें। संवादों की नक़ल न करें।
- \"cliffhanger\": एपिसोड का अंत 1-2 छोटे वाक्य में। \"prediction\": 2 वाक्य, साफ़ अनुमान की भाषा में (\"शायद\", \"हो सकता है\"), तथ्य की तरह नहीं।
चित्र: \"characters\" में हर मुख्य पात्र का अंग्रेज़ी visual विवरण (उम्र, बाल, कपड़ों के रंग, पहचान की एक चीज़; सामान्य, किसी असली व्यक्ति जैसा नहीं)। हर दृश्य का \"image_prompt\" (wide shot, 40-70 शब्द: क्षण, जगह, भाव, मौजूद पात्रों के visual विवरण शब्दशः) और \"closeup_prompt\" (उसी क्षण में मुख्य पात्र के चेहरे का close-up, भावना साफ़, 25-45 शब्द)। ख़ून/हिंसा/नग्नता नहीं; बच्चों को ख़तरे में न दिखाएँ।
\"keywords\": इस एपिसोड की कहानी और शो से जुड़े 20 प्रासंगिक खोज-शब्द (हिंदी + अंग्रेज़ी); कोई असंबंधित शो/व्यक्ति नहीं।
केवल JSON:
{"characters":[{"key":"c1","name":"...","visual":"..."}],
 "hook":"...","headline":"<=8 शब्द","thumb_text":"<=5 शब्द का चौंकाने वाला सवाल/हुक","hook_scene":0,
 "scenes":[{"title":"<=5 शब्द","narration":"...","emotion":"tense|sad|happy|angry|romantic|shock","image_prompt":"...","closeup_prompt":"..."}],
 "cliffhanger":"...","prediction":["...","..."],"prediction_image_prompt":"...","keywords":["..."]}
"""

def analyze_with_gemini(video_url):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("   [Gemini] GEMINI_API_KEY not set; using pre-analyzed episode_UW9UwzeFVEk_prompts.json")
        return None
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
    base_cfg = {"responseMimeType": "application/json", "temperature": 0.5}
    for m in models:
        for cfg in ({**base_cfg, "mediaResolution": "MEDIA_RESOLUTION_LOW"}, base_cfg):
            payload = {
                "contents": [{"parts": [{"file_data": {"file_uri": video_url}}, {"text": GEMINI_PROMPT}]}],
                "generationConfig": cfg,
            }
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                    params={"key": key},
                    json=payload,
                    timeout=600,
                )
                if r.status_code == 200:
                    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    txt = txt.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    print(f"   [Gemini] Analyzed {video_url} successfully with {m}")
                    return json.loads(txt)
            except Exception as e:
                print(f"   [Gemini] {m} warning: {e}")
    return None


# ==============================================================================
# 2. IMAGE MODEL ADAPTERS (Cloudflare, Pollinations, AI Horde, HuggingFace Gradio)
# ==============================================================================

def _cf_credentials():
    """Return list of configured (account_id, api_token) pairs (supports Account 1 + optional Account 2)."""
    creds = []
    acc1, tok1 = os.getenv("CF_ACCOUNT_ID", "").strip(), os.getenv("CF_API_TOKEN", "").strip()
    if acc1 and tok1:
        creds.append((acc1, tok1))
    acc2, tok2 = os.getenv("CF_ACCOUNT_ID_2", "").strip(), os.getenv("CF_API_TOKEN_2", "").strip()
    if acc2 and tok2:
        creds.append((acc2, tok2))
    return creds

def run_cloudflare_model(cf_model_id, steps=4, use_json_base64=True):
    """Create a runner function for any Cloudflare Workers AI text-to-image model."""
    def _runner(prompt, seed):
        creds = _cf_credentials()
        if not creds:
            raise RuntimeError("Skipped (Set CF_ACCOUNT_ID and CF_API_TOKEN in GitHub Secrets)")
        last_err = None
        for idx, (acc, tok) in enumerate(creds):
            url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{cf_model_id}"
            payload = {"prompt": prompt[:2000], "steps": steps, "seed": int(seed)}
            if "flux-1-schnell" in cf_model_id:
                payload.update({"width": 1344, "height": 768})
            else:
                payload.update({"width": 1024, "height": 576})
            r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json=payload, timeout=120)
            if r.status_code == 200:
                ctype = r.headers.get("content-type", "")
                if "application/json" in ctype:
                    b64 = (r.json().get("result") or {}).get("image")
                    if not b64:
                        raise RuntimeError(f"Empty image in JSON response: {r.text[:200]}")
                    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
                return Image.open(io.BytesIO(r.content)).convert("RGB")
            last_err = f"Account#{idx+1} HTTP {r.status_code}: {r.text[:200]}"
        raise RuntimeError(last_err)
    return _runner

def run_pollinations_model(model_name):
    """Create a runner function for Pollinations (tries new gen.pollinations.ai first, then image.pollinations.ai)."""
    def _runner(prompt, seed):
        tok = os.getenv("POLLINATIONS_TOKEN", "").strip()
        hdr = {"User-Agent": "SerialRecapImageBenchmark/1.0"}
        if tok:
            hdr["Authorization"] = f"Bearer {tok}"
        q = urllib.parse.quote(prompt[:1400])
        urls = [
            f"https://gen.pollinations.ai/image/{q}?model={urllib.parse.quote(model_name)}&width=1280&height=720&seed={seed}&nologo=true&enhance=true",
            f"https://image.pollinations.ai/prompt/{q}?model={urllib.parse.quote(model_name.split('/')[-1].split('.')[0])}&width=1280&height=720&seed={seed}&nologo=true&enhance=true&safe=true",
        ]
        last_err = None
        for u in urls:
            try:
                r = requests.get(u, headers=hdr, timeout=150)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                    im = Image.open(io.BytesIO(r.content)).convert("RGB")
                    if im.width >= 400 and im.height >= 300:
                        return im
                last_err = f"HTTP {r.status_code} ({r.headers.get('content-type', '')}): {r.text[:160]}"
            except Exception as e:
                last_err = f"{type(e).__name__}: {str(e)[:140]}"
        raise RuntimeError(last_err or "Pollinations request failed")
    return _runner

def run_ai_horde(prompt, seed):
    """Generate an image via AI Horde (100% free crowdsourced GPU cluster; works with anonymous key `0000000000`)."""
    api_key = os.getenv("AI_HORDE_API_KEY", "").strip() or "0000000000"
    hdr = {"apikey": api_key, "Client-Agent": "SerialRecapBenchmark:1.0:github"}
    payload = {
        "prompt": prompt[:1000],
        "params": {
            "width": 1024,
            "height": 576,
            "steps": 20,
            "seed": str(seed),
            "sampler_name": "k_euler",
            "cfg_scale": 7.0,
        },
        "nsfw": False,
        "censor_nsfw": True,
        "models": ["AlbedoBase XL (SDXL)", "Dreamshaper XL", "ICBINP - I Can't Believe It's Not Photography"],
        "r2": True,
    }
    r = requests.post("https://aihorde.net/api/v2/generate/async", headers=hdr, json=payload, timeout=30)
    if r.status_code not in (200, 202):
        # Fallback to default 512x512 model if anonymous resolution limit is hit
        payload["params"]["width"], payload["params"]["height"] = 768, 512
        payload.pop("models", None)
        r = requests.post("https://aihorde.net/api/v2/generate/async", headers=hdr, json=payload, timeout=30)
        if r.status_code not in (200, 202):
            raise RuntimeError(f"AI Horde init failed ({r.status_code}): {r.text[:200]}")

    req_id = r.json()["id"]
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(6)
        st = requests.get(f"https://aihorde.net/api/v2/generate/status/{req_id}", headers=hdr, timeout=30)
        if st.status_code == 200:
            d = st.json()
            if d.get("done"):
                gens = d.get("generations") or []
                if not gens:
                    raise RuntimeError("AI Horde finished with 0 generations")
                img_field = gens[0].get("img", "")
                if img_field.startswith("http"):
                    img_bytes = requests.get(img_field, timeout=60).content
                else:
                    img_bytes = base64.b64decode(img_field)
                return Image.open(io.BytesIO(img_bytes)).convert("RGB")
            if d.get("faulted"):
                raise RuntimeError("AI Horde job faulted")
    raise RuntimeError("AI Horde timed out after 180s")

def run_hf_gradio_space(space_id):
    """Call a free Hugging Face ZeroGPU Space (`black-forest-labs/FLUX.1-schnell` or `Tongyi-MAI/Z-Image-Turbo`)
    using `gradio_client`."""
    def _runner(prompt, seed):
        try:
            from gradio_client import Client
        except ImportError:
            raise RuntimeError("gradio_client not installed (pip install gradio_client)")
        hf_tok = os.getenv("HF_TOKEN", "").strip() or None
        try:
            client = Client(space_id, token=hf_tok)
        except TypeError:
            client = Client(space_id, hf_token=hf_tok)
        # Try standard FLUX.1-schnell / Z-Image-Turbo /infer or /generate signature
        try:
            res = client.predict(
                prompt=prompt[:1200],
                seed=int(seed),
                randomize_seed=False,
                width=1024,
                height=576,
                num_inference_steps=4,
                api_name="/infer",
            )
        except Exception:
            res = client.predict(prompt[:1200], api_name="/predict")
        path = res[0] if isinstance(res, (list, tuple)) else res
        if isinstance(path, dict):
            path = path.get("path") or path.get("url")
        return Image.open(path).convert("RGB")
    return _runner


# Complete Catalog of Free Models to Benchmark
MODELS = {
    "cf_flux1_schnell": {
        "label": "CF: FLUX.1 Schnell (4 steps)",
        "provider": "Cloudflare Workers AI",
        "model_id": "@cf/black-forest-labs/flux-1-schnell",
        "free_quota": "~173 imgs/day per account",
        "fn": run_cloudflare_model("@cf/black-forest-labs/flux-1-schnell", steps=4),
    },
    "cf_flux2_klein_4b": {
        "label": "CF: FLUX.2 Klein 4B",
        "provider": "Cloudflare Workers AI",
        "model_id": "@cf/black-forest-labs/flux-2-klein-4b",
        "free_quota": "~75-96 imgs/day per account",
        "fn": run_cloudflare_model("@cf/black-forest-labs/flux-2-klein-4b", steps=4),
    },
    "cf_sdxl_lightning": {
        "label": "CF: SDXL-Lightning (ByteDance)",
        "provider": "Cloudflare Workers AI",
        "model_id": "@cf/bytedance/stable-diffusion-xl-lightning",
        "free_quota": "Free on Workers AI",
        "fn": run_cloudflare_model("@cf/bytedance/stable-diffusion-xl-lightning", steps=4),
    },
    "cf_dreamshaper_lcm": {
        "label": "CF: DreamShaper 8 LCM",
        "provider": "Cloudflare Workers AI",
        "model_id": "@cf/lykon/dreamshaper-8-lcm",
        "free_quota": "Free on Workers AI",
        "fn": run_cloudflare_model("@cf/lykon/dreamshaper-8-lcm", steps=6),
    },
    "cf_sdxl_base": {
        "label": "CF: SDXL Base 1.0",
        "provider": "Cloudflare Workers AI",
        "model_id": "@cf/stabilityai/stable-diffusion-xl-base-1.0",
        "free_quota": "Free on Workers AI",
        "fn": run_cloudflare_model("@cf/stabilityai/stable-diffusion-xl-base-1.0", steps=12),
    },
    "pollinations_flux": {
        "label": "Pollinations: FLUX Schnell",
        "provider": "Pollinations.ai",
        "model_id": "black-forest-labs/flux.1-schnell",
        "free_quota": "Free / Pollen key",
        "fn": run_pollinations_model("black-forest-labs/flux.1-schnell"),
    },
    "pollinations_zimage": {
        "label": "Pollinations: Z-Image-Turbo",
        "provider": "Pollinations.ai",
        "model_id": "tongyi-mai/z-image-turbo",
        "free_quota": "Free / Pollen key",
        "fn": run_pollinations_model("tongyi-mai/z-image-turbo"),
    },
    "ai_horde_sdxl": {
        "label": "AI Horde: Free SDXL Cluster",
        "provider": "AI Horde (Stable Horde)",
        "model_id": "AlbedoBase XL / Dreamshaper XL",
        "free_quota": "Unlimited (100% Free)",
        "fn": run_ai_horde,
    },
    "hf_gradio_flux": {
        "label": "HF ZeroGPU: FLUX.1 Schnell",
        "provider": "Hugging Face Spaces (Gradio)",
        "model_id": "black-forest-labs/FLUX.1-schnell",
        "free_quota": "~30-60 ZeroGPU calls/day",
        "fn": run_hf_gradio_space("black-forest-labs/FLUX.1-schnell"),
    },
}


# ==============================================================================
# 3. VISUAL COMPARISON CONTACT SHEET BUILDER
# ==============================================================================

def _make_placeholder(width, height, title, err_msg):
    im = Image.new("RGB", (width, height), (35, 25, 35))
    d = ImageDraw.Draw(im)
    d.rectangle([4, 4, width - 5, height - 5], outline=(180, 60, 60), width=2)
    d.text((20, 25), f"[SKIPPED / FAILED] {title}", fill=(255, 190, 190))
    # Wrap error message across lines
    words = (err_msg or "").split()
    line, y = "", 65
    for w in words:
        if len(line + " " + w) <= 52:
            line = (line + " " + w).strip()
        else:
            d.text((20, y), line, fill=(210, 210, 210))
            y += 24
            line = w
            if y > height - 30:
                break
    if line and y <= height - 30:
        d.text((20, y), line, fill=(210, 210, 210))
    return im

def build_scene_comparison_sheet(scene_tag, scene_title, prompt_text, model_results, out_path):
    """Build a labeled side-by-side 16:9 grid comparing all tested models for a single scene."""
    cw, ch = 640, 360
    header_h = 85
    label_h = 36
    cols = min(3, max(1, len(model_results)))
    rows = (len(model_results) + cols - 1) // cols
    sheet_w = cols * cw
    sheet_h = header_h + rows * (ch + label_h)

    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 24))
    d = ImageDraw.Draw(sheet)
    d.text((20, 14), f"Scene: {scene_tag} | {scene_title}", fill=(255, 220, 60))
    d.text((20, 44), f"Prompt: {prompt_text[:135]}...", fill=(200, 200, 210))

    for idx, item in enumerate(model_results):
        r_idx = idx // cols
        c_idx = idx % cols
        x0 = c_idx * cw
        y0 = header_h + r_idx * (ch + label_h)

        # Draw model label bar
        status_txt = f"{item['label']} ({item['elapsed_s']:.1f}s)" if item["ok"] else f"{item['label']} [FAILED]"
        bar_col = (28, 70, 45) if item["ok"] else (80, 30, 30)
        d.rectangle([x0, y0, x0 + cw - 1, y0 + label_h - 1], fill=bar_col)
        d.text((x0 + 12, y0 + 9), status_txt, fill=(255, 255, 255))

        if item["ok"] and item.get("path") and os.path.exists(item["path"]):
            im = Image.open(item["path"]).convert("RGB").resize((cw, ch))
        else:
            im = _make_placeholder(cw, ch, item["label"], item.get("error", ""))
        sheet.paste(im, (x0, y0 + label_h))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path, quality=90)


# ==============================================================================
# 4. MAIN BENCHMARK RUNNER
# ==============================================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    video_url = os.getenv("VIDEO_URL", "").strip()
    scenes_mode = os.getenv("SCENES_MODE", "sample_3").strip().lower()
    selected_models_env = os.getenv("MODELS_TO_TEST", "all").strip().lower()
    shot_types_env = os.getenv("SHOT_TYPES", "wide").strip().lower()  # "wide" | "both"

    # Load episode prompts (either live via Gemini for a custom URL or from pre-analyzed JSON for UW9UwzeFVEk)
    data = None
    if video_url and "UW9UwzeFVEk" not in video_url and os.getenv("GEMINI_API_KEY", "").strip():
        data = analyze_with_gemini(video_url)
    if not data:
        data = json.load(open(DEFAULT_JSON, encoding="utf-8"))

    shutil.copy(DEFAULT_JSON, os.path.join(OUT_DIR, "episode_UW9UwzeFVEk_prompts.json"))

    scenes = data.get("scenes", [])
    jobs = []
    for i, sc in enumerate(scenes):
        jobs.append((f"scene_{i+1:02d}_wide", sc.get("title", f"Scene {i+1}"), sc["image_prompt"]))
        if shot_types_env == "both" and sc.get("closeup_prompt"):
            jobs.append((f"scene_{i+1:02d}_close", sc.get("title", f"Scene {i+1}") + " (Close-up)", sc["closeup_prompt"]))
    if shot_types_env == "both" and data.get("prediction_image_prompt"):
        jobs.append(("scene_13_prediction", "Prediction Scene", data["prediction_image_prompt"]))

    # Filter scenes based on SCENES_MODE so quick benchmark tests finish in ~2 minutes
    if scenes_mode == "hook_only":
        hook_idx = min(max(int(data.get("hook_scene", 0) or 0), 0), len(scenes) - 1)
        jobs = [j for j in jobs if j[0].startswith(f"scene_{hook_idx+1:02d}_")]
    elif scenes_mode == "sample_3":
        # Pick Scene 1 (Romantic), Scene 8 (Hook/Shock Prophecy), and Scene 12 (Climax Embrace)
        sample_prefixes = ("scene_01_wide", "scene_08_wide", "scene_12_wide")
        jobs = [j for j in jobs if j[0] in sample_prefixes] or jobs[:3]
    elif scenes_mode == "all_12_wide":
        jobs = [j for j in jobs if j[0].endswith("_wide")]
    # else "all_25": run every wide + close-up + prediction prompt

    # Filter models
    if selected_models_env in ("", "all"):
        active_models = list(MODELS.keys())
    elif selected_models_env == "cloudflare_only":
        active_models = [k for k in MODELS if k.startswith("cf_")]
    else:
        wanted = [x.strip() for x in selected_models_env.split(",") if x.strip()]
        active_models = [k for k in MODELS if k in wanted or any(w in k for w in wanted)]

    print(f"== IMAGE BENCHMARK | Episode: {data.get('show_en')} Ep {data.get('source_episode')} ({data.get('video_id')}) ==")
    print(f"   Prompts to generate: {len(jobs)} | Models to test: {len(active_models)} ({', '.join(active_models)})")

    seed_base = zlib.crc32(data.get("video_id", "UW9UwzeFVEk").encode()) % 100000
    all_results = {m: {"ok": 0, "failed": 0, "times": [], "errors": []} for m in active_models}
    per_scene_records = {}

    for j_idx, (tag, title_hi, raw_prompt) in enumerate(jobs):
        full_prompt = f"{raw_prompt}. Style: {STYLE_SUFFIX}"
        seed = seed_base + j_idx * 13
        print(f"\n--- [{j_idx+1}/{len(jobs)}] {tag} ({title_hi}) ---")
        per_scene_records[tag] = []

        for m_key in active_models:
            m_info = MODELS[m_key]
            m_dir = os.path.join(OUT_DIR, m_key)
            os.makedirs(m_dir, exist_ok=True)
            out_img_path = os.path.join(m_dir, f"{tag}.jpg")

            t0 = time.time()
            try:
                im = m_info["fn"](full_prompt, seed)
                elapsed = time.time() - t0
                im.save(out_img_path, quality=92)
                print(f"   [OK]   {m_key:<22} -> {elapsed:.1f}s ({im.width}x{im.height})")
                all_results[m_key]["ok"] += 1
                all_results[m_key]["times"].append(elapsed)
                per_scene_records[tag].append({
                    "model_key": m_key,
                    "label": m_info["label"],
                    "ok": True,
                    "elapsed_s": elapsed,
                    "path": out_img_path,
                })
            except Exception as e:
                elapsed = time.time() - t0
                err_str = str(e)[:180]
                print(f"   [SKIP] {m_key:<22} -> {err_str}")
                all_results[m_key]["failed"] += 1
                all_results[m_key]["errors"].append(err_str)
                per_scene_records[tag].append({
                    "model_key": m_key,
                    "label": m_info["label"],
                    "ok": False,
                    "elapsed_s": elapsed,
                    "error": err_str,
                    "path": None,
                })

        # Build comparison contact sheet for this scene across all tested models
        comp_path = os.path.join(OUT_DIR, "comparisons", f"{tag}_comparison.jpg")
        build_scene_comparison_sheet(tag, title_hi, raw_prompt, per_scene_records[tag], comp_path)
        print(f"   -> Saved side-by-side comparison sheet: {comp_path}")

    # Write summary markdown report & JSON
    report_lines = [
        f"# Multi-Model Image Benchmark Report (`{data.get('video_id')}` — {data.get('show_en')} Ep {data.get('source_episode')})",
        "",
        f"- **Source Video**: [{data.get('show_en')} Ep {data.get('source_episode')} ({data.get('source_date')})]({data.get('video_url')})",
        f"- **Scenes Tested**: `{len(jobs)}` (`SCENES_MODE={scenes_mode}`)",
        "",
        "| Model Key | Provider | Model ID | Free Quota | Success | Avg Speed (s) | Notes / Last Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for m_key in active_models:
        m_info = MODELS[m_key]
        st = all_results[m_key]
        avg_t = f"{sum(st['times'])/len(st['times']):.1f}s" if st["times"] else "-"
        note = "OK" if st["ok"] > 0 and not st["errors"] else (st["errors"][-1] if st["errors"] else "-")
        report_lines.append(
            f"| `{m_key}` | {m_info['provider']} | `{m_info['model_id']}` | {m_info['free_quota']} | "
            f"**{st['ok']}/{len(jobs)}** | {avg_t} | {note} |"
        )

    report_md = "\n".join(report_lines) + "\n"
    open(os.path.join(OUT_DIR, "BENCHMARK_REPORT.md"), "w", encoding="utf-8").write(report_md)
    json.dump({"summary": all_results, "scenes": per_scene_records}, open(os.path.join(OUT_DIR, "benchmark_results.json"), "w"), indent=2)
    print("\n== BENCHMARK COMPLETE! Summary written to output/BENCHMARK_REPORT.md ==")

if __name__ == "__main__":
    main()
