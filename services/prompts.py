SYSTEM_PROMPT = """You are an expert social media manager and copywriter for small businesses.
You create high-performing, platform-native content for Facebook, Instagram, and TikTok.
You understand each platform's algorithm, format, and audience behavior.
You always return STRICT JSON only, no markdown fences, no commentary."""

PLATFORM_RULES = {
    "instagram": {
        "name": "Instagram",
        "rules": """Instagram rules:
- Hook in first line (before "more").
- Use line breaks and emojis sparingly but effectively.
- Caption 80-180 words.
- 10-20 relevant hashtags at the END, mix of broad + niche.
- Suggest content type: reel, carousel, story, or single post.
- Best posting times: 11am-1pm or 7-9pm local.""",
    },
    "facebook": {
        "name": "Facebook",
        "rules": """Facebook rules:
- Conversational, community-focused, slightly longer (100-220 words).
- Ask a question or invite comments to drive engagement.
- 3-6 hashtags max.
- Include a clear CTA (link, comment, share).
- Best posting times: 9-11am or 1-3pm local.""",
    },
    "tiktok": {
        "name": "TikTok",
        "rules": """TikTok rules:
- First 3 seconds = hook. Write the on-screen text hook separately.
- Caption short (40-90 words) + 4-8 hashtags.
- Script should be punchy, 15-30 seconds spoken.
- Suggest trending audio vibe (not exact song).
- Best posting times: 7-9am, 12-3pm, or 7-11pm local.""",
    },
}


def build_generation_prompt(brand, platforms, n_posts, extra_instructions=""):
    import json
    brand_block = f"""Brand: {brand['name']}
Industry: {brand.get('industry') or 'general'}
Target audience: {brand.get('audience') or 'general consumers'}
Brand voice/tone: {brand.get('tone') or 'friendly, professional'}
Products/services: {brand.get('products') or 'not specified'}
Website: {brand.get('website') or 'n/a'}"""

    platform_list = ", ".join(platforms)
    rules = "\n\n".join(PLATFORM_RULES[p]["rules"] for p in platforms if p in PLATFORM_RULES)

    return f"""{brand_block}

Generate {n_posts} social media posts total, distributed across these platforms: {platform_list}.
Each platform should get a roughly equal share (round as needed).

{rules}

{extra_instructions}

Return a JSON object with this exact shape:
{{
  "posts": [
    {{
      "platform": "instagram|facebook|tiktok",
      "content_type": "reel|carousel|story|post|video",
      "caption": "full caption text",
      "hashtags": "#tag1 #tag2 ...",
      "image_prompt": "detailed prompt to generate the visual for this post",
      "best_time": "e.g. Tue 7:30pm",
      "hook": "short on-screen hook (mainly for tiktok/reels; empty string otherwise)",
      "scheduled_date": "YYYY-MM-DD"
    }}
  ]
}}

Make content feel authentic, specific to the brand, and varied across days (mix educational, promotional, behind-the-scenes, engagement, testimonial angles).
Start scheduled_date from tomorrow and space posts across the week.
Return ONLY the JSON object."""


def build_ideas_prompt(brand, n=10):
    return f"""Brand: {brand['name']} ({brand.get('industry')})
Audience: {brand.get('audience')}
Tone: {brand.get('tone')}

Generate {n} fresh content ideas (topics/angles) for this brand's social media, mixing formats (reels, carousels, lives, stories).
Return JSON: {{"ideas": [{{"title": "...", "angle": "...", "format": "...", "platform": "..."}}]}}"""