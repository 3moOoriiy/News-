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
    "سياسة": ["رئيس", "وزير", "انتخابات", "برلمان", "سياسة", "حكومة", "نائب"],
    "رياضة": ["كرة", "لاعب", "مباراة", "دوري", "هدف", "فريق", "بطولة"],
    "اقتصاد": ["سوق", "اقتصاد", "استثمار", "بنك", "مال", "تجارة", "صناعة"],
    "تكنولوجيا": ["تقنية", "تطبيق", "هاتف", "ذكاء", "برمجة", "إنترنت", "رقمي"]
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

def fetch_rss_news(source_name, url, keywords, date_from, date_to, chosen_category):
    """جلب الأخبار من مصادر RSS"""
    try:
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
                try:
                    published_dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S%z")
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
    except Exception as e:
        st.error(f"خطأ في جلب الأخبار من {source_name}: {str(e)}")
        return []

def try_multiple_rss_feeds(source_name, rss_options, keywords, date_from, date_to, chosen_category):
    """تجربة عدة روابط RSS للمصدر الواحد"""
    for rss_url in rss_options:
        try:
            st.info(f"🔄 جاري تجربة: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            # التحقق من وجود entries في الـ feed
            if hasattr(feed, 'entries') and len(feed.entries) > 0:
                st.success(f"✅ تم العثور على RSS في: {rss_url}")
                
                news_list = []
                for entry in feed.entries:
                    try:
                        title = entry.get('title', 'بدون عنوان')
                        summary = entry.get('summary', entry.get('description', ''))
                        link = entry.get('link', '')
                        published = entry.get('published', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        
                        try:
                            published_dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
                        except:
                            try:
                                published_dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S%z")
                            except:
                                try:
                                    published_dt = datetime.strptime(published, "%Y-%m-%d %H:%M:%S")
                                except:
                                    published_dt = datetime.now()
                        
                        # التحقق من التاريخ
                        if not (date_from <= published_dt.date() <= date_to):
                            continue

                        full_text = title + " " + summary
                        if keywords and not any(k.lower() in full_text.lower() for k in keywords):
                            continue

                        auto_category = detect_category(full_text)
                        if chosen_category != "الكل" and auto_category != chosen_category:
                            continue

                        # البحث عن صورة
                        image = ""
                        if hasattr(entry, 'media_content') and entry.media_content:
                            image = entry.media_content[0].get('url', '')
                        elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                            image = entry.media_thumbnail[0].get('url', '')
                        elif hasattr(entry, 'enclosures') and entry.enclosures:
                            for enclosure in entry.enclosures:
                                if 'image' in enclosure.get('type', ''):
                                    image = enclosure.get('href', '')
                                    break

                        news_list.append({
                            "source": source_name,
                            "title": title,
                            "summary": summary,
                            "link": link,
                            "published": published_dt,
                            "image": image,
                            "sentiment": analyze_sentiment(summary),
                            "category": auto_category,
                            "rss_url": rss_url
                        })
                    except Exception as e:
                        st.warning(f"⚠️ خطأ في معالجة خبر: {str(e)}")
                        continue
                
                if news_list:
                    return news_list
                else:
                    st.warning(f"⚠️ لا توجد أخبار تطابق الشروط في: {rss_url}")
                    
            else:
                st.warning(f"⚠️ لا يوجد محتوى في: {rss_url}")
                
        except Exception as e:
            st.warning(f"⚠️ فشل في الوصول لـ {rss_url}: {str(e)}")
            continue
    
    return []

def export_to_word(news_list):
    doc = Document()
    doc.add_heading('تقرير الأخبار', 0)
    
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

# ✅ مصادر الأخبار العامة
general_rss_feeds = {
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

# ✅ مصادر الأخبار العراقية
iraqi_news_sources = {
    "وزارة الداخلية العراقية": {
        "url": "https://moi.gov.iq/",
        "type": "website",
        "rss_options": [
            "https://moi.gov.iq/feed/",
            "https://moi.gov.iq/rss.xml",
            "https://moi.gov.iq/wp-content/rss.xml"
        ]
    },
    "هذا اليوم": {
        "url": "https://hathalyoum.net/",
        "type": "website",
        "rss_options": [
            "https://hathalyoum.net/feed/",
            "https://hathalyoum.net/rss.xml",
            "https://hathalyoum.net/index.php/feed/"
        ]
    },
    "العراق اليوم": {
        "url": "https://iraqtoday.com/",
        "type": "website", 
        "rss_options": [
            "https://iraqtoday.com/feed/",
            "https://iraqtoday.com/rss.xml",
            "https://iraqtoday.com/wp-json/wp/v2/posts"
        ]
    },
    "رئاسة الجمهورية العراقية": {
        "url": "https://presidency.iq/default.aspx",
        "type": "website",
        "rss_options": [
            "https://presidency.iq/feed/",
            "https://presidency.iq/rss.xml",
            "https://presidency.iq/ar/feed/"
        ]
    },
    "الشرق الأوسط": {
        "url": "https://asharq.com/",
        "type": "website",
        "rss_options": [
            "https://asharq.com/feed/",
            "https://asharq.com/rss.xml",
            "https://asharq.com/section/iraq/feed/"
        ]
    },
    "RT Arabic - العراق": {
        "url": "https://arabic.rt.com/focuses/10744-%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82/",
        "type": "website",
        "rss_options": [
            "https://arabic.rt.com/rss/",
            "https://arabic.rt.com/rss/focuses/10744/",
            "https://arabic.rt.com/feeds/iraq.rss"
        ]
    },
    "إندبندنت عربية": {
        "url": "https://www.independentarabia.com/",
        "type": "website",
        "rss_options": [
            "https://www.independentarabia.com/rss",
            "https://www.independentarabia.com/feed/",
            "https://www.independentarabia.com/tags/%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82/feed"
        ]
    },
    "فرانس 24 عربي": {
        "url": "https://www.france24.com/ar/",
        "type": "website",
        "rss_options": [
            "https://www.france24.com/ar/rss",
            "https://www.france24.com/ar/tag/%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82/rss",
            "https://www.france24.com/ar/programs/rss"
        ]
    }
}

# واجهة التحكم
st.sidebar.header("⚙️ إعدادات البحث")

# اختيار نوع المصدر
source_type = st.sidebar.selectbox(
    "🌍 اختر نوع المصدر:",
    ["المصادر العامة", "المصادر العراقية"]
)

if source_type == "المصادر العامة":
    selected_source = st.sidebar.selectbox("🌐 اختر مصدر الأخبار:", list(general_rss_feeds.keys()))
    source_url = general_rss_feeds[selected_source]
    source_info = {"type": "rss", "url": source_url}
else:
    selected_source = st.sidebar.selectbox("🇮🇶 اختر مصدر الأخبار العراقي:", list(iraqi_news_sources.keys()))
    source_info = iraqi_news_sources[selected_source]

keywords_input = st.sidebar.text_input("🔍 كلمات مفتاحية (مفصولة بفواصل):", "")
keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []

category_filter = st.sidebar.selectbox("📁 اختر التصنيف:", ["الكل"] + list(category_keywords.keys()))

date_from = st.sidebar.date_input("📅 من تاريخ:", datetime.today())
date_to = st.sidebar.date_input("📅 إلى تاريخ:", datetime.today())

run = st.sidebar.button("📥 عرض الأخبار", type="primary")

# عرض النتائج الأساسية
col1, col2 = st.columns([2, 1])

with col1:
    if run:
        with st.spinner("🔄 جاري جلب الأخبار..."):
            news = []
            
            if source_type == "المصادر العامة":
                news = fetch_rss_news(
                    selected_source,
                    source_info["url"],
                    keywords,
                    date_from,
                    date_to,
                    category_filter
                )
            else:  # المصادر العراقية
                if source_info.get("rss_options"):
                    # تجربة عدة روابط RSS
                    news = try_multiple_rss_feeds(
                        selected_source,
                        source_info["rss_options"],
                        keywords,
                        date_from,
                        date_to,
                        category_filter
                    )
                
                # إذا لم ينجح أي RSS
                if not news:
                    st.info(f"ℹ️ لم يتم العثور على RSS متاح لـ {selected_source}")
                    st.markdown(f"🔗 **[زيارة {selected_source} مباشرة]({source_info['url']})**")
                    st.markdown("💡 يمكنك زيارة الموقع مباشرة للاطلاع على آخر الأخبار")

        if news:
            st.success(f"✅ تم العثور على {len(news)} خبر من {selected_source}")
            
            # عرض الأخبار
            for i, item in enumerate(news):
                with st.expander(f"📰 {item['title'][:100]}..."):
                    cols = st.columns([1, 3])
                    with cols[0]:
                        if item.get("image"):
                            try:
                                st.image(item["image"], use_column_width=True)
                            except:
                                st.write("🖼️ صورة غير متاحة")
                    
                    with cols[1]:
                        st.markdown(f"**📅 التاريخ:** {item['published'].strftime('%Y-%m-%d %H:%M')}")
                        st.markdown(f"**📁 التصنيف:** {item['category']}")
                        st.markdown(f"**🏢 المصدر:** {item['source']}")
                        st.markdown(f"**📄 الملخص:** {summarize(item['summary'], 50)}")
                        st.markdown(f"**🎯 التحليل العاطفي:** {item['sentiment']}")
                        st.markdown(f"**🔗 [اقرأ المقال كاملاً]({item['link']})**")

        elif run:
            st.warning("❌ لا توجد أخبار بهذه الشروط أو حدث خطأ في جلب البيانات.")

# الشريط الجانبي للإحصائيات
with col2:
    if run and news:
        st.subheader("📊 إحصائيات الأخبار")
        
        # توزيع التصنيفات
        categories = [n['category'] for n in news]
        category_counts = Counter(categories)
        
        st.write("**📁 توزيع التصنيفات:**")
        for cat, count in category_counts.items():
            st.write(f"- {cat}: {count}")
        
        # توزيع المشاعر
        sentiments = [n['sentiment'] for n in news]
        sentiment_counts = Counter(sentiments)
        
        st.write("**🎭 توزيع المشاعر:**")
        for sent, count in sentiment_counts.items():
            st.write(f"- {sent}: {count}")
        
        # أكثر الكلمات تكراراً
        st.write("**🔤 أكثر الكلمات تكراراً:**")
        all_text = " ".join([n['summary'] for n in news])
        words = [word for word in all_text.split() if len(word) > 3]
        word_freq = Counter(words).most_common(10)
        for word, freq in word_freq:
            st.write(f"- **{word}**: {freq}")

# أزرار التصدير
if run and news:
    st.subheader("📥 تصدير البيانات")
    
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        word_file = export_to_word(news)
        st.download_button(
            "📄 تحميل كـ Word",
            data=word_file,
            file_name=f"news_{selected_source}_{datetime.now().strftime('%Y%m%d')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    with col_export2:
        excel_file = export_to_excel(news)
        st.download_button(
            "📊 تحميل كـ Excel",
            data=excel_file,
            file_name=f"news_{selected_source}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# معلومات إضافية
st.sidebar.markdown("---")
st.sidebar.info("""
💡 **ملاحظات:**
- يتم تجربة عدة روابط RSS لكل مصدر عراقي
- بعض المواقع قد تحتاج وقت أطول للاستجابة
- إذا لم يعمل RSS، يمكن زيارة الموقع مباشرة
- استخدم كلمات مفتاحية محددة لتحسين النتائج
""")

st.sidebar.markdown("### 🇮🇶 المصادر العراقية المدعومة:")
st.sidebar.markdown("""
- ✅ وزارة الداخلية العراقية
- ✅ هذا اليوم  
- ✅ العراق اليوم
- ✅ رئاسة الجمهورية العراقية
- ✅ الشرق الأوسط
- ✅ RT Arabic - العراق
- ✅ إندبندنت عربية
- ✅ فرانس 24 عربي
""")
