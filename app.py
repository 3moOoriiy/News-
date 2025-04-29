import streamlit as st
import feedparser
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
import time

# -------- تلخيص بسيط --------
def summarize(text, max_words=20):
    return " ".join(text.split()[:max_words]) + "..."

# -------- استخراج الأخبار من RSS --------
def fetch_news_with_images(rss_url, keywords):
    feed = feedparser.parse(rss_url)
    news_list = []

    for entry in feed.entries:
        title = entry.title
        summary = entry.get("summary", "")
        link = entry.link
        published = entry.get("published", None)
        try:
            published_dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
        except:
            published_dt = datetime.now()

        image = ""
        if 'media_content' in entry:
            image = entry.media_content[0].get('url', '')
        elif 'media_thumbnail' in entry:
            image = entry.media_thumbnail[0].get('url', '')

        if keywords:
            if any(keyword.lower() in (title + " " + summary).lower() for keyword in keywords):
                news_list.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published_dt,
                    "image": image
                })
        else:
            news_list.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published_dt,
                "image": image
            })

    return news_list

# -------- حفظ كـ PDF --------
def export_news_to_pdf(news_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for item in news_list:
        pdf.multi_cell(0, 10, f"العنوان: {item['title']}", align="R")
        pdf.multi_cell(0, 10, f"📅 التاريخ: {item['published'].strftime('%Y-%m-%d %H:%M:%S')}", align="R")
        pdf.multi_cell(0, 10, f"📄 التلخيص: {summarize(item['summary'])}", align="R")
        pdf.multi_cell(0, 10, f"🔗 الرابط: {item['link']}", align="R")
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# -------- Streamlit App --------
st.set_page_config(page_title="أداة الأخبار الشاملة", layout="wide")
st.title("📰 أداة استخراج وعرض وتلخيص الأخبار (كاملة)")

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
    keywords_input = st.text_input("🔍 كلمات مفتاحية:", value="")
    keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []
    sort_order = st.radio("🔃 ترتيب الأخبار:", ["الأحدث أولًا", "الأقدم أولًا"])
    auto_refresh = st.checkbox("♻️ تحديث تلقائي كل 60 ثانية")
    run = st.button("📥 عرض الأخبار")

# -------- تحديث تلقائي --------
if auto_refresh:
    time.sleep(60)
    st.experimental_rerun()

with col2:
    if run:
        rss_url = custom_rss if custom_rss else rss_feeds[selected_feed]
        news = fetch_news_with_images(rss_url, keywords)

        if not news:
            st.warning("⚠️ لا توجد أخبار.")
        else:
            reverse = True if sort_order == "الأحدث أولًا" else False
            news = sorted(news, key=lambda x: x["published"], reverse=reverse)

            st.success(f"✅ تم العثور على {len(news)} خبر.")
            for item in news:
                with st.container():
                    st.markdown("----")
                    cols = st.columns([1, 3])
                    with cols[0]:
                        if item["image"]:
                            st.image(item["image"], width=140)
                    with cols[1]:
                        st.markdown(f"### 📰 {item['title']}")
                        st.markdown(f"📅 **التاريخ:** {item['published'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown(f"**📄 التلخيص:** {summarize(item['summary'])}")
                        st.markdown(f"[🌐 اقرأ المزيد ↗]({item['link']})")

            pdf_buffer = export_news_to_pdf(news)
            st.download_button("📄 تحميل كـ PDF", data=pdf_buffer, file_name="أخبار.pdf", mime="application/pdf")
