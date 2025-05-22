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

# التصنيفات المحسّنة والموسعة (للتصنيف التلقائي فقط)
category_keywords = {
    "سياسة": ["رئيس", "وزير", "انتخابات", "برلمان", "سياسة", "حكومة", "نائب", "مجلس", "دولة", "حزب", "سفير", "وزارة", "قانون", "دستور", "محكمة", "قاضي", "عدالة", "أمن", "شرطة", "جيش", "عسكري", "دفاع", "قوات", "استراتيجية", "دبلوماسية", "معاهدة", "اتفاقية", "مؤتمر", "قمة", "حوار", "مفاوضات", "تحالف", "معارضة", "ثورة", "انقلاب", "ديمقراطية", "حقوق", "حريات", "مواطن", "شعب", "أمة", "وطن", "قومي", "عربي", "إسلامي", "دولي", "إقليمي", "محلي", "بلدية", "محافظة", "ولاية", "مدينة", "عاصمة"],
    
    "رياضة": ["كرة", "لاعب", "مباراة", "دوري", "هدف", "فريق", "بطولة", "رياضة", "ملعب", "تدريب", "مدرب", "حكم", "نادي", "بطل", "كأس", "جائزة", "ميدالية", "ذهبية", "فضية", "برونزية", "أولمبياد", "كرة قدم", "كرة سلة", "كرة طائرة", "تنس", "سباحة", "جري", "مصارعة", "ملاكمة", "جمباز", "ألعاب قوى", "سباق", "ماراثون", "يوجا", "لياقة", "صحة بدنية", "تغذية رياضية", "مكملات", "بطولة العالم", "كأس العالم", "دوري أبطال", "الدوري الممتاز", "الدوري المحلي", "منتخب", "مصر", "السعودية", "الإمارات", "قطر", "العراق", "الأردن", "لبنان", "المغرب", "تونس", "الجزائر"],
    
    "اقتصاد": ["سوق", "اقتصاد", "استثمار", "بنك", "مال", "تجارة", "صناعة", "نفط", "غاز", "بورصة", "أسهم", "عملة", "دولار", "يورو", "ريال", "درهم", "دينار", "جنيه", "ليرة", "تضخم", "ركود", "نمو", "إنتاج", "تصدير", "استيراد", "ميزانية", "عجز", "فائض", "ديون", "قروض", "فوائد", "مصارف", "بنوك", "تمويل", "ائتمان", "ذهب", "فضة", "معادن", "طاقة", "كهرباء", "مياه", "زراعة", "صيد", "سياحة", "فنادق", "طيران", "شحن", "مواصلات", "اتصالات", "تقنية مالية", "عملة رقمية", "بيتكوين", "بلوك تشين", "ذكاء اصطناعي", "روبوت", "أتمتة", "صناعة 4.0", "تحول رقمي", "ريادة أعمال", "شركات ناشئة", "احتكار", "منافسة", "أسعار", "تكلفة", "ربح", "خسارة", "مبيعات", "إيرادات", "مصروفات"],
    
    "تكنولوجيا": ["تقنية", "تطبيق", "هاتف", "ذكاء", "برمجة", "إنترنت", "رقمي", "حاسوب", "شبكة", "آيفون", "أندرويد", "سامسونغ", "هواوي", "أبل", "جوجل", "مايكروسوفت", "فيسبوك", "تويتر", "إنستغرام", "يوتيوب", "تيك توك", "واتساب", "تلغرام", "سناب شات", "لينكد إن", "برنامج", "تطبيق", "موقع", "منصة", "خوارزمية", "بيانات", "تحليل", "إحصاء", "قاعدة بيانات", "خادم", "سحابة", "تخزين", "أمان", "حماية", "فيروس", "هاكر", "اختراق", "تشفير", "كلمة مرور", "هوية رقمية", "بصمة", "وجه", "صوت", "واقع افتراضي", "واقع معزز", "طباعة ثلاثية الأبعاد", "روبوت", "ذكاء اصطناعي", "تعلم آلة", "شبكة عصبية", "معالجة لغة", "رؤية حاسوبية", "إنترنت الأشياء", "البلوك تشين", "عملة رقمية", "NFT", "ميتافيرس", "ألعاب", "بث", "محتوى رقمي", "وسائط متعددة", "فيديو", "صوت", "صورة", "جرافيك", "تصميم", "مونتاج", "تحرير"],
    
    "صحة": ["طب", "مرض", "علاج", "مستشفى", "دواء", "صحة", "طبيب", "فيروس", "لقاح", "وباء", "ممرض", "طبيب أسنان", "صيدلي", "مختبر", "تحليل", "فحص", "أشعة", "جراحة", "عملية", "تخدير", "مريض", "إسعاف", "طوارئ", "عناية مركزة", "قلب", "رئة", "كبد", "كلى", "دماغ", "عظام", "عضلات", "أعصاب", "جلد", "عيون", "أذن", "أنف", "حنجرة", "أسنان", "فم", "معدة", "أمعاء", "بنكرياس", "غدد", "هرمونات", "دم", "ضغط", "سكري", "كوليسترول", "سرطان", "ورم", "التهاب", "عدوى", "بكتيريا", "طفيليات", "حساسية", "مناعة", "مضادات حيوية", "مسكن", "مضاد التهاب", "فيتامين", "معدن", "تغذية", "حمية", "رجيم", "سمنة", "نحافة", "لياقة", "رياضة", "يوجا", "تأمل", "استرخاء", "صحة نفسية", "اكتئاب", "قلق", "توتر", "نوم", "أرق", "حمل", "ولادة", "أطفال", "مراهقة", "شيخوخة", "وقاية", "تطعيم", "نظافة", "تعقيم", "كمامة"],
    
    "تعليم": ["تعليم", "جامعة", "مدرسة", "طالب", "دراسة", "كلية", "معهد", "تربية", "أكاديمي", "بحث", "أستاذ", "معلم", "مدرس", "محاضر", "باحث", "دكتور", "ماجستير", "بكالوريوس", "دبلوم", "شهادة", "درجة علمية", "تخصص", "قسم", "فرع", "مناهج", "كتاب", "مذكرة", "واجب", "امتحان", "اختبار", "تقييم", "درجات", "نتائج", "نجاح", "رسوب", "تفوق", "مكافأة", "منحة", "بعثة", "دورة", "ورشة", "مؤتمر", "ندوة", "محاضرة", "عرض", "مشروع", "رسالة", "أطروحة", "تجربة", "مختبر", "مكتبة", "كتب", "مراجع", "مصادر", "إنترنت", "تعلم إلكتروني", "تعليم عن بعد", "منصة تعليمية", "فيديو تعليمي", "محتوى رقمي", "لغة عربية", "رياضيات", "علوم", "فيزياء", "كيمياء", "أحياء", "جغرافيا", "تاريخ", "دين", "فلسفة", "علم نفس", "اجتماع", "اقتصاد", "سياسة", "قانون", "طب", "هندسة", "حاسوب", "برمجة", "فنون", "أدب", "شعر", "قصة", "رواية", "مسرح", "سينما", "موسيقى", "رسم", "نحت", "خط عربي", "خط", "تصميم", "إعلام", "صحافة", "إذاعة", "تلفزيون", "إعلان", "تسويق", "ترجمة", "لغات أجنبية", "إنجليزي", "فرنسي", "ألماني", "إسباني", "صيني", "ياباني", "روسي", "تركي", "فارسي", "عبري", "لاتيني", "يوناني"]
}

# دالة البحث المفتوح في النصوص - محدثة لتكون أكثر مرونة
def flexible_keyword_search(text, keywords):
    """
    بحث مرن وذكي في النصوص - يبحث عن أي كلمة مفتاحية في أي مكان
    """
    if not text or not keywords:
        return True  # إذا لم تكن هناك كلمات مفتاحية، اعرض كل الأخبار
    
    text_lower = text.lower()
    
    # إزالة المسافات الزائدة وتحويل النص للبحث
    text_cleaned = re.sub(r'\s+', ' ', text_lower).strip()
    
    # البحث المباشر في النص
    for keyword in keywords:
        keyword = keyword.strip().lower()
        if not keyword:
            continue
            
        # البحث المباشر
        if keyword in text_cleaned:
            return True
        
        # البحث بالكلمات المنفصلة (إذا كانت الكلمة المفتاحية تحتوي على مسافات)
        keyword_words = keyword.split()
        if len(keyword_words) > 1:
            # البحث عن كل كلمة منفصلة
            all_words_found = all(word in text_cleaned for word in keyword_words)
            if all_words_found:
                return True
        
        # البحث بالجذور (تجريبي - للكلمات العربية)
        # مثال: "كتب" يجد "كتاب", "كاتب", "مكتوب"
        if len(keyword) >= 3:
            root = keyword[:3]  # أخذ أول 3 أحرف كجذر تقريبي
            if root in text_cleaned:
                return True
    
    return False

# دالة تحسين البحث بالمرادفات والكلمات ذات الصلة
def enhanced_keyword_search(text, keywords):
    """
    بحث محسن يتضمن المرادفات والكلمات ذات الصلة
    """
    if not text or not keywords:
        return True
    
    # قاموس المرادفات البسيط (يمكن توسيعه)
    synonyms_dict = {
        "حرب": ["قتال", "معركة", "صراع", "نزاع", "حرب"],
        "اقتصاد": ["مال", "تجارة", "استثمار", "بورصة", "سوق"],
        "سياسة": ["حكومة", "دولة", "رئيس", "وزير", "انتخابات"],
        "رياضة": ["كرة", "لاعب", "مباراة", "فريق", "بطولة"],
        "تعليم": ["مدرسة", "جامعة", "طالب", "معلم", "دراسة"],
        "صحة": ["طب", "مرض", "علاج", "مستشفى", "دواء"],
        "تكنولوجيا": ["تقنية", "كمبيوتر", "إنترنت", "برمجة", "ذكاء اصطناعي"]
    }
    
    text_lower = text.lower()
    
    for keyword in keywords:
        keyword = keyword.strip().lower()
        if not keyword:
            continue
        
        # البحث المباشر
        if keyword in text_lower:
            return True
        
        # البحث في المرادفات
        for main_word, synonyms in synonyms_dict.items():
            if keyword == main_word or keyword in synonyms:
                for synonym in synonyms:
                    if synonym in text_lower:
                        return True
        
        # البحث الجزئي للكلمات الطويلة
        if len(keyword) > 4:
            # تقسيم الكلمة المفتاحية إلى أجزاء
            parts = [keyword[i:i+4] for i in range(len(keyword)-3)]
            for part in parts:
                if part in text_lower:
                    return True
    
    return False

# الدوال المحسّنة
def create_smart_summary(title, content, max_sentences=3):
    """إنشاء ملخص ذكي أطول"""
    if not content or content == title:
        # إذا لم يكن هناك محتوى، نوسع العنوان
        words = title.split()
        if len(words) > 10:
            return " ".join(words[:15]) + "..."
        else:
            return title + " - تفاصيل إضافية متاحة في المقال الكامل."
    
    # تنظيف النص
    content = re.sub(r'<[^>]+>', '', content)  # إزالة HTML tags
    content = re.sub(r'\s+', ' ', content).strip()  # تنظيف المسافات
    
    # تقسيم إلى جمل
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    if not sentences:
        return title
    
    # أخذ أول عدة جمل
    selected_sentences = sentences[:max_sentences]
    summary = ". ".join(selected_sentences)
    
    # التأكد من طول مناسب
    if len(summary.split()) < 20:
        # إضافة المزيد من الجمل إذا كان قصير
        extra_sentences = sentences[max_sentences:max_sentences+2]
        if extra_sentences:
            summary += ". " + ". ".join(extra_sentences)
    
    # قطع إذا كان طويل جداً
    words = summary.split()
    if len(words) > 80:
        summary = " ".join(words[:80]) + "..."
    
    return summary if summary else title

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
    
    # البحث عن النصوص الطويلة (للملخصات)
    content_patterns = [
        r'<p[^>]*>(.*?)</p>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*summary[^"]*"[^>]*>(.*?)</div>'
    ]
    
    titles = []
    links = []
    contents = []
    
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
    
    # استخراج النصوص للملخصات
    for pattern in content_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            content = re.sub(r'<[^>]+>', '', str(match)).strip()
            if content and len(content) > 50:
                contents.append(content)
    
    # دمج العناوين والروابط والمحتويات
    for i, title in enumerate(titles[:10]):  # أول 10 أخبار
        link = links[i] if i < len(links) else base_url
        content = contents[i] if i < len(contents) else title
        
        # إنشاء ملخص محسن
        smart_summary = create_smart_summary(title, content)
        
        news_list.append({
            "source": source_name,
            "title": title,
            "summary": smart_summary,
            "link": link,
            "published": datetime.now(),
            "image": "",
            "sentiment": analyze_sentiment(smart_summary),
            "category": detect_category(title + " " + smart_summary),
            "extraction_method": "HTML Parsing"
        })
    
    return news_list

def fetch_rss_news(source_name, url, keywords, date_from, date_to, chosen_category):
    """جلب الأخبار من RSS مع بحث مفتوح للكلمات المفتاحية"""
    try:
        feed = feedparser.parse(url)
        news_list = []
        
        if not hasattr(feed, 'entries') or len(feed.entries) == 0:
            return []
        
        for entry in feed.entries:
            try:
                title = entry.get('title', 'بدون عنوان')
                summary = entry.get('summary', entry.get('description', ''))
                content = entry.get('content', [{}])
                if content and isinstance(content, list) and len(content) > 0:
                    full_content = content[0].get('value', summary)
                else:
                    full_content = summary
                
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

                # إنشاء ملخص ذكي محسن
                enhanced_summary = create_smart_summary(title, full_content)
                
                # البحث المفتوح في الكلمات المفتاحية
                full_text = title + " " + enhanced_summary
                if keywords and not enhanced_keyword_search(full_text, keywords):
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
                    "summary": enhanced_summary,
                    "link": link,
                    "published": published_dt,
                    "image": image,
                    "sentiment": analyze_sentiment(enhanced_summary),
                    "category": auto_category,
                    "extraction_method": "RSS"
                })
                
            except Exception as e:
                continue
                
        return news_list
        
    except Exception as e:
        return []

def fetch_website_news(source_name, url, keywords, date_from, date_to, chosen_category):
    """جلب الأخبار من الموقع مباشرة مع بحث مفتوح"""
    try:
        st.info(f"🔄 جاري تحليل موقع {source_name}...")
        
        # جلب محتوى الصفحة
        html_content = safe_request(url)
        if not html_content:
            return []
        
        # استخراج الأخبار من HTML
        base_url = url.rstrip('/')
        news_list = extract_news_from_html(html_content, source_name, base_url)
        
        # فلترة النتائج بالبحث المفتوح
        filtered_news = []
        for news in news_list:
            # البحث المفتوح في الكلمات المفتاحية
            full_text = news['title'] + " " + news['summary']
            if keywords and not enhanced_keyword_search(full_text, keywords):
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

# إعدادات البحث المحسّنة
st.sidebar.markdown("### 🔍 البحث المفتوح بالكلمات المفتاحية")
keywords_input = st.sidebar.text_area(
    "كلمات مفتاحية للبحث (أي كلمة أو عبارة):", 
    value="",
    height=100,
    help="""
    ✨ يمكنك البحث بأي كلمة أو عبارة:
    
    أمثلة للبحث:
    • كلمة واحدة: بغداد
    • عدة كلمات: الرئيس، الوزير، الحكومة
    • عبارات: الشرق الأوسط، كرة القدم
    • أي موضوع: كورونا، اقتصاد، تعليم
    
    💡 ملاحظات:
    - اتركه فارغاً لعرض جميع الأخبار
    - استخدم الفاصلة للفصل بين الكلمات
    - البحث يشمل العناوين والملخصات
    - يدعم البحث الجزئي والمرادفات
    """
)

# معالجة الكلمات المفتاحية
keywords = []
if keywords_input.strip():
    # تقسيم النص إلى كلمات مفتاحية
    raw_keywords = [kw.strip() for kw in keywords_input.split(",")]
    # إزالة الكلمات الفارغة
    keywords = [kw for kw in raw_keywords if kw]

# عرض الكلمات المفتاحية المُدخلة
if keywords:
    st.sidebar.success(f"✅ تم تحديد {len(keywords)} كلمة مفتاحية للبحث")
    with st.sidebar.expander("📝 الكلمات المفتاحية المحددة"):
        for i, keyword in enumerate(keywords, 1):
            st.write(f"{i}. **{keyword}**")
else:
    st.sidebar.info("🌐 سيتم عرض جميع الأخبار (بدون فلترة)")

category_filter = st.sidebar.selectbox(
    "📁 اختر التصنيف:", 
    ["الكل"] + list(category_keywords.keys()),
    help="فلترة الأخبار حسب التصنيف التلقائي"
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
    
    # خيارات البحث المتقدم
    st.markdown("#### 🔍 خيارات البحث المتقدم")
    search_in_title = st.checkbox("البحث في العناوين", True)
    search_in_summary = st.checkbox("البحث في الملخصات", True)
    use_partial_search = st.checkbox("البحث الجزئي", True, help="البحث عن أجزاء من الكلمات")
    use_synonyms = st.checkbox("استخدام المرادفات", True, help="البحث في المرادفات والكلمات ذات الصلة")

run = st.sidebar.button("📥 جلب الأخبار", type="primary", help="ابدأ عملية جلب وتحليل الأخبار")

# معلومات إضافية في الشريط الجانبي
st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 نصائح للبحث الفعّال")
st.sidebar.markdown("""
**🎯 أمثلة للبحث:**
- `بغداد، البصرة، أربيل` - مدن عراقية
- `كورونا، صحة، لقاح` - مواضيع صحية  
- `نفط، اقتصاد، استثمار` - مواضيع اقتصادية
- `انتخابات، برلمان، حكومة` - مواضيع سياسية

**✨ ميزات البحث:**
- البحث في أي كلمة أو عبارة
- لا حاجة للالتزام بكلمات محددة
- البحث الذكي بالمرادفات
- البحث الجزئي للكلمات الطويلة
""")

# عرض النتائج
if run:
    # التحقق من صحة البيانات المُدخلة
    if date_from > date_to:
        st.error("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        st.stop()
    
    # عرض معلومات البحث
    st.info(f"""
    🔍 **معلومات البحث:**
    - المصدر: **{selected_source}**
    - الكلمات المفتاحية: **{len(keywords)}** {"كلمة" if keywords else "بدون فلترة"}
    - التصنيف: **{category_filter}**
    - الفترة الزمنية: **{date_from}** إلى **{date_to}**
    - عدد الأخبار المطلوب: **{max_news}** خبر كحد أقصى
    """)
    
    if keywords:
        st.success(f"🎯 البحث عن: {', '.join(keywords)}")
    
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
        
        # إحصائيات سريعة ومحسنة
        st.subheader("📊 إحصائيات الأخبار المجمعة")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("📰 إجمالي الأخبار", len(news))
        with col2:
            categories = [n['category'] for n in news]
            most_common_cat = Counter(categories).most_common(1)[0][0] if categories else "غير محدد"
            st.metric("📁 أكثر تصنيف", most_common_cat)
        with col3:
            positive_news = len([n for n in news if "إيجابي" in n['sentiment']])
            st.metric("😃 أخبار إيجابية", positive_news)
        with col4:
            negative_news = len([n for n in news if "سلبي" in n['sentiment']])
            st.metric("😠 أخبار سلبية", negative_news)
        with col5:
            st.metric("⏱️ وقت المعالجة", f"{processing_time}s")
        
        # عرض أكثر الكلمات تكراراً بشكل بارز
        st.subheader("🔤 الكلمات الأكثر تكراراً في الأخبار")
        all_text = " ".join([n['title'] + " " + n['summary'] for n in news])
        # تنظيف النص وتحسين البحث
        words = re.findall(r'\b[أ-ي]{2,}\b', all_text)  # كلمات عربية من حرفين فأكثر
        word_freq = Counter(words).most_common(20)  # أهم 20 كلمة
        
        if word_freq:
            # عرض الكلمات في شكل جدول منظم
            col_words1, col_words2 = st.columns(2)
            
            with col_words1:
                st.markdown("**الكلمات الأكثر تكراراً (1-10):**")
                for i, (word, freq) in enumerate(word_freq[:10], 1):
                    percentage = (freq / len(news)) * 100
                    st.write(f"{i}. **{word}**: {freq} مرة ({percentage:.1f}% من الأخبار)")
            
            with col_words2:
                st.markdown("**الكلمات الأكثر تكراراً (11-20):**")
                for i, (word, freq) in enumerate(word_freq[10:20], 11):
                    percentage = (freq / len(news)) * 100
                    st.write(f"{i}. **{word}**: {freq} مرة ({percentage:.1f}% من الأخبار)")
        
        # إضافة مربع معلومات عن التحليل
        st.info(f"""
        📈 **ملخص التحليل:**
        - تم تحليل **{len(news)}** خبر من مصدر **{selected_source}**
        - تم استخراج **{len(word_freq)}** كلمة مختلفة
        - أكثر كلمة تكراراً: **{word_freq[0][0]}** ({word_freq[0][1]} مرة) {f"إذا كانت متوفرة" if word_freq else ""}
        - التصنيف الأكثر شيوعاً: **{most_common_cat}**
        - نسبة الأخبار الإيجابية: **{(positive_news/len(news)*100):.1f}%**
        - البحث المستخدم: **{"مفتوح" if keywords else "شامل"}** {"(" + ", ".join(keywords[:3]) + "...)" if len(keywords) > 3 else "(" + ", ".join(keywords) + ")" if keywords else ""}
        """)
        
        st.markdown("---")
        
        # عرض الأخبار بتصميم محسن
        st.subheader("📑 الأخبار المجمعة")
        
        for i, item in enumerate(news[:max_news], 1):
            # حاوية رئيسية مع تصميم أنيق
            with st.container():
                # إنشاء أعمدة للتخطيط
                if item.get('image'):
                    col_image, col_content = st.columns([1, 5])  # عمود أصغر للصورة، أكبر للمحتوى
                    
                    with col_image:
                        st.image(
                            item['image'], 
                            width=80,  # تصغير أكثر للصورة
                            caption="",
                            use_column_width=False
                        )
                    
                    with col_content:
                        # العنوان
                        st.markdown(f"### 📰 {item['title']}")
                        
                        # معلومات سريعة في صف واحد
                        info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                        with info_col1:
                            st.markdown(f"**🏢 {item['source']}**")
                        with info_col2:
                            st.markdown(f"**📁 {item['category']}**")
                        with info_col3:
                            st.markdown(f"**🎭 {item['sentiment']}**")
                        with info_col4:
                            st.markdown(f"**📅 {item['published'].strftime('%m-%d %H:%M')}**")
                        
                        # الملخص المحسن
                        st.markdown("**📄 الملخص التفصيلي:**")
                        st.markdown(f">{item['summary']}")
                        
                        # الرابط
                        st.markdown(f"🔗 **[قراءة المقال كاملاً ↗]({item['link']})**")
                
                else:
                    # تخطيط بدون صورة
                    st.markdown(f"### 📰 {item['title']}")
                    
                    # معلومات سريعة
                    info_col1, info_col2, info_col3, info_col4, info_col5 = st.columns(5)
                    with info_col1:
                        st.markdown(f"**🏢 {item['source']}**")
                    with info_col2:
                        st.markdown(f"**📁 {item['category']}**")
                    with info_col3:
                        st.markdown(f"**🎭 {item['sentiment']}**")
                    with info_col4:
                        st.markdown(f"**📅 {item['published'].strftime('%Y-%m-%d')}**")
                    with info_col5:
                        st.markdown(f"**🔧 {item.get('extraction_method', 'غير محدد')}**")
                    
                    # الملخص في مربع منفصل
                    st.markdown("**📄 الملخص التفصيلي:**")
                    st.info(item['summary'])
                    
                    # الرابط
                    st.markdown(f"🔗 **[قراءة المقال كاملاً ↗]({item['link']})**")
                
                # إبراز الكلمات المفتاحية الموجودة في الخبر
                if keywords:
                    found_keywords = []
                    full_text = (item['title'] + " " + item['summary']).lower()
                    for keyword in keywords:
                        if keyword.lower() in full_text:
                            found_keywords.append(keyword)
                    
                    if found_keywords:
                        st.markdown(f"🎯 **الكلمات المطابقة:** {', '.join(found_keywords)}")
                
                # خط فاصل أنيق
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
            
            st.subheader("🔤 تفصيل الكلمات المتكررة")
            all_text = " ".join([n['title'] + " " + n['summary'] for n in news])
            # تنظيف النص
            words = re.findall(r'\b[أ-ي]{2,}\b', all_text)  # كلمات عربية من حرفين فأكثر
            word_freq = Counter(words).most_common(30)  # أول 30 كلمة
            
            if word_freq:
                st.markdown("**أهم 30 كلمة في الأخبار:**")
                cols = st.columns(3)
                for i, (word, freq) in enumerate(word_freq):
                    with cols[i % 3]:
                        percentage = (freq / len(news)) * 100
                        st.write(f"**{word}**: {freq} مرة ({percentage:.1f}%)")
            
            # تحليل الكلمات المفتاحية المطابقة
            if keywords:
                st.subheader("🎯 تحليل مطابقة الكلمات المفتاحية")
                keyword_matches = {}
                
                for news_item in news:
                    full_text = (news_item['title'] + " " + news_item['summary']).lower()
                    for keyword in keywords:
                        if keyword.lower() in full_text:
                            if keyword not in keyword_matches:
                                keyword_matches[keyword] = 0
                            keyword_matches[keyword] += 1
                
                if keyword_matches:
                    st.markdown("**معدل مطابقة الكلمات المفتاحية:**")
                    for keyword, count in sorted(keyword_matches.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / len(news)) * 100
                        st.write(f"• **{keyword}**: {count} أخبار ({percentage:.1f}%)")
                else:
                    st.warning("لم تُطابق أي من الكلمات المفتاحية المحددة في الأخبار المُجمعة")
    
    else:
        st.warning("❌ لم يتم العثور على أخبار بالشروط المحددة")
        
        # اقتراحات للمساعدة
        st.markdown("### 💡 اقتراحات لتحسين البحث:")
        suggestions = [
            "🔍 **وسع نطاق البحث**: جرب كلمات مفتاحية أكثر عمومية",
            "📅 **وسع الفترة الزمنية**: اختر فترة زمنية أطول",
            "🌐 **غير المصدر**: جرب مصدر أخبار مختلف",
            "📁 **غير التصنيف**: اختر 'الكل' بدلاً من تصنيف محدد",
            "🔤 **تبسيط الكلمات**: استخدم كلمات أبسط وأكثر شيوعاً"
        ]
        
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")
        
        if keywords:
            st.info(f"💭 **تم البحث عن:** {', '.join(keywords)}")
            st.markdown("جرب كلمات مفتاحية مختلفة أو اتركها فارغة لعرض جميع الأخبار")
        
        st.markdown(f"🔗 **[زيارة {selected_source} مباشرة]({source_info['url']})**")

# معلومات في الشريط الجانبي
st.sidebar.markdown("---")
st.sidebar.success("✅ **البحث المفتوح متاح الآن!**")
st.sidebar.info("""
🚀 **ميزات البحث الجديدة:**
- 🔍 بحث مفتوح بأي كلمة
- 📝 لا حاجة لكلمات محددة مسبقاً  
- 🧠 بحث ذكي بالمرادفات
- 🔤 بحث جزئي للكلمات
- 🎯 إبراز الكلمات المطابقة
- 📊 تحليل مطابقة متقدم

**تقنيات متقدمة:**
- جلب RSS تلقائي
- تحليل مواقع الويب
- تصنيف ذكي للأخبار
- تحليل المشاعر
- إزالة المحتوى المكرر
- ملخصات ذكية مطولة
""")

# معلومات تقنية محدثة
with st.expander("ℹ️ معلومات تقنية - تحديث البحث المفتوح"):
    st.markdown("""
    ### 🆕 **أحدث التحسينات - البحث المفتوح:**
    
    #### 🔍 **البحث المفتوح الجديد:**
    - **حرية كاملة في البحث**: يمكنك البحث بأي كلمة أو عبارة
    - **لا قيود على الكلمات**: غير محدود بقاموس كلمات محدد مسبقاً
    - **بحث متعدد الطبقات**: يبحث في العناوين والملخصات معاً
    - **مرونة في الإدخال**: دعم الكلمات المفردة والعبارات المركبة
    
    #### 🧠 **خوارزميات البحث الذكية:**
    - **`flexible_keyword_search()`**: بحث مباشر ومرن
    - **`enhanced_keyword_search()`**: بحث متقدم بالمرادفات
    - **البحث الجزئي**: العثور على أجزاء الكلمات الطويلة
    - **البحث بالجذور**: تحليل الجذور العربية التقريبي
    - **دعم المرادفات**: قاموس مرادفات قابل للتوسيع
    
    #### 📝 **ميزات الواجهة المحسّنة:**
    - **مربع نص كبير**: لسهولة إدخال الكلمات المتعددة
    - **عرض الكلمات المحددة**: قائمة بالكلمات المفتاحية المُدخلة
    - **إبراز المطابقات**: عرض الكلمات المطابقة لكل خبر
    - **تحليل متقدم**: إحصائيات مطابقة الكلمات المفتاحية
    - **نصائح تفاعلية**: أمثلة وإرشادات للبحث الفعّال
    
    #### 🎯 **أمثلة للاستخدام:**
    
    **البحث البسيط:**
    ```
    بغداد
    كورونا
    اقتصاد
    ```
    
    **البحث المتعدد:**
    ```
    الرئيس، الوزير، الحكومة
    كرة القدم، رياضة، بطولة
    ```
    
    **البحث بالعبارات:**
    ```
    الشرق الأوسط
    وزارة الداخلية
    كأس العالم
    ```
    
    **البحث الموضوعي:**
    ```
    تعليم، جامعة، طلاب
    صحة، مستشفى، لقاح
    تكنولوجيا، ذكاء اصطناعي
    ```
    
    #### 🔧 **التحسينات التقنية:**
    
    **معالجة النصوص:**
    - تنظيف الكلمات المفتاحية من المسافات الزائدة
    - تحويل الأحرف للحالة الصغيرة للمقارنة
    - دعم البحث في النصوص العربية والإنجليزية
    
    **خوارزميات البحث:**
    ```python
    def enhanced_keyword_search(text, keywords):
        # بحث مباشر
        if keyword in text_lower:
            return True
        
        # بحث بالمرادفات
        for synonym in synonyms:
            if synonym in text_lower:
                return True
        
        # بحث جزئي للكلمات الطويلة
        if len(keyword) > 4:
            parts = [keyword[i:i+4] for i in range(len(keyword)-3)]
            for part in parts:
                if part in text_lower:
                    return True
    ```
    
    **قاموس المرادفات القابل للتوسيع:**
    ```python
    synonyms_dict = {
        "حرب": ["قتال", "معركة", "صراع", "نزاع"],
        "اقتصاد": ["مال", "تجارة", "استثمار", "بورصة"],
        "سياسة": ["حكومة", "دولة", "رئيس", "وزير"],
        # يمكن إضافة المزيد...
    }
    ```
    
    #### 📊 **مميزات التحليل الجديدة:**
    - **إحصائيات المطابقة**: نسبة مطابقة كل كلمة مفتاحية
    - **عرض الكلمات المطابقة**: إبراز الكلمات الموجودة في كل خبر
    - **تحليل شامل**: ربط الكلمات المفتاحية بالنتائج
    - **اقتراحات ذكية**: نصائح لتحسين البحث عند عدم وجود نتائج
    
    #### 🚀 **فوائد النظام الجديد:**
    
    **للمستخدم العادي:**
    - سهولة البحث بأي كلمة يريدها
    - عدم الحاجة لمعرفة الكلمات المحددة مسبقاً
    - مرونة في التعبير عن اهتماماته
    
    **للمستخدم المتقدم:**
    - بحث دقيق بعبارات مخصصة
    - استخدام المرادفات للبحث الشامل
    - تحليل متقدم لنتائج البحث
    
    **للمطورين:**
    - كود قابل للتوسيع والتطوير
    - خوارزميات بحث متقدمة
    - معالجة ذكية للنصوص العربية
    
    ### 🎯 **الخلاصة:**
    النظام الآن يوفر **بحث مفتوح وحر** بدلاً من الاقتصار على كلمات محددة مسبقاً، مما يجعله أكثر مرونة وقابلية للاستخدام في جميع السيناريوهات والمواضيع.
    """)
