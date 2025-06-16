import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from textblob import TextBlob
from collections import Counter
from docx import Document
import json
import re
import time
from urllib.parse import urljoin, urlparse
import concurrent.futures
from threading import Lock
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.set_page_config(page_title=":newspaper: أداة الأخبار العربية الذكية", layout="wide")
st.title(":rolled_up_newspaper: أداة سحب وتحليل الأخبار المتطورة (Web Scraping)")

# التصنيفات المحسّنة
category_keywords = {
    "سياسة": ["رئيس", "وزير", "انتخابات", "برلمان", "سياسة", "حكومة", "نائب", "مجلس", "دولة", "حزب", "رئيس الوزراء", "رئيس الجمهورية"],
    "رياضة": ["كرة", "لاعب", "مباراة", "دوري", "هدف", "فريق", "بطولة", "رياضة", "ملعب", "تدريب", "كأس", "منتخب"],
    "اقتصاد": ["سوق", "اقتصاد", "استثمار", "بنك", "مال", "تجارة", "صناعة", "نفط", "غاز", "بورصة", "عملة", "أسعار"],
    "تكنولوجيا": ["تقنية", "تطبيق", "هاتف", "ذكاء", "برمجة", "إنترنت", "رقمي", "حاسوب", "شبكة", "آيفون", "أندرويد", "تكنولوجيا"],
    "صحة": ["طب", "مرض", "علاج", "مستشفى", "دواء", "صحة", "طبيب", "فيروس", "لقاح", "وباء", "كورونا", "طبي"],
    "تعليم": ["تعليم", "جامعة", "مدرسة", "طالب", "دراسة", "كلية", "معهد", "تربية", "أكاديمي", "بحث", "امتحان", "شهادة"],
    "أمن": ["أمن", "شرطة", "عسكري", "إرهاب", "جريمة", "اعتقال", "قتل", "حادث", "انفجار", "عملية أمنية", "داعش", "حرب"]
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

def generate_news_id(title, url):
    """توليد معرف فريد للخبر"""
    unique_string = f"{title}{url}"
    return hashlib.md5(unique_string.encode('utf-8')).hexdigest()[:10]

def get_page_content(url, timeout=15):
    """جلب محتوى الصفحة مع headers متقدمة"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.warning(f"خطأ في الوصول لـ {url}: {str(e)}")
        return None

def extract_links_from_page(soup, base_url, site_config):
    """استخراج روابط الأخبار من الصفحة"""
    links = []
    
    # تجربة عدة selectors حسب نوع الموقع
    link_selectors = site_config.get("link_selectors", [
        "article a[href]",
        ".news-item a[href]",
        ".post a[href]",
        ".entry a[href]",
        "h1 a[href]",
        "h2 a[href]",
        "h3 a[href]",
        ".title a[href]",
        ".headline a[href]",
        "a[href*='news']",
        "a[href*='article']",
        "a[href*='post']"
    ])
    
    for selector in link_selectors:
        try:
            elements = soup.select(selector)
            for element in elements[:20]:  # أول 20 رابط لكل selector
                href = element.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    title = element.get_text(strip=True) or element.get('title', '')
                    
                    # فلترة الروابط غير المرغوبة
                    if not any(skip in full_url.lower() for skip in ['#', 'javascript:', 'mailto:', 'tel:']):
                        if len(title) > 10 and len(title) < 200:
                            links.append({
                                'url': full_url,
                                'title': title
                            })
            
            if links:  # إذا وجدنا روابط، نتوقف
                break
                
        except Exception as e:
            continue
    
    # إزالة الروابط المكررة
    seen_urls = set()
    unique_links = []
    for link in links:
        if link['url'] not in seen_urls:
            seen_urls.add(link['url'])
            unique_links.append(link)
    
    return unique_links[:15]  # أول 15 رابط فريد

def extract_article_content(url, site_config):
    """استخراج محتوى المقال من الرابط"""
    content = get_page_content(url)
    if not content:
        return None
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # استخراج العنوان
        title_selectors = site_config.get("title_selectors", [
            "h1.title",
            "h1.headline",
            ".entry-title",
            ".post-title",
            "h1",
            ".article-title",
            "title"
        ])
        
        title = ""
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if len(title) > 10:
                    break
        
        # استخراج المحتوى
        content_selectors = site_config.get("content_selectors", [
            ".entry-content",
            ".post-content",
            ".article-content",
            ".content",
            ".post-body",
            ".article-body",
            ".news-content",
            "article p",
            ".description"
        ])
        
        content_text = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                texts = []
                for elem in elements:
                    # إزالة العناصر غير المرغوبة
                    for unwanted in elem.select('script, style, nav, footer, .ad, .advertisement'):
                        unwanted.decompose()
                    text = elem.get_text(strip=True)
                    if text and len(text) > 20:
                        texts.append(text)
                
                content_text = " ".join(texts)
                if len(content_text) > 50:
                    break
        
        # استخراج الصورة
        image_selectors = site_config.get("image_selectors", [
            ".featured-image img",
            ".post-thumbnail img",
            ".article-image img",
            "article img",
            ".content img"
        ])
        
        image_url = ""
        for selector in image_selectors:
            img = soup.select_one(selector)
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    image_url = urljoin(url, src)
                    break
        
        # استخراج التاريخ
        date_selectors = site_config.get("date_selectors", [
            ".published-date",
            ".post-date",
            ".article-date",
            ".date",
            "time[datetime]",
            ".entry-date"
        ])
        
        published_date = datetime.now()
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True) or date_elem.get('datetime', '')
                # محاولة تحليل التاريخ
                try:
                    # تجربة عدة تنسيقات للتاريخ
                    for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                        try:
                            published_date = datetime.strptime(date_text[:19], date_format)
                            break
                        except:
                            continue
                    break
                except:
                    continue
        
        return {
            'title': title or "بدون عنوان",
            'content': content_text or title,
            'image': image_url,
            'published': published_date,
            'url': url
        }
        
    except Exception as e:
        st.warning(f"خطأ في استخراج المحتوى من {url}: {str(e)}")
        return None

def scrape_website_news(source_name, source_config, keywords, date_from, date_to, chosen_category, max_articles=15):
    """سحب الأخبار من موقع واحد"""
    st.info(f":arrows_counterclockwise: جاري تحليل موقع {source_name}...")
    
    base_url = source_config["url"]
    content = get_page_content(base_url)
    
    if not content:
        return []
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # استخراج روابط الأخبار
        links = extract_links_from_page(soup, base_url, source_config)
        
        if not links:
            st.warning(f"لم يتم العثور على روابط في {source_name}")
            return []
        
        st.info(f"تم العثور على {len(links)} رابط، جاري تحليل المحتوى...")
        
        news_list = []
        processed_count = 0
        
        # استخدام threading لتسريع العملية
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_link = {
                executor.submit(extract_article_content, link['url'], source_config): link 
                for link in links[:max_articles]
            }
            
            for future in concurrent.futures.as_completed(future_to_link):
                link = future_to_link[future]
                try:
                    article = future.result(timeout=10)
                    if article:
                        processed_count += 1
                        
                        # تطبيق الفلاتر
                        full_text = f"{article['title']} {article['content']}"
                        
                        # فلترة الكلمات المفتاحية
                        if keywords:
                            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
                            if not any(keyword.lower() in full_text.lower() for keyword in keyword_list):
                                continue
                        
                        # فلترة التاريخ
                        if not (date_from <= article['published'].date() <= date_to):
                            continue
                        
                        # التصنيف والتحليل
                        category = detect_category(full_text)
                        if chosen_category != "الكل" and category != chosen_category:
                            continue
                        
                        news_item = {
                            "id": generate_news_id(article['title'], article['url']),
                            "source": source_name,
                            "title": article['title'],
                            "summary": summarize(article['content'], 40),
                            "content": article['content'][:500] + "..." if len(article['content']) > 500 else article['content'],
                            "link": article['url'],
                            "published": article['published'],
                            "image": article['image'],
                            "sentiment": analyze_sentiment(full_text),
                            "category": category,
                            "extraction_method": "Advanced Web Scraping"
                        }
                        
                        news_list.append(news_item)
                        
                        # تحديث التقدم
                        if processed_count % 3 == 0:
                            st.info(f"تم معالجة {processed_count} مقال...")
                            
                except Exception as e:
                    continue
        
        # إزالة المكرر
        unique_news = []
        seen_ids = set()
        for news in news_list:
            if news['id'] not in seen_ids:
                seen_ids.add(news['id'])
                unique_news.append(news)
        
        st.success(f":white_check_mark: تم استخراج {len(unique_news)} خبر من {source_name}")
        return unique_news
        
    except Exception as e:
        st.error(f"خطأ في معالجة {source_name}: {str(e)}")
        return []

def scrape_multiple_sources(sources, keywords, date_from, date_to, chosen_category, max_per_source=10):
    """سحب الأخبار من مصادر متعددة بشكل متوازي"""
    all_news = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, (source_name, config) in enumerate(sources.items()):
        status_text.text(f"معالجة {source_name}... ({i+1}/{len(sources)})")
        progress_bar.progress((i + 1) / len(sources))
        
        try:
            news = scrape_website_news(
                source_name, 
                config, 
                keywords, 
                date_from, 
                date_to, 
                chosen_category, 
                max_per_source
            )
            all_news.extend(news)
            time.sleep(1)  # تأخير بسيط لتجنب حظر IP
        except Exception as e:
            st.warning(f"تخطي {source_name} بسبب خطأ: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    return all_news

def create_analytics_charts(news_list):
    """إنشاء الرسوم البيانية للتحليلات"""
    charts = {}
    
    # توزيع التصنيفات
    categories = [news['category'] for news in news_list]
    category_counts = Counter(categories)
    
    fig_category = px.pie(
        values=list(category_counts.values()),
        names=list(category_counts.keys()),
        title="توزيع الأخبار حسب التصنيف",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_category.update_traces(textposition='inside', textinfo='percent+label')
    charts['categories'] = fig_category
    
    # توزيع المشاعر
    sentiments = [news['sentiment'].split()[1] for news in news_list]  # استخراج النص بعد الإيموجي
    sentiment_counts = Counter(sentiments)
    
    fig_sentiment = px.bar(
        x=list(sentiment_counts.keys()),
        y=list(sentiment_counts.values()),
        title="توزيع المشاعر في الأخبار",
        color=list(sentiment_counts.keys()),
        color_discrete_map={'إيجابي': 'green', 'سلبي': 'red', 'محايد': 'gray'}
    )
    charts['sentiment'] = fig_sentiment
    
    # توزيع المصادر
    sources = [news['source'] for news in news_list]
    source_counts = Counter(sources)
    
    fig_sources = px.bar(
        x=list(source_counts.values()),
        y=list(source_counts.keys()),
        orientation='h',
        title="عدد الأخبار لكل مصدر",
        color=list(source_counts.values()),
        color_continuous_scale='Blues'
    )
    charts['sources'] = fig_sources
    
    # توزيع زمني
    dates = [news['published'].date() for news in news_list]
    date_counts = Counter(dates)
    
    fig_timeline = px.line(
        x=list(date_counts.keys()),
        y=list(date_counts.values()),
        title="التوزيع الزمني للأخبار",
        markers=True
    )
    fig_timeline.update_xaxes(title_text="التاريخ")
    fig_timeline.update_yaxes(title_text="عدد الأخبار")
    charts['timeline'] = fig_timeline
    
    return charts

def export_to_word(news_list):
    """تصدير الأخبار إلى ملف Word"""
    doc = Document()
    doc.add_heading('تقرير الأخبار المجمعة - Web Scraping', 0)
    doc.add_paragraph(f'تاريخ التقرير: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    doc.add_paragraph(f'عدد الأخبار: {len(news_list)}')
    doc.add_paragraph('طريقة الاستخراج: Web Scraping المتطور')
    doc.add_paragraph('---')
    
    for i, news in enumerate(news_list, 1):
        doc.add_heading(f'{i}. {news["title"]}', level=2)
        doc.add_paragraph(f"المصدر: {news['source']}")
        doc.add_paragraph(f"التصنيف: {news['category']}")
        doc.add_paragraph(f"التاريخ: {news['published'].strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"التحليل العاطفي: {news['sentiment']}")
        doc.add_paragraph(f"الملخص: {news['summary']}")
        doc.add_paragraph(f"المحتوى: {news.get('content', 'غير متاح')}")
        doc.add_paragraph(f"الرابط: {news['link']}")
        doc.add_paragraph('---')
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def export_to_excel(news_list):
    """تصدير الأخبار إلى ملف Excel"""
    df = pd.DataFrame(news_list)
    columns_order = ['source', 'title', 'category', 'sentiment', 'published', 'summary', 'content', 'link', 'extraction_method']
    df = df.reindex(columns=[col for col in columns_order if col in df.columns])
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='الأخبار')
    buffer.seek(0)
    return buffer

# مصادر الأخبار المحسّنة مع إعدادات Scraping
iraqi_news_sources = {
    "وزارة الداخلية العراقية": {
        "url": "https://moi.gov.iq/",
        "title_selectors": ["h1", ".title", ".post-title"],
        "content_selectors": [".content", ".post-content", "article p"],
        "link_selectors": ["article a[href]", ".post a[href]", "h3 a[href]"],
        "date_selectors": [".date", ".published", "time"],
        "image_selectors": [".featured-image img", "article img"]
    },
    "الشرق الأوسط": {
        "url": "https://asharq.com/",
        "title_selectors": ["h1.title", ".article-title", "h1"],
        "content_selectors": [".article-content", ".content", "article p"],
        "link_selectors": ["article a[href]", ".news-item a[href]"],
        "date_selectors": [".article-date", ".date"],
        "image_selectors": [".article-image img", "article img"]
    },
    "RT Arabic": {
        "url": "https://arabic.rt.com/",
        "title_selectors": [".article__heading", "h1", ".title"],
        "content_selectors": [".article__text", ".content", "article p"],
        "link_selectors": [".link_color a[href]", "article a[href]"],
        "date_selectors": [".date", ".article__date"],
        "image_selectors": [".media img", "article img"]
    },
    "الجزيرة نت": {
        "url": "https://www.aljazeera.net/",
        "title_selectors": ["h1", ".post-title", ".article-title"],
        "content_selectors": [".wysiwyg", ".article-content", "article p"],
        "link_selectors": ["article a[href]", ".post a[href]"],
        "date_selectors": [".date-simple", ".date"],
        "image_selectors": [".article-featured-image img", "article img"]
    },
    "بغداد اليوم": {
        "url": "https://baghdadtoday.news/",
        "title_selectors": ["h1", ".entry-title", ".post-title"],
        "content_selectors": [".entry-content", ".post-content"],
        "link_selectors": ["article a[href]", ".post-title a[href]"],
        "date_selectors": [".entry-date", ".date"],
        "image_selectors": [".post-thumbnail img", "article img"]
    },
    "وكالة الأنباء العراقية": {
        "url": "https://www.ina.iq/",
        "title_selectors": ["h1", ".title", ".news-title"],
        "content_selectors": [".content", ".news-content", "article p"],
        "link_selectors": [".news-item a[href]", "article a[href]"],
        "date_selectors": [".date", ".news-date"],
        "image_selectors": [".news-image img", "article img"]
    }
}

# واجهة المستخدم الرئيسية
st.sidebar.header(":gear: إعدادات البحث المتقدم")

# اختيار المصادر
selected_sources = st.sidebar.multiselect(
    ":globe_with_meridians: اختر مصادر الأخبار:",
    list(iraqi_news_sources.keys()),
    default=list(iraqi_news_sources.keys())[:3],
    help="يمكنك اختيار مصدر واحد أو أكثر"
)

# إعدادات البحث
keywords_input = st.sidebar.text_input(
    ":mag: كلمات مفتاحية (مفصولة بفواصل):", 
    "",
    help="اتركها فارغة لجلب جميع الأخبار"
)

category_filter = st.sidebar.selectbox(
    ":file_folder: اختر التصنيف:", 
    ["الكل"] + list(category_keywords.keys()),
    help="فلترة الأخبار حسب التصنيف"
)

# إعدادات التاريخ
col_date1, col_date2 = st.sidebar.columns(2)
with col_date1:
    date_from = st.date_input(":date: من تاريخ:", datetime.today() - timedelta(days=3))
with col_date2:
    date_to = st.date_input(":date: إلى تاريخ:", datetime.today())

# خيارات متقدمة
with st.sidebar.expander(":gear: خيارات متقدمة"):
    max_per_source = st.slider("عدد الأخبار لكل مصدر:", 5, 20, 10)
    include_content = st.checkbox("استخراج المحتوى الكامل", True)
    show_analytics = st.checkbox("عرض التحليلات المتقدمة", True)

# زر بدء العملية
run = st.sidebar.button(":rocket: بدء عملية السحب", type="primary", help="ابدأ عملية سحب الأخبار من المواقع")

# عرض النتائج
if run:
    if not selected_sources:
        st.error(":x: يرجى اختيار مصدر واحد على الأقل")
    else:
        with st.spinner(":robot_face: جاري تشغيل نظام Web Scraping المتطور..."):
            start_time = time.time()
            
            # إعداد المصادر المختارة
            sources_to_scrape = {name: iraqi_news_sources[name] for name in selected_sources}
            
            # سحب الأخبار
            news = scrape_multiple_sources(
                sources_to_scrape,
                keywords_input,
                date_from,
                date_to,
                category_filter,
                max_per_source
            )
            
            end_time = time.time()
            processing_time = round(end_time - start_time, 2)
        
        if news:
            st.success(f":tada: تم سحب {len(news)} خبر من {len(selected_sources)} مصدر في {processing_time} ثانية")
            
            # إحصائيات سريعة
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(":newspaper: إجمالي الأخبار", len(news))
            with col2:
                categories = [n['category'] for n in news]
                most_common_category = Counter(categories).most_common(1)[0][0] if categories else "غير محدد"
                st.metric(":file_folder: أكثر تصنيف", most_common_category)
            with col3:
                positive_news = len([n for n in news if "إيجابي" in n['sentiment']])
                st.metric(":smiley: أخبار إيجابية", positive_news)
            with col4:
                st.metric(":stopwatch: وقت المعالجة", f"{processing_time}s")
            
            # التحليلات المتقدمة
            if show_analytics:
                with st.expander(":bar_chart: تحليلات متقدمة", expanded=True):
                    charts = create_analytics_charts(news)
                    
                    col_analysis1, col_analysis2 = st.columns(2)
                    
                    with col_analysis1:
                        st.plotly_chart(charts['categories'], use_container_width=True)
                        st.plotly_chart(charts['sentiment'], use_container_width=True)
                    
                    with col_analysis2:
                        st.plotly_chart(charts['sources'], use_container_width=True)
                        st.plotly_chart(charts['timeline'], use_container_width=True)
                    
                                       # إحصائيات إضافية

                    
                    # سحابة الكلمات
                    st.subheader(":cloud: سحابة الكلمات المفتاحية")
                    wordcloud = WordCloud(
                        width=800, 
                        height=400, 
                        background_color='white',
                        font_path=None,  # يمكن تحديد مسار خط عربي إذا لزم الأمر
                        collocations=False
                    ).generate(all_text)
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
            
            # عرض الأخبار
            st.subheader(f":newspaper: نتائج البحث ({len(news)} خبر)")
            
            for i, item in enumerate(news, 1):
                with st.expander(f"{i}. {item['title']}", expanded=False):
                    col_news1, col_news2 = st.columns([1, 3])
                    
                    with col_news1:
                        if item['image']:
                            st.image(item['image'], width=200)
                        else:
                            st.warning("لا توجد صورة")
                    
                    with col_news2:
                        st.markdown(f"""
                        **المصدر:** {item['source']}  
                        **التصنيف:** {item['category']}  
                        **التاريخ:** {item['published'].strftime('%Y-%m-%d %H:%M')}  
                        **المشاعر:** {item['sentiment']}  
                        **الملخص:** {item['summary']}
                        """)
                        
                        if include_content:
                            st.markdown("**المحتوى:**")
                            st.write(item['content'])
                        
                        st.markdown(f"[قراءة المزيد على الموقع الأصلي]({item['link']})")
            
            # خيارات التصدير
            st.subheader(":floppy_disk: خيارات التصدير")
            export_col1, export_col2, export_col3 = st.columns(3)
            
            with export_col1:
                if st.button(":page_facing_up: تصدير إلى Word"):
                    word_file = export_to_word(news)
                    st.download_button(
                        label="تحميل ملف Word",
                        data=word_file,
                        file_name=f"arabic_news_report_{datetime.now().strftime('%Y%m%d')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            
            with export_col2:
                if st.button(":bar_chart: تصدير إلى Excel"):
                    excel_file = export_to_excel(news)
                    st.download_button(
                        label="تحميل ملف Excel",
                        data=excel_file,
                        file_name=f"arabic_news_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with export_col3:
                if st.button(":file_folder: تصدير إلى JSON"):
                    json_data = json.dumps(news, ensure_ascii=False, default=str)
                    st.download_button(
                        label="تحميل ملف JSON",
                        data=json_data,
                        file_name=f"arabic_news_report_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
        else:
            st.warning(":warning: لم يتم العثور على أخبار تطابق معايير البحث")
else:
    st.info(":information_source: يرجى ضبط إعدادات البحث ثم الضغط على زر 'بدء عملية السحب'")

# تذييل الصفحة
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>أداة سحب وتحليل الأخبار العربية المتطورة | تم التطوير باستخدام Python و Streamlit</p>
    <p>الإصدار 2.0 | آخر تحديث: يونيو 2024</p>
</div>
""", unsafe_allow_html=True)
