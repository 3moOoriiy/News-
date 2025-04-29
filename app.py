import streamlit as st
import feedparser
from datetime import datetime

def fetch_news_with_images(rss_url, keywords):
    feed = feedparser.parse(rss_url)
    news_list = []
    total_entries = len(feed.entries)

    for entry in feed.entries:
        title = entry.title
        summary = entry.get("summary", "")
        link = entry.link
        published = entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # نحاول نجيب صورة لو فيه
        image = ""
        if 'media_content' in entry:
            image = entry.media_content[0]['url']
        elif 'media_thumbnail' in entry:
            image = entry.media_thumbnail[0]['url']

        if keywords:
            if any(keyword.lower() in (title + " " + summary).lower() for keyword in keywords):
                news_list.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published,
                    "image": image
                })
        else:
            news_list.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
                "image": image
            })

    return news_list, total_entries


# Streamlit UI
st.set_page_config(page_title="بطاقات الأخبار مع صور", layout="wide")
st.title("🗞️ بطاقات الأخبار - مع دعم الصور")

rss_feeds = {
    "BBC عربي": "http://feeds.bbci.co.uk/arabic/rss.xml",
    "CNN بالعربية": "http://arabic.cnn.com/rss/latest",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "France24 عربي": "https://www.france24.com/ar/rss",
    "الشرق الأوسط": "https://aawsat.com/home/rss.xml"
}

col1, col2 = st.columns([1, 2])

with col1:
    selected_feed = st.selectbox("🌐 اختر المصدر:", list(rss_feeds.keys()))
    custom_rss = st.text_input("🔗 رابط RSS مخصص (اختياري):", value="")
    keywords_input = st.text_input("🔍 كلمات مفتاحية (مفصولة بفواصل):", value="")
    keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []
    run = st.button("📥 عرض الأخبار")

with col2:
    if run:
        with st.spinner("جاري تحميل الأخبار..."):
            rss_url = custom_rss if custom_rss else rss_feeds[selected_feed]
            news, total = fetch_news_with_images(rss_url, keywords)

            if total == 0:
                st.error("❌ لا توجد أخبار في المصدر.")
            elif not news:
                st.warning(f"⚠️ لا توجد أخبار تطابق الكلمات، لكن هناك {total} خبر متاح.")
            else:
                st.success(f"✅ تم العثور على {len(news)} خبر.")

                for item in news:
                    with st.container():
                        st.markdown("----")
                        if item["image"]:
                            st.image(item["image"], use_column_width=True)
                        st.markdown(f"### 📰 {item['title']}")
                        st.markdown(f"**🕓 التاريخ:** {item['published']}")
                        st.markdown(f"**📄 الوصف:** {item['summary']}")
                        st.markdown(f"[🌐 اقرأ المزيد ↗]({item['link']})")
