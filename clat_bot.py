import os, asyncio, telegram, feedparser, re
from groq import Groq
import edge_tts

# ── YOUR KEYS ─────────────────────────────────────────────────
GROQ_API_KEY        = "YOUR_GROQ_API_KEY"
TELEGRAM_BOT_TOKEN  = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHANNEL_ID = "YOUR_TELEGRAM_CHAT_ID"

# ─────────────────────────────────────────────────────────────
client = Groq(api_key=GROQ_API_KEY)

RSS_SOURCES = {
    "The Hindu":      "https://www.thehindu.com/news/national/feeder/default.rss",
    "Indian Express": "https://indianexpress.com/section/india/feed/",
    "PIB":            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
}

# ── SCRAPER ───────────────────────────────────────────────────
def get_news():
    articles = []
    for source, url in RSS_SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                articles.append({
                    "source":  source,
                    "title":   entry.get("title", ""),
                    "summary": entry.get("summary", "")[:400],
                })
        except Exception as e:
            print(f"Error {source}: {e}")
    print(f"Scraped {len(articles)} articles")
    return articles

# ── AI — BULLET BRIEF ─────────────────────────────────────────
def generate_bullet_brief(articles):
    dump = "\n\n".join([
        f"[{a['source']}] {a['title']}\n{a['summary']}"
        for a in articles
    ])
    prompt = f"""You are a CLAT/AILET expert coach. From these articles pick only what is
relevant to: Constitutional Law, SC Judgments, International Relations,
Parliament Bills, Environment, Appointments, Science/Tech, Economics.

Generate exactly this format:

📌 CLAT DAILY BRIEF
━━━━━━━━━━━━━━━━━━━

⚖️ SUPREME COURT
• [summary] — 🎯 Why CLAT: [exam angle]

🏛️ CONSTITUTION & LAW
• [summary] — 🎯 Why CLAT: [exam angle]

🌍 INTERNATIONAL AFFAIRS
• [summary] — 🎯 Why CLAT: [exam angle]

📜 PARLIAMENT & BILLS
• [summary] — 🎯 Why CLAT: [exam angle]

🌿 ENVIRONMENT
• [summary] — 🎯 Why CLAT: [exam angle]

📊 ECONOMICS
• [summary] — 🎯 Why CLAT: [exam angle]

📚 VOCABULARY OF THE DAY
1. [word]: [meaning]
2. [word]: [meaning]
3. [word]: [meaning]
4. [word]: [meaning]
5. [word]: [meaning]

⚖️ LEGAL TERMS
1. [term]: [simple explanation]
2. [term]: [simple explanation]
3. [term]: [simple explanation]
4. [term]: [simple explanation]
5. [term]: [simple explanation]

ARTICLES:
{dump}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return response.choices[0].message.content

# ── AI — READING BRIEF ────────────────────────────────────────
def generate_reading_brief(articles):
    dump = "\n\n".join([
        f"[{a['source']}] {a['title']}\n{a['summary']}"
        for a in articles
    ])
    prompt = f"""You are a CLAT/AILET expert coach. From these articles write a detailed
READING BRIEF for students who prefer in-depth study.

Format:
📖 FULL READING BRIEF
"For those who prefer reading over listening"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each major news item write:
1. What happened (background + details)
2. Constitutional or legal provisions involved
3. CLAT exam angles (GK, Legal Reasoning, English sections)
4. Keywords to remember

Include 8 to 10 items. Target 15 minute read.

ARTICLES:
{dump}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000
    )
    return response.choices[0].message.content

# ── AUDIO GENERATOR ───────────────────────────────────────────
def clean_for_audio(text):
    clean = re.sub(r'[^\w\s\.,;:!?()\-]', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

async def make_audio(text, filename, lang="en"):
    if lang == "en":
        voice = "en-IN-NeerjaNeural"
        intro = "Welcome to CLAT Daily Brief. Today's current affairs curated for CLAT and AILET preparation. "
    else:
        voice = "hi-IN-SwaraNeural"
        intro = "CLAT Daily Brief mein aapka swagat hai. Aaj ke mahatvapoorn samachar jo CLAT aur AILET ke liye zaroori hain. "

    clean = clean_for_audio(text)
    full_text = intro + clean

    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(full_text, voice, rate="+5%")
            await communicate.save(filename)
            print(f"Audio saved: {filename}")
            return True
        except Exception as e:
            print(f"Audio attempt {attempt+1} failed: {e}")
            await asyncio.sleep(5)
    print(f"Audio failed after 3 attempts — skipping {filename}")
    return False

# ── SEND TO TELEGRAM ──────────────────────────────────────────
async def send_message(bot, text):
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await bot.send_message(TELEGRAM_CHANNEL_ID, chunk)
        await asyncio.sleep(1)

async def send():
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    # Step 1 — Scrape
    articles = get_news()

    # Step 2 — Generate bullet brief
    print("Generating bullet brief...")
    bullets = generate_bullet_brief(articles)

    # Step 3 — Generate reading brief
    print("Generating reading brief...")
    reading = generate_reading_brief(articles)

    # Step 4 — Generate audio files
    print("Generating English audio...")
    en_ok = await make_audio(bullets, "en_brief.mp3", lang="en")

    print("Generating Hindi audio...")
    hi_ok = await make_audio(bullets, "hi_brief.mp3", lang="hi")

    # Step 5 — Send bullet brief
    print("Sending bullet brief...")
    await send_message(bot, bullets)

    # Step 6 — Send reading brief
    print("Sending reading brief...")
    await send_message(bot, "📖 *Prefer Reading? Here is your full 15-min brief:*")
    await send_message(bot, reading)

    # Step 7 — Send English audio
    if en_ok:
        print("Sending English audio...")
        with open("en_brief.mp3", "rb") as f:
            await bot.send_audio(
                TELEGRAM_CHANNEL_ID,
                audio=f,
                title="CLAT Daily English Podcast",
                caption="🎧 10 min English brief — listen on your way!"
            )

    # Step 8 — Send Hindi audio
    if hi_ok:
        print("Sending Hindi audio...")
        with open("hi_brief.mp3", "rb") as f:
            await bot.send_audio(
                TELEGRAM_CHANNEL_ID,
                audio=f,
                title="CLAT Daily Hindi Podcast",
                caption="🎧 Hindi brief — sunein aur taiyaari karein!"
            )

    print("✅ All done! Sent to Telegram!")

asyncio.run(send())
