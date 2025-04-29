import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime
from io import BytesIO
from textblob import TextBlob
from collections import Counter
from docx import Document

st.set_page_config(page_title="📰 أداة الأخبار العربية الذكية", layout="wide")
st.title("🗞️ أداة إدارة وتحليل الأخبار (نسخة محسّنة + مصادر أكثر)")

# التصنيفات
category_keywords = {
    "سياسة": ["رئيس", "وزير", "انتخابات", "برلمان", "سياسة"],
    "رياضة": ["كرة", "لاعب", "مباراة", "دوري", "هدف"],
    "اقتصاد": ["سوق", "اقتصاد", "استثمار", "بنك", "مال"],
    "تكنولوجيا": ["تقنية", "تطبيق", "هاتف", "ذكاء", "برمجة"]
}

# الدوال
def summarize(text, max_words=25):
    return " ".join(text.split()[:max_words]) + "..."

def analyze_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.1:
        return "😃 إيجابي"
    elif polarity < -0.1:
        return "😠 سلبي"
    else:
        return "😐 محايد"

def detect_category(text):
    for category, words in category_keywords.items():
        if any(word in text for word in words):
            return category
    return "غير مصنّف"

def fetch_news(source_name, url, keywords, date_from, date_to, chosen_category):
    feed = feedparser.parse(url)
    news_list = []
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

        if not (date_from <= published_dt.date() <= date_to):
            continue

        full_text = title + " " + summary
        if keywords and not any(k.lower() in full_text.lower() for k in keywords):
            continue

        auto_category = detect_category(full_text)
        if chosen_category != "الكل" and auto_category != chosen_category:
            continue

        news_list.append({
            "source": source_name,
            "title": title,
            "summary": summary,
            "link": link,
            "published": published_dt,
            "image": image,
            "sentiment": analyze_sentiment(summary),
            "category": auto_category
        })

    return news_list

def export_to_word(news_list):
    doc = Document()
    for news in news_list:
        doc.add_heading(news['title'], level=2)
        doc.add_paragraph(f"المصدر: {news['source']}  |  التصنيف: {news['category']}")
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

# ✅ مصادر الأخبار (تم التوسيع)
rss_feeds = {
    "BBC عربي": "http://feeds.bbci.co.uk/arabic/rss.xml",
    "CNN بالعربية": "http://arabic.cnn.com/rss/latest",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "France24 عربي": "https://www.france24.com/ar/rss",
    "الشرق الأوسط": "https://aawsat.com/home/rss.xml",
    "سكاي نيوز عربية": "https://www.skynewsarabia.com/web/rss",
    "الجزيرة": "https://www.aljazeera.net/aljazeerarss/ar/home",
    "عربي21": "https://arabi21.com/feed",
    "الوطن": "https://www.elwatannews.com/home/rss",
    "اليوم السابع": "https://www.youm7.com/rss/SectionRss?SectionID=65",
    "المصري اليوم": "https://www.almasryalyoum.com/rss/rssfeeds",
    "صحيفة سبق": "https://sabq.org/rss"
}

# واجهة التحكم
col1, col2 = st.columns([1, 2])
with col1:
    selected_source = st.selectbox("🌐 اختر مصدر الأخبار:", list(rss_feeds.keys()))
    keywords_input = st.text_input("🔍 كلمات مفتاحية (مفصولة بفواصل):", "")
    keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []
    category_filter = st.selectbox("📁 اختر التصنيف:", ["الكل"] + list(category_keywords.keys()))
    date_from = st.date_input("📅 من تاريخ:", datetime.today())
    date_to = st.date_input("📅 إلى تاريخ:", datetime.today())
    run = st.button("📥 عرض الأخبار")

# عرض النتائج
with col2:
    if run:
        news = fetch_news(
            selected_source,
            rss_feeds[selected_source],
            keywords,
            date_from,
            date_to,
            category_filter
        )

        if not news:
            st.warning("❌ لا توجد أخبار بهذه الشروط.")
        else:
            st.success(f"✅ تم العثور على {len(news)} خبر.")
            for item in news:
                with st.container():
                    st.markdown("----")
                    cols = st.columns([1, 4])
                    with cols[0]:
                        if item["image"]:
                            st.image(item["image"], use_column_width=True)
                    with cols[1]:
                        st.markdown(f"### 📰 {item['title']}")
                        st.markdown(f"📅 التاريخ: {item['published'].strftime('%Y-%m-%d')}")
                        st.markdown(f"📁 التصنيف: {item['category']}")
                        st.markdown(f"📄 التلخيص: {summarize(item['summary'])}")
                        st.markdown(f"🎯 التحليل: {item['sentiment']}")
                        st.markdown(f"[🌐 اقرأ المزيد ↗]({item['link']})")

            word_file = export_to_word(news)
            excel_file = export_to_excel(news)

            st.download_button("📄 تحميل كـ Word", data=word_file, file_name="news.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.download_button("📊 تحميل كـ Excel", data=excel_file, file_name="news.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.markdown("### 🔠 أكثر الكلمات تكرارًا:")
            all_text = " ".join([n['summary'] for n in news])
            words = [word for word in all_text.split() if len(word) > 3]
            word_freq = Counter(words).most_common(10)
            for word, freq in word_freq:
                st.markdown(f"- **{word}**: {freq} مرة")
