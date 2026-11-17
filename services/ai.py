import json
import urllib.request
import urllib.error
import os
from config import (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL,
                    GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL,
                    GEMINI_API_KEY, GEMINI_MODEL)


def _providers():
    """Return list of (provider_name, api_key, model, base_url, kind) in priority order."""
    out = []
    if OPENAI_API_KEY:
        out.append(("openai", OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, "openai"))
    if GROQ_API_KEY:
        out.append(("groq", GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL, "openai"))
    if GEMINI_API_KEY:
        out.append(("gemini", GEMINI_API_KEY, GEMINI_MODEL, None, "gemini"))
    return out


def _call_openai_compat(base_url, api_key, model, messages, temperature, max_tokens):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # OpenAI supports json_object response_format; Groq too. Gemini compat differs, handle separately.
    try:
        payload["response_format"] = {"type": "json_object"}
    except Exception:
        pass
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        # strip possible markdown fences
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)


def _call_gemini(api_key, model, messages, temperature, max_tokens):
    # Convert OpenAI-style messages to Gemini format
    system_text = ""
    user_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        else:
            user_text += m["content"] + "\n"
    prompt = (system_text + "\n" + user_text).strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens,
                            "responseMimeType": "application/json"},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        content = body["candidates"][0]["content"]["parts"][0]["text"]
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        return json.loads(content)


def _call_llm(messages, temperature=0.8, max_tokens=2500):
    providers = _providers()
    if not providers:
        return None  # demo mode
    last_err = None
    for name, key, model, base, kind in providers:
        try:
            if kind == "gemini":
                return _call_gemini(key, model, messages, temperature, max_tokens)
            else:
                return _call_openai_compat(base, key, model, messages, temperature, max_tokens)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All LLM providers failed. Last error: {last_err}")


def _active_provider():
    ps = _providers()
    return ps[0][0] if ps else "demo"


def generate_posts(brand, platforms, n_posts, extra=""):
    from services.prompts import build_generation_prompt, SYSTEM_PROMPT
    prompt = build_generation_prompt(brand, platforms, n_posts, extra)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = _call_llm(messages, temperature=0.85, max_tokens=3000)
    if result is None:
        result = _mock_posts(brand, platforms, n_posts)
    posts = result.get("posts", [])
    for p in posts:
        p.setdefault("caption", "")
        p.setdefault("hashtags", "")
        p.setdefault("image_prompt", "")
        p.setdefault("best_time", "")
        p.setdefault("hook", "")
        p.setdefault("content_type", "post")
        p.setdefault("scheduled_date", "")
    return posts


def generate_ideas(brand, n=10):
    from services.prompts import build_ideas_prompt, SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_ideas_prompt(brand, n)},
    ]
    result = _call_llm(messages, temperature=0.9, max_tokens=1500)
    if result is None:
        result = _mock_ideas(brand, n)
    return result.get("ideas", [])


def _mock_posts(brand, platforms, n_posts):
    name = brand["name"]
    ind = brand.get("industry") or "business"
    posts = []
    import datetime
    base = datetime.date.today() + datetime.timedelta(days=1)
    angles = ["educational tip", "behind the scenes", "customer story", "product spotlight", "engagement question"]
    for i in range(n_posts):
        plat = platforms[i % len(platforms)]
        date = (base + datetime.timedelta(days=i)).isoformat()
        posts.append({
            "platform": plat,
            "content_type": "reel" if plat == "tiktok" else ("carousel" if i % 3 == 0 else "post"),
            "caption": f"[DEMO MODE - add a free Groq/OpenAI key for real AI content]\n\nHey everyone! Here's a quick {angles[i % len(angles)]} from {name}. "
                       f"We're passionate about helping our {ind} community. What's your biggest challenge right now? Drop it below 👇",
            "hashtags": "#smallbusiness #socialmedia #marketing #growth" if plat != "tiktok" else "#fyp #smallbiz #tips",
            "image_prompt": f"Bright, modern photo representing {name} in {ind}, clean aesthetic, warm lighting",
            "best_time": "Tue 7:30pm" if plat == "instagram" else ("Wed 1pm" if plat == "facebook" else "Thu 8pm"),
            "hook": "Wait for it..." if plat == "tiktok" else "",
            "scheduled_date": date,
        })
    return {"posts": posts}


def _mock_ideas(brand, n):
    return {"ideas": [
        {"title": f"Idea {i+1} for {brand['name']}", "angle": "educational", "format": "carousel", "platform": "instagram"}
        for i in range(n)
    ]}


def provider_status():
    ps = _providers()
    if not ps:
        return "demo (no API key set)"
    return ", ".join(f"{n} ({m})" for n, _, m, _, _ in ps)