import asyncio, telegram, feedparser
from groq import Groq

GROQ_API_KEY        = "YOUR_GROQ_API_KEY"
TELEGRAM_BOT_TOKEN  = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHANNEL_ID = "YOUR_TELEGRAM_CHAT_ID"

client = Groq(api_key=GROQ_API_KEY)

RSS_SOURCES = {
    "The Hindu":      "https://www.thehindu.com/news/national/feeder/default.rss",
    "Indian Express": "https://indianexpress.com/section/india/feed/",
    "PIB":            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
}

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

def generate_reading_brief(articles):
    dump = "\n\n".join([
        f"[{a['source']}] {a['title']}\n{a['summary']}"
        for a in articles
    ])
    prompt = f"""You are a CLAT/AILET expert coach. Write a detailed READING BRIEF.

Format:
📖 FULL READING BRIEF
━━━━━━━━━━━━━━━━━━━━

For each major news item write:
1. What happened
2. Constitutional or legal provisions involved
3. CLAT exam angles
4. Keywords to remember

Include 8 items. Target 15 minute read.

ARTICLES:
{dump}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000
    )
    return response.choices[0].message.content

async def send_message(bot, text):
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await bot.send_message(TELEGRAM_CHANNEL_ID, chunk)
        await asyncio.sleep(1)

async def send():
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

    print("Scraping news...")
    articles = get_news()

    print("Generating bullet brief...")
    bullets = generate_bullet_brief(articles)

    print("Generating reading brief...")
    reading = generate_reading_brief(articles)

    print("Sending to Telegram...")
    await send_message(bot, bullets)
    await send_message(bot, "📖 *Full Reading Brief — 15 min read:*")
    await send_message(bot, reading)

    print("✅ Done! Sent to Telegram!")

asyncio.run(send())
