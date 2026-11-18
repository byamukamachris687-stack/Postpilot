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


REWRITE_INSTRUCTIONS = {
    "engaging": "Make the caption more engaging and conversational. Add a hook, a question, and a clear CTA. Keep the same core message.",
    "shorter": "Shorten the caption to under 60 words while keeping the key message and CTA.",
    "emojis": "Add relevant emojis throughout the caption (not too many) to make it more eye-catching.",
    "professional": "Rewrite in a more professional, polished tone suitable for B2B. Remove slang and excessive emojis.",
    "story": "Rewrite as a short personal story (first person) that leads into the offer/CTA.",
    "viral": "Rewrite to maximize virality: strong hook in first 5 words, curiosity gap, short sentences, bold claim.",
}


def build_rewrite_prompt(caption, instruction_key, platform="instagram"):
    instr = REWRITE_INSTRUCTIONS.get(instruction_key, instruction_key)
    return f"""Platform: {platform}
Original caption:
\"\"\"{caption}\"\"\"

Task: {instr}

Return JSON: {{"caption": "rewritten caption", "hashtags": "updated hashtags if needed"}}"""


def build_reply_prompt(brand, comment, n=3):
    return f"""Brand: {brand['name']} ({brand.get('industry')})
Brand voice: {brand.get('tone') or 'friendly, professional'}
Audience: {brand.get('audience')}

A customer left this comment on your post:
\"\"\"{comment}\"\"\"

Generate {n} different reply options. Mix tones: one friendly, one helpful/informative, one short & witty. Keep each under 40 words. Include an emoji or two where natural.

Return JSON: {{"replies": [{{"tone": "...", "text": "..."}}]}}"""


def build_repurpose_prompt(brand, source_text, n=5):
    return f"""Brand: {brand['name']} ({brand.get('industry')})
Audience: {brand.get('audience')}
Tone: {brand.get('tone')}

Source content (blog post / article / notes):
\"\"\"{source_text[:3000]}\"\"\"

Turn this into {n} social media posts across Instagram, Facebook, and TikTok. Each post should extract one key idea/insight from the source. Vary formats (tip, quote, story, list, question).

Return JSON: {{"posts": [{{"platform": "instagram|facebook|tiktok", "content_type": "reel|carousel|post", "caption": "...", "hashtags": "...", "hook": "..."}}]}}"""


def build_strategy_prompt(brand):
    return f"""Brand: {brand['name']} ({brand.get('industry')})
Audience: {brand.get('audience')}
Tone: {brand.get('tone')}
Products: {brand.get('products')}

Create a 7-day content strategy for this brand's social media. For each day: theme, content type, platform focus, and one specific post idea.

Return JSON: {{"strategy": [{{"day": "Monday", "theme": "...", "platform": "...", "format": "...", "idea": "..."}}], "tip": "one pro tip for the week"}}"""