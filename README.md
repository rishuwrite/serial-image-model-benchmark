# Free Image Models Benchmark & Prompt Generator (`Pati Brahmachari Ep 453 — UW9UwzeFVEk`)

This repository contains:
1. **`data/episode_UW9UwzeFVEk_prompts.json`**: The complete scene-by-scene analysis and **25 image generation prompts** (12 Wide shots + 12 Close-up shots + 1 Prediction shot) generated using your exact हिंदी टीवी-सीरियल रिकैप prompt on **[Pati Brahmachari | Full Episode 453 | 28 Oct 2026 (`UW9UwzeFVEk`)](https://www.youtube.com/watch?v=UW9UwzeFVEk)**.
2. **`.github/workflows/benchmark_images.yml` & `scripts/benchmark_models.py`**: A GitHub Actions workflow that generates the scene illustrations across **all 9 free image models** and produces labeled **side-by-side comparison contact sheets** (`output/comparisons/scene_XX_wide_comparison.jpg`) plus a timing & success table in your GitHub Actions summary.
3. **`scripts/production_images_dropin.py`**: A drop-in replacement for `recap/images.py` in your main `serial-recap-bot` repository with 4-step FLUX.1 Schnell, FLUX.2 Klein 4B, SDXL-Lightning, dual Cloudflare account support, updated Pollinations (`gen.pollinations.ai`), and AI Horde fallback.

---

## 1. All 9 Free Image Models Tested in This Repo

| Model Key | Provider | Official Model ID | Free Quota ($0) | API Key Needed? |
| :--- | :--- | :--- | :--- | :--- |
| `cf_flux1_schnell` | **Cloudflare Workers AI** | `@cf/black-forest-labs/flux-1-schnell` | **~173 images/day** (at `steps=4`) per free account | `CF_ACCOUNT_ID` + `CF_API_TOKEN` |
| `cf_flux2_klein_4b` | **Cloudflare Workers AI** | `@cf/black-forest-labs/flux-2-klein-4b` | **~75–96 images/day** per free account | Same `CF_ACCOUNT_ID` + `CF_API_TOKEN` |
| `cf_sdxl_lightning` | **Cloudflare Workers AI** | `@cf/bytedance/stable-diffusion-xl-lightning` | **Included in Workers Free** | Same `CF_ACCOUNT_ID` + `CF_API_TOKEN` |
| `cf_dreamshaper_lcm` | **Cloudflare Workers AI** | `@cf/lykon/dreamshaper-8-lcm` | **Included in Workers Free** | Same `CF_ACCOUNT_ID` + `CF_API_TOKEN` |
| `cf_sdxl_base` | **Cloudflare Workers AI** | `@cf/stabilityai/stable-diffusion-xl-base-1.0` | **Included in Workers Free** | Same `CF_ACCOUNT_ID` + `CF_API_TOKEN` |
| `pollinations_flux` | **Pollinations.ai** | `black-forest-labs/flux.1-schnell` | Free / Pollen allowance | Optional `POLLINATIONS_TOKEN` |
| `pollinations_zimage` | **Pollinations.ai** | `tongyi-mai/z-image-turbo` | Free / Pollen allowance | Optional `POLLINATIONS_TOKEN` |
| `ai_horde_sdxl` | **AI Horde (Stable Horde)** | `AlbedoBase XL (SDXL)` / `Dreamshaper XL` | **Unlimited (100% Free Forever)** | Works with **no key** (anonymous `0000000000`) or free `AI_HORDE_API_KEY` |
| `hf_gradio_flux` | **Hugging Face Spaces (ZeroGPU)** | `black-forest-labs/FLUX.1-schnell` | **~30–60 ZeroGPU calls/day** | Works anonymously or with free `HF_TOKEN` |

---

## 2. Step-by-Step Guide: Which API Keys to Add in GitHub Secrets

Go to your GitHub repository → **Settings → Secrets and variables → Actions → New repository secret**:

### A. Required for the 5 Cloudflare Models (`cf_*`) — 100% Free, No Credit Card Required
1. **`CF_ACCOUNT_ID`** & **`CF_API_TOKEN`** *(You already have these from your main bot!)*:
   - Log in to [dash.cloudflare.com](https://dash.cloudflare.com).
   - In the left sidebar, click **AI → Workers AI** → click **Use REST API**.
   - Copy your **Account ID** → save as `CF_ACCOUNT_ID`.
   - Click **Create a Workers AI API Token** → copy the token → save as `CF_API_TOKEN`.
2. *(Optional)* **`CF_ACCOUNT_ID_2`** & **`CF_API_TOKEN_2`**:
   - If you create a second free Cloudflare account on another email, add its Account ID and Token here. Both `benchmark_models.py` and `production_images_dropin.py` automatically fail over to Account #2 if Account #1 uses up its 10,000 daily free Neurons (~346 FLUX images/day total!).

### B. Optional Free Keys for Faster Priority on Non-Cloudflare Models
*(Note: `ai_horde_sdxl`, `hf_gradio_flux`, and `pollinations_*` will run even if you leave these blank, but adding free keys removes anonymous queue throttling!)*

1. **`HF_TOKEN` (Hugging Face Read Token — 100% Free, 30 Seconds)**:
   - Open [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (sign up for free, no credit card).
   - Click **Create new token** → choose **Read** type → name it `image-bench` → copy the `hf_...` token and save as `HF_TOKEN`.
   - Gives you higher daily ZeroGPU quota when `gradio_client` calls `black-forest-labs/FLUX.1-schnell`.
2. **`AI_HORDE_API_KEY` (AI Horde Free Kudos Key — 100% Free, 30 Seconds)**:
   - If left blank, the script automatically uses the official anonymous key `0000000000`.
   - For faster queue priority, register a free key at [aihorde.net/register](https://aihorde.net/register) (no credit card, 100% volunteer community project) and save as `AI_HORDE_API_KEY`.
3. **`POLLINATIONS_TOKEN` (Pollinations API Key — Optional)**:
   - Generate a token at [enter.pollinations.ai](https://enter.pollinations.ai) and save as `POLLINATIONS_TOKEN`.
4. **`GEMINI_API_KEY` (Optional)**:
   - Only needed if you pass a *different* YouTube episode URL into the workflow input. For `https://youtu.be/UW9UwzeFVEk`, all 25 prompts are already pre-generated inside `data/episode_UW9UwzeFVEk_prompts.json`!

---

## 3. How to Run the Test in GitHub Actions (1 Click)

1. Push or upload this repository to GitHub.
2. Open the **Actions** tab → click **`image-model-benchmark`** on the left → click **Run workflow**.
3. Choose your options:
   - **`scenes_mode`**:
     - `sample_3` *(Recommended first run — takes ~2–3 mins)*: Generates **Scene 1** (Courtyard Romance), **Scene 8** (Hook/Storm Prophecy), and **Scene 12** (Candlelit Climax Embrace) across every model and builds 3 side-by-side comparison grids!
     - `hook_only`: Generates only the main Hook scene (`scene_08_wide`) across all 9 models in ~45 seconds.
     - `all_12_wide`: Generates all 12 wide scene prompts across every selected model.
     - `all_25`: Generates all 12 wide shots + 12 close-ups + 1 prediction shot (25 images per model).
   - **`models_to_test`**:
     - Leave as `all` to test all 9 models, set to `cloudflare_only` to compare only the 5 Cloudflare models, or pass specific keys like `cf_flux1_schnell,cf_flux2_klein_4b,cf_sdxl_lightning`.
4. When the run finishes:
   - Scroll down the workflow run page to see the **Markdown Benchmark Table** (success rate + average seconds per image for every model).
   - Download the **`image-benchmark-outputs-...`** artifact zip and open **`comparisons/scene_01_wide_comparison.jpg`**, **`scene_08_wide_comparison.jpg`**, and **`scene_12_wide_comparison.jpg`** to see all models side-by-side!
