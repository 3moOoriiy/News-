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
import ssl
from bs4 import BeautifulSoup

# تعطيل تحقق SSL للتعامل مع المواقع الحكومية
ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(page_title=":newspaper: أداة الأخبار العربية الذكية", layout="wide")
st.title(":rolled_up_newspaper: أداة إدارة وتحليل الأخبار المتطورة (RSS + Web Scraping)")

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
        return ":neutral_face: محايد"
    try:
        polarity = TextBlob(text).sentiment.polarity
        if polarity > 0.1:
            return ":smiley: إيجابي"
        elif polarity < -0.1:
            return ":angry: سلبي"
        else:
            return ":neutral_face: محايد"
    except:
        return ":neutral_face: محايد"

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
    """طلب آمن مع معالجة الأخطاء للمواقع الحكومية"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        st.warning(f"خطأ في الوصول لـ {url}: {str(e)}")
        return None

def extract_news_from_html(html_content, source_name, base_url):
    """استخراج الأخبار من HTML بطريقة ذكية للمواقع الحكومية"""
    if not html_content:
        return []
    
    news_list = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # أنماط مختلفة للمواقع الحكومية
    if "moi.gov.iq" in base_url:  # وزارة الداخلية
        news_items = soup.find_all('div', class_=re.compile('news-item|post-item'))
    elif "presidency.iq" in base_url:  # رئاسة الجمهورية
        news_items = soup.find_all('div', class_=re.compile('news|article'))
    else:
        news_items = soup.find_all(['article', 'div'], class_=re.compile('news|post|article'))
    
    for item in news_items[:10]:  # أول 10 أخبار فقط
        try:
            title = item.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a']).get_text(strip=True)
            link = item.find('a')['href'] if item.find('a') else base_url
            
            # معالجة الروابط النسبية
            if link.startswith('/'):
                link = base_url + link
            elif not link.startswith('http'):
                link = base_url + '/' + link
                
            summary = item.find('p').get_text(strip=True) if item.find('p') else title
            image = item.find('img')['src'] if item.find('img') else ""
            
            news_list.append({
                "source": source_name,
                "title": title,
                "summary": summary,
                "link": link,
                "published": datetime.now(),
                "image": image,
                "sentiment": analyze_sentiment(summary),
                "category": detect_category(title + " " + summary),
                "extraction_method": "HTML Parsing (Gov)"
            })
        except Exception as e:
            continue
    
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
                if keywords:
                    if isinstance(keywords, str):
                        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
                    
                    if not any(re.search(r'\b{}\b'.format(re.escape(k.lower())), full_text.lower()) for k in keywords):
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

def fetch_government_news(source_name, source_info, keywords, date_from, date_to, chosen_category):
    """دالة متخصصة للمواقع الحكومية"""
    try:
        st.info(f"جارٍ تحليل الموقع الحكومي: {source_name}...")
        html_content = safe_request(source_info["url"])
        if not html_content:
            return []
            
        base_url = source_info["url"].rstrip('/')
        news_list = extract_news_from_html(html_content, source_name, base_url)
        
        # فلترة النتائج
        filtered_news = []
        for news in news_list:
            # فلترة الكلمات المفتاحية
            full_text = news['title'] + " " + news['summary']
            if keywords:
                if isinstance(keywords, str):
                    keywords = [k.strip() for k in keywords.split(",") if k.strip()]
                
                if not any(re.search(r'\b{}\b'.format(re.escape(k.lower())), full_text.lower()) for k in keywords):
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
    
    # المحاولة الأولى: RSS (إذا كان متاحاً)
    if source_info.get("rss_options"):
        st.info(":arrows_counterclockwise: المحاولة الأولى: البحث عن RSS...")
        for rss_url in source_info["rss_options"]:
            try:
                news = fetch_rss_news(source_name, rss_url, keywords, date_from, date_to, chosen_category)
                if news:
                    st.success(f":white_check_mark: تم العثور على {len(news)} خبر من RSS: {rss_url}")
                    all_news.extend(news)
                    break
            except:
                continue
    
    # المحاولة الثانية: تحليل الموقع الحكومي مباشرة
    if not all_news or source_info.get("type") == "government":
        all_news.extend(fetch_government_news(source_name, source_info, keywords, date_from, date_to, chosen_category))
    
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
        "type": "government",
        "rss_options": []  # لا يوجد RSS فعال
    },
    "رئاسة الجمهورية العراقية": {
        "url": "https://presidency.iq/",
        "type": "government",
        "rss_options": []
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
    }
}

# واجهة المستخدم
st.sidebar.header(":gear: إعدادات البحث المتقدم")

# اختيار نوع المصدر
source_type = st.sidebar.selectbox(
    ":earth_africa: اختر نوع المصدر:",
    ["المصادر العامة", "المصادر العراقية"]
)

if source_type == "المصادر العامة":
    selected_source = st.sidebar.selectbox(":globe_with_meridians: اختر مصدر الأخبار:", list(general_rss_feeds.keys()))
    source_url = general_rss_feeds[selected_source]
    source_info = {"type": "rss", "url": source_url}
else:
    selected_source = st.sidebar.selectbox(":flag-iq: اختر مصدر الأخبار العراقي:", list(iraqi_news_sources.keys()))
    source_info = iraqi_news_sources[selected_source]

# إعدادات البحث
keywords_input = st.sidebar.text_input(
    ":mag: كلمات مفتاحية (مفصولة بفواصل):", 
    "",
    help="أدخل أي كلمات تريد البحث عنها"
)

category_filter = st.sidebar.selectbox(
    ":file_folder: اختر التصنيف:", 
    ["الكل"] + list(category_keywords.keys())
)

# إعدادات التاريخ
col_date1, col_date2 = st.sidebar.columns(2)
with col_date1:
    date_from = st.date_input(":date: من تاريخ:", datetime.today() - timedelta(days=7))
with col_date2:
    date_to = st.date_input(":date: إلى تاريخ:", datetime.today())

# خيارات متقدمة
with st.sidebar.expander(":gear: خيارات متقدمة"):
    max_news = st.slider("عدد الأخبار الأقصى:", 5, 50, 20)
    image_size = st.slider("حجم الصور:", 100, 500, 200)

run = st.sidebar.button(":inbox_tray: جلب الأخبار", type="primary")

# عرض النتائج
if run:
    with st.spinner(":robot_face: جاري جمع الأخبار..."):
        start_time = time.time()
        
        if source_type == "المصادر العامة":
            news = fetch_rss_news(
                selected_source,
                source_info["url"],
                keywords_input,
                date_from,
                date_to,
                category_filter
            )
        else:
            news = smart_news_fetcher(
                selected_source,
                source_info,
                keywords_input,
                date_from,
                date_to,
                category_filter
            )
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
    
    if news:
        st.success(f":tada: تم جلب {len(news)} خبر في {processing_time} ثانية")
        
        # عرض الأخبار
        st.subheader(":bookmark_tabs: الأخبار المجمعة")
        
        for i, item in enumerate(news[:max_news], 1):
            with st.container():
                st.markdown(f"### {i}. :newspaper: {item['title']}")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**المصدر:** {item['source']}")
                    st.markdown(f"**التاريخ:** {item['published'].strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**التصنيف:** {item['category']}")
                    st.markdown(f"**المشاعر:** {item['sentiment']}")
                
                with col2:
                    st.markdown(f"**الملخص:** {summarize(item['summary'], 40)}")
                    st.markdown(f"[قراءة المزيد ↗]({item['link']})")
                
                if item.get('image'):
                    st.image(item['image'], width=image_size)
                
                st.markdown("---")
        
        # تصدير البيانات
        st.subheader(":outbox_tray: تصدير البيانات")
        col1, col2 = st.columns(2)
        with col1:
            word_file = export_to_word(news)
            st.download_button("تحميل Word", word_file, "الأخبار.docx")
        with col2:
            excel_file = export_to_excel(news)
            st.download_button("تحميل Excel", excel_file, "الأخبار.xlsx")
    
    else:
        st.warning(":x: لم يتم العثور على أخبار")
        st.info(f":link: [زيارة الموقع مباشرة ↗]({source_info['url']})")

# معلومات إضافية
st.sidebar.markdown("---")
st.sidebar.info("""
:bulb: **نصائح للبحث:**
- للمواقع الحكومية: جرب كلمات مثل "وزير", "قرار", "اجتماع"
- استخدم كلمات مفتاحية محددة لتحسين النتائج
""")
