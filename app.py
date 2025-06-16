import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from collections import Counter
from docx import Document
import urllib.request
import urllib.parse
import json
import re
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import arabic_reshaper
from bidi.algorithm import get_display
import requests
from requests.exceptions import RequestException
from transformers import pipeline

st.set_page_config(page_title=":newspaper: أداة الأخبار العربية الذكية", layout="wide")
st.title(":rolled_up_newspaper: أداة إدارة وتحليل الأخبار المتطورة (RSS + Web Scraping)")

# التخزين المؤقت لتحسين الأداء
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_cached_rss(url):
    return feedparser.parse(url)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_html_content(url):
    return safe_request(url)

# التصنيفات المحسّنة مع أوزان للكلمات
category_keywords = {
    "سياسة": {
        "وزير": 3, "رئيس": 3, "انتخابات": 2, "برلمان": 2, "سياسة": 1,
        "حكومة": 2, "نائب": 2, "مجلس": 2, "دولة": 1, "حزب": 2
    },
    "رياضة": {
        "كرة": 3, "لاعب": 2, "مباراة": 3, "دوري": 2, "هدف": 2,
        "فريق": 2, "بطولة": 2, "رياضة": 1, "ملعب": 1, "تدريب": 1
    },
    "اقتصاد": {
        "سوق": 2, "اقتصاد": 3, "استثمار": 2, "بنك": 2, "مال": 1,
        "تجارة": 2, "صناعة": 2, "نفط": 3, "غاز": 2, "بورصة": 2
    },
    "تكنولوجيا": {
        "تقنية": 3, "تطبيق": 2, "هاتف": 2, "ذكاء": 2, "برمجة": 2,
        "إنترنت": 1, "رقمي": 1, "حاسوب": 2, "شبكة": 1, "آيفون": 1
    },
    "صحة": {
        "طب": 3, "مرض": 2, "علاج": 2, "مستشفى": 2, "دواء": 2,
        "صحة": 1, "طبيب": 2, "فيروس": 2, "لقاح": 2, "وباء": 2
    },
    "تعليم": {
        "تعليم": 3, "جامعة": 2, "مدرسة": 2, "طالب": 1, "دراسة": 1,
        "كلية": 2, "معهد": 2, "تربية": 1, "أكاديمي": 1, "بحث": 1
    }
}

# تحسين التعامل مع التواريخ
def parse_date(date_str):
    date_formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d %b %Y %H:%M:%S"
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    
    # محاولة استخراج التاريخ من النص
    match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
    if match:
        return datetime.strptime(match.group(), "%Y-%m-%d")
    
    match = re.search(r'\d{2}/\d{2}/\d{4}', date_str)
    if match:
        return datetime.strptime(match.group(), "%d/%m/%Y")
    
    return datetime.now()

# الدوال المحسّنة
def summarize(text, max_words=30):
    if not text:
        return "لا يوجد ملخص متاح"
    
    # تنظيف النص من الوسوم HTML
    clean_text = re.sub(r'<[^>]+>', '', text)
    words = clean_text.split()
    
    if len(words) <= max_words:
        return clean_text
    
    return " ".join(words[:max_words]) + "..."

# تحسين تحليل المشاعر للغة العربية
sentiment_analyzer = None

def get_sentiment_analyzer():
    global sentiment_analyzer
    if sentiment_analyzer is None:
        try:
            sentiment_analyzer = pipeline('sentiment-analysis', model='CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment')
        except:
            sentiment_analyzer = None
    return sentiment_analyzer

def analyze_sentiment(text):
    if not text:
        return ":neutral_face: محايد"
    
    try:
        analyzer = get_sentiment_analyzer()
        if analyzer:
            result = analyzer(text[:512])  # تحليل أول 512 حرف فقط
            label = result[0]['label']
            if label == 'positive':
                return ":smiley: إيجابي"
            elif label == 'negative':
                return ":angry: سلبي"
        
        # الطريقة الاحتياطية إذا لم يعمل النموذج
        positive_words = ["إيجابي", "ممتاز", "جيد", "رائع", "نجاح"]
        negative_words = ["سلبي", "سيء", "فشل", "مشكلة", "خسارة"]
        
        text_lower = text.lower()
        positive_count = sum(text_lower.count(word) for word in positive_words)
        negative_count = sum(text_lower.count(word) for word in negative_words)
        
        if positive_count > negative_count:
            return ":smiley: إيجابي"
        elif negative_count > positive_count:
            return ":angry: سلبي"
        return ":neutral_face: محايد"
    except:
        return ":neutral_face: محايد"

def detect_category(text):
    if not text:
        return "غير مصنّف"
    
    text_lower = text.lower()
    category_scores = {}
    
    for category, words in category_keywords.items():
        score = 0
        for word, weight in words.items():
            if word in text_lower:
                score += weight
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores, key=category_scores.get)
    return "غير مصنّف"

def safe_request(url, timeout=10, max_retries=3):
    """طلب آمن مع معالجة الأخطاء وإعادة المحاولة"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # التحقق من نوع المحتوى
            content_type = response.headers.get('Content-Type', '')
            if 'charset' in content_type:
                charset = content_type.split('charset=')[-1]
                return response.content.decode(charset, errors='ignore')
            return response.text
            
        except RequestException as e:
            st.warning(f"محاولة {attempt+1}/{max_retries} - خطأ في الوصول لـ {url}: {str(e)}")
            time.sleep(2)  # انتظار قبل إعادة المحاولة
    
    st.error(f"فشل جميع المحاولات للوصول لـ {url}")
    return None

def extract_news_from_html(html_content, source_name, base_url):
    """استخراج الأخبار من HTML باستخدام BeautifulSoup"""
    if not html_content:
        return []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        news_list = []
        
        # البحث عن عناصر الأخبار الشائعة
        news_elements = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'(news|article|item|post)', re.IGNORECASE))
        
        for element in news_elements[:15]:  # الحد الأقصى 15 عنصرًا
            try:
                # استخراج العنوان
                title_element = element.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'(title|heading|name)', re.IGNORECASE))
                title = title_element.get_text(strip=True) if title_element else ""
                
                # استخراج الرابط
                link = ""
                link_element = element.find('a', href=True)
                if link_element:
                    link = link_element['href']
                    if link.startswith('/'):
                        link = base_url + link
                    elif not link.startswith('http'):
                        link = base_url + '/' + link
                
                # استخراج الملخص
                summary_element = element.find(['p', 'div'], class_=re.compile(r'(summary|excerpt|description)', re.IGNORECASE))
                summary = summary_element.get_text(strip=True) if summary_element else title
                
                # استخراج الصورة
                image = ""
                img_element = element.find('img', src=True)
                if img_element and 'src' in img_element.attrs:
                    image = img_element['src']
                    if image.startswith('/'):
                        image = base_url + image
                    elif not image.startswith('http'):
                        image = base_url + '/' + image
                
                # استخراج التاريخ
                date_element = element.find(['time', 'span'], class_=re.compile(r'(date|time|published)', re.IGNORECASE))
                date_str = date_element['datetime'] if date_element and 'datetime' in date_element.attrs else date_element.get_text(strip=True) if date_element else ""
                published = parse_date(date_str) if date_str else datetime.now()
                
                if title and len(title) > 10:
                    news_list.append({
                        "source": source_name,
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "published": published,
                        "image": image,
                        "sentiment": analyze_sentiment(title + " " + summary),
                        "category": detect_category(title + " " + summary),
                        "extraction_method": "HTML Parsing"
                    })
                    
            except Exception as e:
                continue
        
        return news_list
        
    except Exception as e:
        st.error(f"خطأ في تحليل HTML: {str(e)}")
        return []

def fetch_rss_news(source_name, url, keywords, date_from, date_to, chosen_category):
    """جلب الأخبار من RSS مع تحسينات"""
    try:
        feed = fetch_cached_rss(url)
        news_list = []
        
        if not hasattr(feed, 'entries') or len(feed.entries) == 0:
            return []
        
        for entry in feed.entries:
            try:
                title = entry.get('title', 'بدون عنوان')
                summary = entry.get('summary', entry.get('description', title))
                link = entry.get('link', '')
                published = entry.get('published', entry.get('updated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
                # معالجة التاريخ
                published_dt = parse_date(published)
                
                # فلترة التاريخ
                if not (date_from <= published_dt.date() <= date_to):
                    continue

                # فلترة الكلمات المفتاحية
                full_text = title + " " + summary
                if keywords:
                    if isinstance(keywords, str):
                        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
                    
                    # البحث عن أي كلمة مفتاحية في النص
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
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get('type', '').startswith('image'):
                            image = enc.get('href', '')
                            break

                news_list.append({
                    "source": source_name,
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published_dt,
                    "image": image,
                    "sentiment": analyze_sentiment(full_text),
                    "category": auto_category,
                    "extraction_method": "RSS"
                })
                
            except Exception as e:
                continue
                
        return news_list
        
    except Exception as e:
        st.error(f"خطأ في جلب RSS: {str(e)}")
        return []

def fetch_website_news(source_name, url, keywords, date_from, date_to, chosen_category):
    """جلب الأخبار من الموقع مباشرة مع تحسينات"""
    try:
        progress = st.progress(0, text=f"جاري تحليل موقع {source_name}...")
        
        # جلب محتوى الصفحة
        html_content = fetch_html_content(url)
        progress.progress(30)
        
        if not html_content:
            return []
        
        # استخراج الأخبار من HTML
        base_url = url.rstrip('/')
        news_list = extract_news_from_html(html_content, source_name, base_url)
        progress.progress(70)
        
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
            
            # فلترة التاريخ
            if not (date_from <= news['published'].date() <= date_to):
                continue
            
            filtered_news.append(news)
        
        progress.progress(100)
        return filtered_news[:15]  # أول 15 خبرًا
        
    except Exception as e:
        st.error(f"خطأ في جلب الأخبار من {source_name}: {str(e)}")
        return []

def smart_news_fetcher(source_name, source_info, keywords, date_from, date_to, chosen_category):
    """جالب الأخبار الذكي - يجرب عدة طرق"""
    all_news = []
    
    # المحاولة الأولى: RSS
    if source_info.get("rss_options"):
        for rss_url in source_info["rss_options"]:
            try:
                news = fetch_rss_news(source_name, rss_url, keywords, date_from, date_to, chosen_category)
                if news:
                    st.success(f":white_check_mark: تم العثور على {len(news)} خبر من RSS: {rss_url}")
                    all_news.extend(news)
                    break
            except:
                continue
    
    # المحاولة الثانية: تحليل الموقع مباشرة
    if not all_news:
        website_news = fetch_website_news(source_name, source_info["url"], keywords, date_from, date_to, chosen_category)
        if website_news:
            st.success(f":white_check_mark: تم استخراج {len(website_news)} خبر من الموقع مباشرة")
            all_news.extend(website_news)
    
    # إزالة المكرر
    seen_titles = set()
    unique_news = []
    for news in all_news:
        title = news['title'].strip()[:100]  # النظر فقط في أول 100 حرف من العنوان
        if title not in seen_titles:
            seen_titles.add(title)
            unique_news.append(news)
    
    return unique_news

def export_to_word(news_list):
    doc = Document()
    doc.add_heading('تقرير الأخبار المجمعة', 0)
    
    # إعداد المستند للغة العربية
    section = doc.sections[0]
    section.orientation = 1  # اتجاه الصفحة عمودي
    
    # إضافة محتوى التقرير
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
    # تحضير البيانات للتصدير
    data = []
    for news in news_list:
        data.append({
            "المصدر": news["source"],
            "العنوان": news["title"],
            "التصنيف": news["category"],
            "المشاعر": news["sentiment"],
            "التاريخ": news["published"].strftime("%Y-%m-%d %H:%M:%S"),
            "الملخص": news["summary"],
            "الرابط": news["link"],
            "طريقة الاستخراج": news.get("extraction_method", "غير محدد")
        })
    
    df = pd.DataFrame(data)
    
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
st.sidebar.header(":gear: إعدادات البحث المتقدم")

# اختيار نوع المصدر
source_type = st.sidebar.selectbox(
    ":earth_africa: اختر نوع المصدر:",
    ["المصادر العامة", "المصادر العراقية"],
    help="المصادر العامة تعتمد على RSS، المصادر العراقية تستخدم تقنيات متقدمة"
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
    help="يمكنك إدخال أي كلمات تريد البحث عنها"
)
keywords = keywords_input  # سيتم معالجتها في الدوال

category_filter = st.sidebar.selectbox(
    ":file_folder: اختر التصنيف:", 
    ["الكل"] + list(category_keywords.keys()),
    help="فلترة الأخبار حسب التصنيف"
)

# إعدادات التاريخ
col_date1, col_date2 = st.sidebar.columns(2)
with col_date1:
    date_from = st.date_input(":date: من تاريخ:", datetime.today() - timedelta(days=7))
with col_date2:
    date_to = st.date_input(":date: إلى تاريخ:", datetime.today())

# خيارات متقدمة
with st.sidebar.expander(":gear: خيارات متقدمة"):
    max_news = st.slider("عدد الأخبار الأقصى:", 5, 100, 20)
    include_sentiment = st.checkbox("تحليل المشاعر", True)
    include_categorization = st.checkbox("التصنيف التلقائي", True)
    image_size = st.slider("حجم الصور:", 100, 500, 200)

run = st.sidebar.button(":inbox_tray: جلب الأخبار", type="primary", help="ابدأ عملية جلب وتحليل الأخبار")

# عرض النتائج
if run:
    with st.spinner(":robot_face: جاري تشغيل الذكاء الاصطناعي لجلب الأخبار..."):
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
        st.success(f":tada: تم جلب {len(news)} خبر من {selected_source} في {processing_time} ثانية")
        
        # إحصائيات سريعة
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(":newspaper: إجمالي الأخبار", len(news))
        with col2:
            categories = [n['category'] for n in news]
            st.metric(":file_folder: أكثر تصنيف", Counter(categories).most_common(1)[0][0] if categories else "غير محدد")
        with col3:
            positive_news = len([n for n in news if "إيجابي" in n['sentiment']])
            st.metric(":smiley: أخبار إيجابية", positive_news)
        with col4:
            st.metric(":stopwatch: وقت المعالجة", f"{processing_time}s")
        
        # عرض الأخبار
        st.subheader(":bookmark_tabs: الأخبار المجمعة")
        
        for i, item in enumerate(news[:max_news], 1):
            with st.container():
                st.markdown(f"### {i}. :newspaper: {item['title']}")
                
                col_info, col_content = st.columns([1, 2])
                
                with col_info:
                    st.markdown(f"**:office: المصدر:** {item['source']}")
                    st.markdown(f"**:date: التاريخ:** {item['published'].strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**:file_folder: التصنيف:** {item['category']}")
                    st.markdown(f"**:performing_arts: المشاعر:** {item['sentiment']}")
                    st.markdown(f"**:wrench: الطريقة:** {item.get('extraction_method', 'غير محدد')}")
                
                with col_content:
                    st.markdown(f"**:page_facing_up: الملخص:** {summarize(item['summary'], 40)}")
                    st.markdown(f"**:link: [قراءة المقال كاملاً ↗]({item['link']})**")
                
                if item.get('image'):
                    try:
                        st.image(item['image'], caption=item['title'], width=image_size)
                    except:
                        st.warning("تعذر تحميل الصورة")
                
                st.markdown("---")
        
        # تصدير البيانات
        st.subheader(":outbox_tray: تصدير البيانات")
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            word_file = export_to_word(news)
            st.download_button(
                ":page_facing_up: تحميل Word",
                data=word_file,
                file_name=f"اخبار_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        with col_export2:
            excel_file = export_to_excel(news)
            st.download_button(
                ":bar_chart: تحميل Excel",
                data=excel_file,
                file_name=f"اخبار_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col_export3:
            json_data = json.dumps(news, ensure_ascii=False, default=str, indent=2)
            st.download_button(
                ":floppy_disk: تحميل JSON",
                data=json_data.encode('utf-8'),
                file_name=f"اخبار_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
        
        # تحليلات متقدمة
        with st.expander(":bar_chart: تحليلات متقدمة"):
            col_analysis1, col_analysis2 = st.columns(2)
            
            with col_analysis1:
                st.subheader(":file_folder: توزيع التصنيفات")
                categories = [n['category'] for n in news]
                category_counts = Counter(categories)
                
                for cat, count in category_counts.most_common():
                    percentage = (count / len(news)) * 100
                    st.write(f"• **{cat}**: {count} ({percentage:.1f}%)")
            
            with col_analysis2:
                st.subheader(":performing_arts: تحليل المشاعر")
                sentiments = [n['sentiment'] for n in news]
                sentiment_counts = Counter(sentiments)
                
                for sent, count in sentiment_counts.items():
                    percentage = (count / len(news)) * 100
                    st.write(f"• **{sent}**: {count} ({percentage:.1f}%)")
            
            st.subheader(":abc: أكثر الكلمات تكراراً")
            all_text = " ".join([n['title'] + " " + n['summary'] for n in news])
            # تنظيف النص
            words = re.findall(r'[^\W_]+', all_text, re.UNICODE)  # كلمات عربية فقط
            word_freq = Counter(words).most_common(15)
            
            if word_freq:
                cols = st.columns(3)
                for i, (word, freq) in enumerate(word_freq):
                    with cols[i % 3]:
                        st.write(f"**{word}**: {freq} مرة")
    
    else:
        st.warning(":x: لم يتم العثور على أخبار بالشروط المحددة")
        st.info(":bulb: جرب توسيع نطاق التاريخ أو تغيير الكلمات المفتاحية")
        st.markdown(f":link: **[زيارة {selected_source} مباشرة]({source_info['url']})**")

# معلومات في الشريط الجانبي
st.sidebar.markdown("---")
st.sidebar.info("""
:rocket: **تقنيات متقدمة:**
- جلب RSS تلقائي
- تحليل مواقع الويب باستخدام الذكاء الاصطناعي
- تصنيف ذكي للأخبار
- تحليل المشاعر للغة العربية
- إزالة المحتوى المكرر تلقائياً
""")

st.sidebar.success(":white_check_mark: نظام ذكي متطور لجمع الأخبار!")

# معلومات تقنية
with st.expander(":information_source: معلومات تقنية"):
    st.markdown("""
    ### :hammer_and_wrench: التقنيات المستخدمة:
    - **RSS Parsing**: لجلب الأخبار من المصادر التقليدية
    - **HTML Analysis**: لتحليل مواقع الويب مباشرة باستخدام BeautifulSoup
    - **Smart Categorization**: تصنيف تلقائي للأخبار مع أوزان للكلمات
    - **Sentiment Analysis**: تحليل المشاعر باستخدام نموذج BERT للغة العربية
    - **Regex Extraction**: استخراج العناوين والروابط بالتعبيرات النمطية
    - **Duplicate Removal**: إزالة الأخبار المكررة تلقائياً
    
    ### :chart_with_upwards_trend: المزايا الجديدة:
    - **Multi-Method Fetching**: جلب الأخبار بعدة طرق
    - **Fallback System**: نظام احتياطي عند فشل RSS
    - **Advanced Filtering**: فلترة متقدمة بالكلمات والتصنيفات
    - **Real-time Processing**: معالجة فورية للبيانات
    - **Export Options**: تصدير بصيغ متعددة (Word, Excel, JSON)
    
    ### :dart: كيف يعمل النظام:
    1. **محاولة RSS أولاً**: البحث عن feeds متاحة
    2. **تحليل HTML**: استخراج المحتوى من الصفحة مباشرة باستخدام الذكاء الاصطناعي
    3. **معالجة ذكية**: تنظيف وتصنيف البيانات
    4. **إزالة التكرار**: ضمان عدم تكرار الأخبار
    5. **تحليل متقدم**: استخراج الإحصائيات والمشاعر
    """)
