import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime
from io import BytesIO
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import time
from docx import Document
from fpdf import FPDF

# -------- إعداد الصفحة --------
st.set_page_config(page_title="📰 أداة إدارة الأخبار المتقدمة", layout="wide")

# -------- تلخيص سريع --------
def summarize(text, max_words=25):
    return " ".join(text.split()[:max_words]) + "..."

# -------- تحليل معنوي --------
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        return "😃 إيجابي"
    elif polarity < -0.1:
        return "😠 سلبي"
    else:
        return "😐 محايد"

# -------- استخراج الأخبار --------
def fetch_news(rss_links, keywords, date_from, date_to):
    all_news = []
    for source, url in rss_links.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            summary = entry.get("summary", "")
            link = entry.link
            published = entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            try:
                published_dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
            except:
                published_dt = datetime.now()
            image = ""
            if 'media_content' in entry:
                image = entry.media_content[0].get('url', '')
            elif 'media_thumbnail' in entry:
                image = entry.media_thumbnail[0].get('url', '')

            # فلترة حسب التاريخ
            if not (date_from <= published_dt.date() <= date_to):
                continue

            # فلترة حسب الكلمات المفتاحية
            if keywords:
                if not any(keyword.lower() in (title + summary).lower() for keyword in keywords):
                    continue

            all_news.append({
                "source": source,
                "title": title,
                "summary": summary,
                "link": link,
                "published": published_dt,
                "image": image,
                "sentiment": analyze_sentiment(summary)
            })
    return all_news

# -------- تصدير الأخبار --------
def export_to_word(news_list):
    doc = Document()
    for news in news_list:
        doc.add_heading(news['title'], level=2)
        doc.add_paragraph(f"المصدر: {news['source']}")
        doc.add_paragraph(f"📅 التاريخ: {news['published'].strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"📄 التلخيص: {summarize(news['summary'])}")
        doc.add_paragraph(f"🔗 الرابط: {news['link']}")
        doc.add_paragraph(f"تحليل معنوي: {news['sentiment']}")
        doc.add_paragraph("-----")
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def export_to_excel(news_list):
    df = pd.DataFrame(news_list)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

def export_to_html(news_list):
    df = pd.DataFrame(news_list)
    buffer = BytesIO()
    buffer.write(df.to_html().encode())
    buffer.seek(0)
    return buffer

# -------- واجهة Streamlit --------
st.title("🗞️ أداة إدارة وتحليل الأخبار الذكية")

# -------- المصادر --------
rss_sources = {
    "BBC عربي": "http://feeds.bbci.co.uk/arabic/rss.xml",
    "CNN بالعربية": "http://arabic.cnn.com/rss/latest",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "France24 عربي": "https://www.france24.com/ar/rss",
    "الشرق الأوسط": "https://aawsat.com/home/rss.xml"
}

col1, col2 = st.columns([1, 2])

with col1:
    selected_sources = st.multiselect("🌐 اختر مصادر الأخبار:", list(rss_sources.keys()), default=list(rss_sources.keys()))
    keywords_input = st.text_input("🔍 كلمات مفتاحية (مفصولة بفواصل):", "")
    keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []
    date_from = st.date_input("📅 من تاريخ:", datetime.today())
    date_to = st.date_input("📅 إلى تاريخ:", datetime.today())
    auto_refresh = st.checkbox("♻️ تحديث تلقائي كل 60 ثانية")
    run = st.button("📥 عرض الأخبار")

if auto_refresh:
    time.sleep(60)
    st.experimental_rerun()

with col2:
    if run:
        selected_rss_links = {src: rss_sources[src] for src in selected_sources}
        news = fetch_news(selected_rss_links, keywords, date_from, date_to)

        if not news:
            st.warning("⚠️ لا توجد أخبار بهذه الشروط.")
        else:
            st.success(f"✅ تم العثور على {len(news)} خبر.")
            # عرض الأخبار Grid
            show_count = st.session_state.get("show_count", 6)
            news_to_display = news[:show_count]

            for i in range(0, len(news_to_display), 3):
                cols = st.columns(3)
                for idx, col in enumerate(cols):
                    if i + idx < len(news_to_display):
                        item = news_to_display[i + idx]
                        with col:
                            if item['image']:
                                st.image(item['image'], width=200)
                            st.markdown(f"### {item['title']}")
                            st.markdown(f"**📅 التاريخ:** {item['published'].strftime('%Y-%m-%d')}")
                            st.markdown(f"**المصدر:** {item['source']}")
                            st.markdown(f"**📄 التلخيص:** {summarize(item['summary'])}")
                            st.markdown(f"**تحليل:** {item['sentiment']}")
                            st.markdown(f"[اقرأ المزيد ↗]({item['link']})")

            if show_count < len(news):
                if st.button("عرض المزيد"):
                    st.session_state["show_count"] = show_count + 6

            # أزرار التحميل
            st.download_button("📥 تحميل كـ Word", data=export_to_word(news), file_name="news.docx")
            st.download_button("📥 تحميل كـ Excel", data=export_to_excel(news), file_name="news.xlsx")
            st.download_button("📥 تحميل كـ HTML", data=export_to_html(news), file_name="news.html")

            # رسم سحابة الكلمات
            all_text = " ".join(item['summary'] for item in news)
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_text)
            st.header("☁️ أكثر الكلمات تكرارًا")
            st.image(wordcloud.to_array())

            # رسم الإحصائيات
            df = pd.DataFrame(news)
            if not df.empty:
                st.header("📊 عدد الأخبار حسب المصدر")
                st.bar_chart(df['source'].value_counts())

                st.header("📊 توزيع التحليل المعنوي")
                st.bar_chart(df['sentiment'].value_counts())
