import streamlit as st
import feedparser
from datetime import datetime

# -------- استخراج الأخبار من RSS --------
def fetch_news_from_rss(rss_url, keywords):
    feed = feedparser.parse(rss_url)
    news_list = []
    total_entries = len(feed.entries)

    for entry in feed.entries:
        title = entry.title
        summary = entry.get("summary", "")
        link = entry.link
        published = entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if keywords:
            if any(keyword.lower() in (title + " " + summary).lower() for keyword in keywords):
                news_list.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published
                })
        else:
            news_list.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published
            })

    return news_list, total_entries

# -------- Streamlit App --------
st.set_page_config(page_title="أداة الأخبار - عرض كبطاقات", layout="wide")
st.title("🗞️ استخراج الأخبار وعرضها كبطاقات (RSS News Cards)")

# قائمة مصادر RSS
rss_feeds = {
    "BBC عربي": "http://feeds.bbci.co.uk/arabic/rss.xml",
    "CNN بالعربية": "http://arabic.cnn.com/rss/latest",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "France24 عربي": "https://www.france24.com/ar/rss",
    "الشرق الأوسط": "https://aawsat.com/home/rss.xml"
}

# تقسيم الأعمدة
col1, col2 = st.columns([1, 2])

with col1:
    selected_feed = st.selectbox("🌐 اختر مصدر الأخبار:", list(rss_feeds.keys()))
    custom_rss = st.text_input("🔗 أدخل رابط RSS مخصص (اختياري):", value="")
    keywords_input = st.text_input("🔍 كلمات مفتاحية (مفصولة بفواصل):", value="")
    keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []
    run_scrape = st.button("📥 استخراج الأخبار")

with col2:
    if run_scrape:
        with st.spinner("⏳ جاري تحميل الأخبار..."):
            rss_url = custom_rss if custom_rss else rss_feeds[selected_feed]
            news, total = fetch_news_from_rss(rss_url, keywords)

            if total == 0:
                st.error("❌ لم يتم العثور على أخبار في هذا المصدر.")
            elif not news:
                st.warning(f"⚠️ لم يتم العثور على أخبار تطابق الكلمات. ({total} خبر موجود بدون تطابق).")
            else:
                st.success(f"✅ تم العثور على {len(news)} خبر يطابق الكلمات من أصل {total} خبر.")
                for item in news:
                    with st.container():
                        st.markdown(f"### 📰 {item['title']}")
                        st.markdown(f"**🕓 التاريخ:** {item['published']}")
                        st.markdown(f"**📄 الوصف:** {item['summary']}")
                        st.markdown(f"[🌐 اقرأ المزيد ↗]({item['link']})")
                        st.markdown("---")
