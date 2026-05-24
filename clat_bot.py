import os, asyncio, telegram, feedparser
from groq import Groq

GROQ_API_KEY        = os.environ["GROQ_API_KEY"]
TELEGRAM_BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

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

def generate_brief(articles):
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

async def send():
    articles = get_news()
    brief    = generate_brief(articles)
    print(brief)
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    for chunk in [brief[i:i+4000] for i in range(0, len(brief), 4000)]:
        await bot.send_message(TELEGRAM_CHANNEL_ID, chunk)
    print("✅ Sent to Telegram!")

asyncio.run(send())
