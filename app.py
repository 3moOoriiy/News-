import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from textblob import TextBlob
from collections import Counter
from docx import Document
import urllib.request
import urllib.parse
import json
import re
import time

st.set_page_config(page_title="📰 أداة الأخبار العربية الذكية", layout="wide")
st.title("🗞️ أداة إدارة وتحليل الأخبار المتطورة (RSS + Web Scraping)")

# التصنيفات المحسّنة
category_keywords = {
    "سياسة": ["رئيس", "وزير", "انتخابات", "برلمان", "سياسة", "حكومة", "نائب", "مجلس", "دولة", "حزب"],
    "رياضة": ["كرة", "لاعب", "مباراة", "دوري", "هدف", "فريق", "بطولة", "رياضة", "ملعب", "تدريب"],
    "اقتصاد": ["سوق", "اقتصاد", "استثمار", "بنك", "مال", "تجارة", "صناعة", "نفط", "غاز", "بورصة"],
    "تكنولوجيا": ["تقنية", "تطبيق", "هاتف", "ذكاء", "برمجة", "إنترنت", "رقمي", "حاسوب", "شبكة", "آيفون"],
    "صحة": ["طب", "مرض", "علاج", "مستشفى", "دواء", "صحة", "طبيب", "فيروس", "لقاح", "وباء"],
    "تعليم": ["تعليم", "جامعة", "مدرسة", "طالب", "دراسة", "كلية", "معهد", "تربية", "أكاديمي", "بحث"]
}

# الدوال المحسّنة
def summarize(text, max_words=30):
    if not text:
        return "لا يوجد ملخص متاح"
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."

def analyze_sentiment(text):
    if not text:
        return "😐 محايد"
    try:
        polarity = TextBlob(text).sentiment.polarity
        if polarity > 0.1:
            return "😃 إيجابي"
        elif polarity < -0.1:
            return "😠 سلبي"
        else:
            return "😐 محايد"
    except:
        return "😐 محايد"

def detect_category(text):
    if not text:
        return "غير مصنّف"
    text_lower = text.lower()
    category_scores = {}
    
    for category, words in category_keywords.items():
        score = sum(1 for word in words if word in text_lower)
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores, key=category_scores.get)
    return "غير مصنّف"

def safe_request(url, timeout=10):
    """طلب آمن مع معالجة الأخطاء"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        st.warning(f"خطأ في الوصول لـ {url}: {str(e)}")
        return None

def extract_news_from_html(html_content, source_name, base_url):
    """استخراج الأخبار من HTML بطريقة ذكية"""
    if not html_content:
        return []
    
    news_list = []
    
    # البحث عن العناوين المحتملة
    title_patterns = [
        r'<h[1-4][^>]*>(.*?)</h[1-4]>',
        r'<title[^>]*>(.*?)</title>',
        r'<a[^>]*title="([^"]+)"',
        r'<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>'
    ]
    
    # البحث عن الروابط
    link_patterns = [
        r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        r'href="([^"]+)"'
    ]
    
    titles = []
    links = []
    
    for pattern in title_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            if isinstance(match, tuple):
                title = match[0] if match[0] else match[1] if len(match) > 1 else ""
            else:
                title = match
            title = re.sub(r'<[^>]+>', '', title).strip()
            if title and len(title) > 10 and len(title) < 200:
                titles.append(title)
    
    for pattern in link_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                link = match[0]
            else:
                link = match
            if link and not link.startswith('#') and not link.startswith('javascript:'):
                if link.startswith('/'):
                    link = base_url + link
                elif not link.startswith('http'):
                    link = base_url + '/' + link
                links.append(link)
    
    # دمج العناوين والروابط
    for i, title in enumerate(titles[:10]):  # أول 10 أخبار
        link = links[i] if i < len(links) else base_url
        
        news_list.append({
            "source": source_name,
            "title": title,
            "summary": title,  # استخدام العنوان كملخص مؤقت
            "link": link,
            "published": datetime.now(),
            "image": "",
            "sentiment": analyze_sentiment(title),
            "category": detect_category(title),
            "extraction_method": "HTML Parsing"
        })
    
    return news_list

def fetch_rss_news(source_name, url, keywords, date_from, date_to, chosen_category):
    """جلب الأخبار من RSS"""
    try:
        feed = feedparser.parse(url)
        news_list = []
        
        if not hasattr(feed, 'entries') or len(feed.entries) == 0:
            return []
        
        for entry in feed.entries:
            try:
                title = entry.get('title', 'بدون عنوان')
                summary = entry.get('summary', entry.get('description', title))
                link = entry.get('link', '')
                published = entry.get('published', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # معالجة التاريخ
                try:
                    published_dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
                except:
                    try:
                        published_dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S%z")
                    except:
                        published_dt = datetime.now()
                
                # فلترة التاريخ
                if not (date_from <= published_dt.date() <= date_to):
                    continue

                # فلترة الكلمات المفتاحية
                full_text = title + " " + summary
                if keywords and not any(k.lower() in full_text.lower() for k in keywords):
                    continue

                # فلترة التصنيف
                auto_category = detect_category(full_text)
                if chosen_category != "الكل" and auto_category != chosen_category:
                    continue

                # البحث عن صورة
                image = ""
                if hasattr(entry, 'media_content') and entry.media_content:
                    image = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image = entry.media_thumbnail[0].get('url', '')

                news_list.append({
                    "source": source_name,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published_dt,
                    "image": image,
                    "sentiment": analyze_sentiment(summary),
                    "category": auto_category,
                    "extraction_method": "RSS"
                })
                
            except Exception as e:
                continue
                
        return news_list
        
    except Exception as e:
        return []

def fetch_website_news(source_name, url, keywords, date_from, date_to, chosen_category):
    """جلب الأخبار من الموقع مباشرة"""
    try:
        st.info(f"🔄 جاري تحليل موقع {source_name}...")
        
        # جلب محتوى الصفحة
        html_content = safe_request(url)
        if not html_content:
            return []
        
        # استخراج الأخبار من HTML
        base_url = url.rstrip('/')
        news_list = extract_news_from_html(html_content, source_name, base_url)
        
        # فلترة النتائج
        filtered_news = []
        for news in news_list:
            # فلترة الكلمات المفتاحية
            full_text = news['title'] + " " + news['summary']
            if keywords and not any(k.lower() in full_text.lower() for k in keywords):
                continue
            
            # فلترة التصنيف
            if chosen_category != "الكل" and news['category'] != chosen_category:
                continue
            
            filtered_news.append(news)
        
        return filtered_news[:10]  # أول 10 أخبار
        
    except Exception as e:
        st.error(f"خطأ في جلب الأخبار من {source_name}: {str(e)}")
        return []

def smart_news_fetcher(source_name, source_info, keywords, date_from, date_to, chosen_category):
    """جالب الأخبار الذكي - يجرب عدة طرق"""
    all_news = []
    
    # المحاولة الأولى: RSS
    if source_info.get("rss_options"):
        st.info("🔄 المحاولة الأولى: البحث عن RSS...")
        for rss_url in source_info["rss_options"]:
            try:
                news = fetch_rss_news(source_name, rss_url, keywords, date_from, date_to, chosen_category)
                if news:
                    st.success(f"✅ تم العثور على {len(news)} خبر من RSS: {rss_url}")
                    all_news.extend(news)
                    break
            except:
                continue
    
    # المحاولة الثانية: تحليل الموقع مباشرة
    if not all_news:
        st.info("🔄 المحاولة الثانية: تحليل الموقع مباشرة...")
        website_news = fetch_website_news(source_name, source_info["url"], keywords, date_from, date_to, chosen_category)
        if website_news:
            st.success(f"✅ تم استخراج {len(website_news)} خبر من الموقع مباشرة")
            all_news.extend(website_news)
    
    # إزالة المكرر
    seen_titles = set()
    unique_news = []
    for news in all_news:
        if news['title'] not in seen_titles:
            seen_titles.add(news['title'])
            unique_news.append(news)
    
    return unique_news

def export_to_word(news_list):
    doc = Document()
    doc.add_heading('تقرير الأخبار المجمعة', 0)
    doc.add_paragraph(f'تاريخ التقرير: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    doc.add_paragraph(f'عدد الأخبار: {len(news_list)}')
    doc.add_paragraph('---')
    
    for i, news in enumerate(news_list, 1):
        doc.add_heading(f'{i}. {news["title"]}', level=2)
        doc.add_paragraph(f"المصدر: {news['source']}")
        doc.add_paragraph(f"التصنيف: {news['category']}")
        doc.add_paragraph(f"التاريخ: {news['published'].strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"طريقة الاستخراج: {news.get('extraction_method', 'غير محدد')}")
        doc.add_paragraph(f"التحليل العاطفي: {news['sentiment']}")
        doc.add_paragraph(f"الملخص: {news['summary']}")
        doc.add_paragraph(f"الرابط: {news['link']}")
        doc.add_paragraph('---')
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def export_to_excel(news_list):
    df = pd.DataFrame(news_list)
    # ترتيب الأعمدة
    columns_order = ['source', 'title', 'category', 'sentiment', 'published', 'summary', 'link', 'extraction_method']
    df = df.reindex(columns=[col for col in columns_order if col in df.columns])
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='الأخبار')
    buffer.seek(0)
    return buffer

# مصادر الأخبار المحسّنة
general_rss_feeds = {
    "BBC عربي": "http://feeds.bbci.co.uk/arabic/rss.xml",
    "الجزيرة": "https://www.aljazeera.net/aljazeerarss/ar/home",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "France24 عربي": "https://www.france24.com/ar/rss",
    "سكاي نيوز عربية": "https://www.skynewsarabia.com/web/rss",
    "عربي21": "https://arabi21.com/feed"
}

iraqi_news_sources = {
    "وزارة الداخلية العراقية": {
        "url": "https://moi.gov.iq/",
        "type": "website",
        "rss_options": [
            "https://moi.gov.iq/feed/",
            "https://moi.gov.iq/rss.xml"
        ]
    },
    "هذا اليوم": {
        "url": "https://hathalyoum.net/",
        "type": "website",
        "rss_options": [
            "https://hathalyoum.net/feed/",
            "https://hathalyoum.net/rss.xml"
        ]
    },
    "العراق اليوم": {
        "url": "https://iraqtoday.com/",
        "type": "website",
        "rss_options": [
            "https://iraqtoday.com/feed/",
            "https://iraqtoday.com/rss.xml"
        ]
    },
    "رئاسة الجمهورية العراقية": {
        "url": "https://presidency.iq/default.aspx",
        "type": "website",
        "rss_options": [
            "https://presidency.iq/feed/",
            "https://presidency.iq/rss.xml"
        ]
    },
    "الشرق الأوسط": {
        "url": "https://asharq.com/",
        "type": "website",
        "rss_options": [
            "https://asharq.com/feed/",
            "https://asharq.com/rss.xml"
        ]
    },
    "RT Arabic - العراق": {
        "url": "https://arabic.rt.com/focuses/10744-%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82/",
        "type": "website",
        "rss_options": [
            "https://arabic.rt.com/rss/"
        ]
    },
    "إندبندنت عربية": {
        "url": "https://www.independentarabia.com/",
        "type": "website",
        "rss_options": [
            "https://www.independentarabia.com/rss"
        ]
    },
    "فرانس 24 عربي": {
        "url": "https://www.france24.com/ar/",
        "type": "website",
        "rss_options": [
            "https://www.france24.com/ar/rss"
        ]
    }
}

# واجهة المستخدم المحسّنة
st.sidebar.header("⚙️ إعدادات البحث المتقدم")

# اختيار نوع المصدر
source_type = st.sidebar.selectbox(
    "🌍 اختر نوع المصدر:",
    ["المصادر العامة", "المصادر العراقية"],
    help="المصادر العامة تعتمد على RSS، المصادر العراقية تستخدم تقنيات متقدمة"
)

if source_type == "المصادر العامة":
    selected_source = st.sidebar.selectbox("🌐 اختر مصدر الأخبار:", list(general_rss_feeds.keys()))
    source_url = general_rss_feeds[selected_source]
    source_info = {"type": "rss", "url": source_url}
else:
    selected_source = st.sidebar.selectbox("🇮🇶 اختر مصدر الأخبار العراقي:", list(iraqi_news_sources.keys()))
    source_info = iraqi_news_sources[selected_source]

# إعدادات البحث
keywords_input = st.sidebar.text_input(
    "🔍 كلمات مفتاحية (مفصولة بفواصل):", 
    "",
    help="مثال: سياسة، اقتصاد، بغداد"
)
keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []

category_filter = st.sidebar.selectbox(
    "📁 اختر التصنيف:", 
    ["الكل"] + list(category_keywords.keys()),
    help="فلترة الأخبار حسب التصنيف"
)

# إعدادات التاريخ
col_date1, col_date2 = st.sidebar.columns(2)
with col_date1:
    date_from = st.date_input("📅 من تاريخ:", datetime.today() - timedelta(days=7))
with col_date2:
    date_to = st.date_input("📅 إلى تاريخ:", datetime.today())

# خيارات متقدمة
with st.sidebar.expander("⚙️ خيارات متقدمة"):
    max_news = st.slider("عدد الأخبار الأقصى:", 5, 50, 20)
    include_sentiment = st.checkbox("تحليل المشاعر", True)
    include_categorization = st.checkbox("التصنيف التلقائي", True)

run = st.sidebar.button("📥 جلب الأخبار", type="primary", help="ابدأ عملية جلب وتحليل الأخبار")

# عرض النتائج
if run:
    with st.spinner("🤖 جاري تشغيل الذكاء الاصطناعي لجلب الأخبار..."):
        start_time = time.time()
        
        if source_type == "المصادر العامة":
            news = fetch_rss_news(
                selected_source,
                source_info["url"],
                keywords,
                date_from,
                date_to,
                category_filter
            )
        else:
            news = smart_news_fetcher(
                selected_source,
                source_info,
                keywords,
                date_from,
                date_to,
                category_filter
            )
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
    
    if news:
        st.success(f"🎉 تم جلب {len(news)} خبر من {selected_source} في {processing_time} ثانية")
        
        # إحصائيات سريعة
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📰 إجمالي الأخبار", len(news))
        with col2:
            categories = [n['category'] for n in news]
            st.metric("📁 أكثر تصنيف", Counter(categories).most_common(1)[0][0] if categories else "غير محدد")
        with col3:
            positive_news = len([n for n in news if "إيجابي" in n['sentiment']])
            st.metric("😃 أخبار إيجابية", positive_news)
        with col4:
            st.metric("⏱️ وقت المعالجة", f"{processing_time}s")
        
        # عرض الأخبار
        st.subheader("📑 الأخبار المجمعة")
        
        for i, item in enumerate(news[:max_news], 1):
            with st.container():
                st.markdown(f"### {i}. 📰 {item['title']}")
                
                col_info, col_content = st.columns([1, 2])
                
                with col_info:
                    st.markdown(f"**🏢 المصدر:** {item['source']}")
                    st.markdown(f"**📅 التاريخ:** {item['published'].strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**📁 التصنيف:** {item['category']}")
                    st.markdown(f"**🎭 المشاعر:** {item['sentiment']}")
                    st.markdown(f"**🔧 الطريقة:** {item.get('extraction_method', 'غير محدد')}")
                
                with col_content:
                    st.markdown(f"**📄 الملخص:** {summarize(item['summary'], 40)}")
                    st.markdown(f"**🔗 [قراءة المقال كاملاً ↗]({item['link']})**")
                
                if item.get('image'):
                    st.image(item['image'], caption=item['title'], use_column_width=True)
                
                st.markdown("---")
        
        # تصدير البيانات
        st.subheader("📤 تصدير البيانات")
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            word_file = export_to_word(news)
            st.download_button(
                "📄 تحميل Word",
                data=word_file,
                file_name=f"اخبار_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        with col_export2:
            excel_file = export_to_excel(news)
            st.download_button(
                "📊 تحميل Excel",
                data=excel_file,
                file_name=f"اخبار_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col_export3:
            json_data = json.dumps(news, ensure_ascii=False, default=str, indent=2)
            st.download_button(
                "💾 تحميل JSON",
                data=json_data.encode('utf-8'),
                file_name=f"اخبار_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
        
        # تحليلات متقدمة
        with st.expander("📊 تحليلات متقدمة"):
            col_analysis1, col_analysis2 = st.columns(2)
            
            with col_analysis1:
                st.subheader("📁 توزيع التصنيفات")
                categories = [n['category'] for n in news]
                category_counts = Counter(categories)
                
                for cat, count in category_counts.most_common():
                    percentage = (count / len(news)) * 100
                    st.write(f"• **{cat}**: {count} ({percentage:.1f}%)")
            
            with col_analysis2:
                st.subheader("🎭 تحليل المشاعر")
                sentiments = [n['sentiment'] for n in news]
                sentiment_counts = Counter(sentiments)
                
                for sent, count in sentiment_counts.items():
                    percentage = (count / len(news)) * 100
                    st.write(f"• **{sent}**: {count} ({percentage:.1f}%)")
            
            st.subheader("🔤 أكثر الكلمات تكراراً")
            all_text = " ".join([n['title'] + " " + n['summary'] for n in news])
            # تنظيف النص
            words = re.findall(r'\b[أ-ي]{3,}\b', all_text)  # كلمات عربية فقط
            word_freq = Counter(words).most_common(15)
            
            if word_freq:
                cols = st.columns(3)
                for i, (word, freq) in enumerate(word_freq):
                    with cols[i % 3]:
                        st.write(f"**{word}**: {freq} مرة")
    
    else:
        st.warning("❌ لم يتم العثور على أخبار بالشروط المحددة")
        st.info("💡 جرب توسيع نطاق التاريخ أو تغيير الكلمات المفتاحية")
        st.markdown(f"🔗 **[زيارة {selected_source} مباشرة]({source_info['url']})**")

# معلومات في الشريط الجانبي
st.sidebar.markdown("---")
st.sidebar.info("""
🚀 **تقنيات متقدمة:**
- جلب RSS تلقائي
- تحليل مواقع الويب
- تصنيف ذكي للأخبار
- تحليل المشاعر
- إزالة المحتوى المكرر
""")

st.sidebar.success("✅ نظام ذكي متطور لجمع الأخبار!")

# معلومات تقنية
with st.expander("ℹ️ معلومات تقنية"):
    st.markdown("""
    ### 🛠️ التقنيات المستخدمة:
    - **RSS Parsing**: لجلب الأخبار من المصادر التقليدية
    - **HTML Analysis**: لتحليل مواقع الويب مباشرة  
    - **Smart Categorization**: تصنيف تلقائي للأخبار
    - **Sentiment Analysis**: تحليل المشاعر باستخدام TextBlob
    - **Regex Extraction**: استخراج العناوين والروابط بالتعبيرات النمطية
    - **Duplicate Removal**: إزالة الأخبار المكررة تلقائياً
    
    ### 📈 المزايا الجديدة:
    - **Multi-Method Fetching**: جلب الأخبار بعدة طرق
    - **Fallback System**: نظام احتياطي عند فشل RSS
    - **Advanced Filtering**: فلترة متقدمة بالكلمات والتصنيفات
    - **Real-time Processing**: معالجة فورية للبيانات
    - **Export Options**: تصدير بصيغ متعددة (Word, Excel, JSON)
    
    ### 🎯 كيف يعمل النظام:
    1. **محاولة RSS أولاً**: البحث عن feeds متاحة
    2. **تحليل HTML**: استخراج المحتوى من الصفحة مباشرة
    3. **معالجة ذكية**: تنظيف وتصنيف البيانات
    4. **إزالة التكرار**: ضمان عدم تكرار الأخبار
    5. **تحليل متقدم**: استخراج الإحصائيات والمشاعر
    """)
