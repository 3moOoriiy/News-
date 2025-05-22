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

# حروف الجر والكلمات الصغيرة التي يجب تجنبها
STOP_WORDS = {
    'في', 'من', 'إلى', 'على', 'عن', 'مع', 'بعد', 'قبل', 'تحت', 'فوق', 'حول', 'خلال', 'عبر', 'ضد', 'نحو', 'عند', 'لدى',
    'أن', 'إن', 'كان', 'كانت', 'يكون', 'تكون', 'هو', 'هي', 'هم', 'هن', 'أنت', 'أنتم', 'أنتن', 'أنا', 'نحن',
    'هذا', 'هذه', 'ذلك', 'تلك', 'التي', 'الذي', 'اللذان', 'اللاتي', 'اللواتي', 'بعض', 'كل', 'جميع',
    'أو', 'أم', 'لكن', 'لكن', 'غير', 'سوى', 'فقط', 'أيضا', 'أيضاً', 'كذلك', 'أيضاً', 'حيث', 'بينما', 'كما',
    'قد', 'لقد', 'قال', 'قالت', 'أضاف', 'أضافت', 'أكد', 'أكدت', 'ذكر', 'ذكرت', 'أشار', 'أشارت'
}

def clean_text_for_analysis(text):
    """تنظيف النص وإزالة الكلمات غير المفيدة"""
    if not text:
        return ""
    
    # تنظيف النص من HTML والرموز الخاصة
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\u0600-\u06FF\s]', ' ', text)  # الاحتفاظ بالعربية والمسافات فقط
    text = re.sub(r'\s+', ' ', text).strip()
    
    # تقسيم إلى كلمات وفلترة
    words = text.split()
    filtered_words = []
    
    for word in words:
        word = word.strip()
        # تجاهل الكلمات القصيرة (أقل من 3 أحرف) وحروف الجر
        if len(word) >= 3 and word not in STOP_WORDS:
            filtered_words.append(word)
    
    return ' '.join(filtered_words)

def extract_meaningful_words(text, min_length=3, max_words=50):
    """استخراج الكلمات المفيدة فقط"""
    if not text:
        return []
    
    cleaned_text = clean_text_for_analysis(text)
    words = cleaned_text.split()
    
    # فلترة إضافية للكلمات المفيدة
    meaningful_words = []
    for word in words:
        if (len(word) >= min_length and 
            word not in STOP_WORDS and 
            not word.isdigit() and
            len(word) <= 15):  # تجنب الكلمات الطويلة جداً
            meaningful_words.append(word)
    
    return meaningful_words[:max_words]

def open_search(text, search_terms):
    """بحث مفتوح تماماً بدون قيود مسبقة"""
    if not text or not search_terms:
        return True  # إذا لم تكن هناك كلمات بحث، اعرض كل شيء
    
    text_clean = text.lower().strip()
    
    for term in search_terms:
        term = term.strip().lower()
        if not term or len(term) < 2:
            continue
            
        # البحث المباشر
        if term in text_clean:
            return True
            
        # البحث الجزئي للكلمات الطويلة
        if len(term) > 5:
            # تقسيم الكلمة إلى أجزاء للبحث الجزئي
            for i in range(len(term) - 3):
                part = term[i:i+4]
                if part in text_clean:
                    return True
    
    return False

def smart_categorize(text):
    """تصنيف ذكي مبني على تحليل المحتوى وليس كلمات مسجلة"""
    if not text:
        return "غير مصنف"
    
    text_lower = text.lower()
    
    # كلمات دلالية للتصنيفات (يمكن توسيعها ديناميكياً)
    category_patterns = {
        "سياسة": ["رئيس", "وزير", "حكومة", "انتخابات", "برلمان", "مجلس", "دولة", "سياسة", "قانون", "عدالة"],
        "اقتصاد": ["اقتصاد", "مال", "استثمار", "بنك", "تجارة", "سوق", "أسهم", "عملة", "نفط", "طاقة"],
        "رياضة": ["كرة", "لاعب", "مباراة", "فريق", "بطولة", "دوري", "رياضة", "ملعب", "تدريب", "نادي"],
        "صحة": ["صحة", "طب", "مرض", "علاج", "مستشفى", "دواء", "فيروس", "لقاح", "طبيب", "مريض"],
        "تعليم": ["تعليم", "جامعة", "مدرسة", "طالب", "معلم", "دراسة", "تربية", "امتحان", "كلية", "أكاديمي"],
        "تكنولوجيا": ["تقنية", "تكنولوجيا", "كمبيوتر", "إنترنت", "تطبيق", "برمجة", "ذكاء", "رقمي", "هاتف", "شبكة"]
    }
    
    scores = {}
    for category, words in category_patterns.items():
        score = sum(1 for word in words if word in text_lower)
        if score > 0:
            scores[category] = score
    
    return max(scores, key=scores.get) if scores else "عام"

def analyze_sentiment_simple(text):
    """تحليل بسيط للمشاعر"""
    if not text:
        return "😐 محايد"
    
    positive_words = ["نجح", "تقدم", "إيجابي", "جيد", "ممتاز", "رائع", "تطور", "ازدهار", "انتصار", "فوز"]
    negative_words = ["فشل", "سيء", "خطأ", "مشكلة", "أزمة", "تراجع", "انهيار", "هزيمة", "كارثة", "قلق"]
    
    text_lower = text.lower()
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return "😃 إيجابي"
    elif negative_count > positive_count:
        return "😠 سلبي"
    else:
        return "😐 محايد"

def create_enhanced_summary(title, content, max_length=200):
    """إنشاء ملخص محسن وطويل"""
    if not content or content.strip() == title.strip():
        return title + " - للمزيد من التفاصيل، يرجى زيارة الرابط الأصلي."
    
    # تنظيف المحتوى
    content_clean = re.sub(r'<[^>]+>', '', content)
    content_clean = re.sub(r'\s+', ' ', content_clean).strip()
    
    # دمج العنوان والمحتوى بذكاء
    if title not in content_clean:
        full_text = title + ". " + content_clean
    else:
        full_text = content_clean
    
    # تقطيع إلى جمل
    sentences = re.split(r'[.!?]+', full_text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    if not sentences:
        return title
    
    # بناء ملخص تدريجي
    summary = ""
    for sentence in sentences:
        if len(summary + sentence) <= max_length:
            summary += sentence + ". "
        else:
            break
    
    if not summary.strip():
        summary = title
    
    # إضافة نقاط في النهاية إذا كان مقطوعاً
    if len(full_text) > len(summary) and not summary.endswith("..."):
        summary = summary.rstrip(". ") + "..."
    
    return summary.strip()

def safe_web_request(url, timeout=10):
    """طلب ويب آمن مع معالجة شاملة للأخطاء"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        st.warning(f"تعذر الوصول إلى {url}: {str(e)}")
        return None

def fetch_rss_news(source_name, url, search_terms, date_from, date_to):
    """جلب الأخبار من RSS مع بحث مفتوح"""
    try:
        with st.spinner(f"🔄 جاري جلب الأخبار من {source_name}..."):
            feed = feedparser.parse(url)
            
        if not hasattr(feed, 'entries') or len(feed.entries) == 0:
            return []
        
        news_list = []
        
        for entry in feed.entries:
            try:
                title = entry.get('title', 'بدون عنوان').strip()
                summary = entry.get('summary', entry.get('description', '')).strip()
                
                # جلب المحتوى الكامل إن وجد
                content = entry.get('content', [])
                if content and isinstance(content, list) and len(content) > 0:
                    full_content = content[0].get('value', summary)
                else:
                    full_content = summary
                
                link = entry.get('link', '')
                published_str = entry.get('published', '')
                
                # معالجة التاريخ
                try:
                    if published_str:
                        # تجربة عدة تنسيقات للتاريخ
                        for fmt in ['%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S']:
                            try:
                                published_dt = datetime.strptime(published_str.strip(), fmt)
                                break
                            except:
                                continue
                        else:
                            published_dt = datetime.now()
                    else:
                        published_dt = datetime.now()
                except:
                    published_dt = datetime.now()
                
                # فلترة التاريخ
                if not (date_from <= published_dt.date() <= date_to):
                    continue
                
                # إنشاء ملخص محسن
                enhanced_summary = create_enhanced_summary(title, full_content)
                
                # البحث المفتوح
                full_search_text = title + " " + enhanced_summary
                if search_terms and not open_search(full_search_text, search_terms):
                    continue
                
                # البحث عن صورة
                image_url = ""
                if hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url', '')
                
                news_item = {
                    "source": source_name,
                    "title": title,
                    "summary": enhanced_summary,
                    "link": link,
                    "published": published_dt,
                    "image": image_url,
                    "sentiment": analyze_sentiment_simple(enhanced_summary),
                    "category": smart_categorize(full_search_text)
                }
                
                news_list.append(news_item)
                
            except Exception as e:
                continue
        
        return news_list[:50]  # حد أقصى 50 خبر
        
    except Exception as e:
        st.error(f"خطأ في جلب الأخبار من {source_name}: {str(e)}")
        return []

def export_to_excel(news_data):
    """تصدير البيانات إلى Excel"""
    df = pd.DataFrame(news_data)
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='الأخبار')
    
    buffer.seek(0)
    return buffer

def export_to_word(news_data):
    """تصدير البيانات إلى Word"""
    doc = Document()
    doc.add_heading('تقرير الأخبار', 0)
    doc.add_paragraph(f'تاريخ التقرير: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    doc.add_paragraph(f'عدد الأخبار: {len(news_data)}')
    doc.add_paragraph('---')
    
    for i, news in enumerate(news_data, 1):
        doc.add_heading(f'{i}. {news["title"]}', level=2)
        doc.add_paragraph(f"المصدر: {news['source']}")
        doc.add_paragraph(f"التصنيف: {news['category']}")
        doc.add_paragraph(f"المشاعر: {news['sentiment']}")
        doc.add_paragraph(f"التاريخ: {news['published'].strftime('%Y-%m-%d %H:%M')}")
        doc.add_paragraph(f"الملخص: {news['summary']}")
        doc.add_paragraph(f"الرابط: {news['link']}")
        doc.add_paragraph('---')
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# مصادر الأخبار
NEWS_SOURCES = {
    "الجزيرة": "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9",
    "BBC العربية": "http://feeds.bbci.co.uk/arabic/rss.xml",
    "العربية": "https://www.alarabiya.net/ar/rss.xml",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "France24 عربي": "https://www.france24.com/ar/rss",
    "سكاي نيوز عربية": "https://www.skynewsarabia.com/web/rss",
    "الشرق الأوسط": "https://aawsat.com/rss/latest",
    "CNN العربية": "https://arabic.cnn.com/api/v1/rss/rss.xml"
}

# واجهة المستخدم
st.sidebar.header("🔍 البحث المفتوح والمرن")

# اختيار المصدر
selected_source = st.sidebar.selectbox(
    "📡 اختر مصدر الأخبار:",
    list(NEWS_SOURCES.keys()),
    help="اختر المصدر الإخباري الذي تريد البحث فيه"
)

# البحث المفتوح
st.sidebar.markdown("### 🆓 بحث حر ومفتوح")
search_input = st.sidebar.text_area(
    "ابحث عن أي شيء تريده:",
    value="",
    height=120,
    help="""
    🔍 ابحث بحرية تامة عن أي موضوع:
    
    مثال:
    • كلمة واحدة: كورونا
    • عدة كلمات: بغداد، الرئيس، كرة القدم  
    • عبارة: الذكاء الاصطناعي
    • موضوع: التعليم في العراق
    
    ✨ لا توجد قيود - ابحث عن أي شيء!
    """
)

# معالجة كلمات البحث
search_terms = []
if search_input.strip():
    # تقسيم النص بالفواصل أو المسافات
    raw_terms = re.split(r'[،,\s]+', search_input.strip())
    search_terms = [term.strip() for term in raw_terms if term.strip() and len(term.strip()) > 1]

# عرض كلمات البحث
if search_terms:
    st.sidebar.success(f"✅ سيتم البحث عن: {len(search_terms)} كلمة/عبارة")
    with st.sidebar.expander("📝 كلمات البحث المحددة"):
        for i, term in enumerate(search_terms, 1):
            st.write(f"{i}. **{term}**")
else:
    st.sidebar.info("🌐 سيتم عرض جميع الأخبار")

# إعدادات التاريخ
col1, col2 = st.sidebar.columns(2)
with col1:
    date_from = st.date_input("من تاريخ:", datetime.today() - timedelta(days=7))
with col2:
    date_to = st.date_input("إلى تاريخ:", datetime.today())

# إعدادات إضافية
with st.sidebar.expander("⚙️ إعدادات إضافية"):
    max_articles = st.slider("عدد الأخبار الأقصى:", 5, 50, 20)
    show_images = st.checkbox("عرض الصور", True)
    detailed_analysis = st.checkbox("تحليل مفصل", True)

# زر البحث
search_button = st.sidebar.button("🔍 ابدأ البحث", type="primary")

# المحتوى الرئيسي
if search_button:
    if date_from > date_to:
        st.error("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
        st.stop()
    
    # عرض معلومات البحث
    st.info(f"""
    🎯 **تفاصيل البحث:**
    - المصدر: **{selected_source}**
    - كلمات البحث: **{len(search_terms)}** {"كلمة" if search_terms else "بحث شامل"}
    - الفترة: من **{date_from}** إلى **{date_to}**
    """)
    
    if search_terms:
        st.success(f"🔍 البحث عن: {', '.join(search_terms[:5])}{'...' if len(search_terms) > 5 else ''}")
    
    # جلب الأخبار
    start_time = time.time()
    
    news_data = fetch_rss_news(
        selected_source,
        NEWS_SOURCES[selected_source],
        search_terms,
        date_from,
        date_to
    )
    
    processing_time = round(time.time() - start_time, 2)
    
    if news_data:
        # تحديد العدد المطلوب
        news_data = news_data[:max_articles]
        
        st.success(f"🎉 تم جلب {len(news_data)} خبر في {processing_time} ثانية")
        
        # إحصائيات سريعة
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📰 الأخبار", len(news_data))
        
        with col2:
            categories = [item['category'] for item in news_data]
            top_category = Counter(categories).most_common(1)[0][0] if categories else "غير محدد"
            st.metric("📁 أكثر تصنيف", top_category)
        
        with col3:
            sentiments = [item['sentiment'] for item in news_data]
            positive_count = len([s for s in sentiments if "إيجابي" in s])
            st.metric("😃 إيجابية", positive_count)
        
        with col4:
            st.metric("⚡ سرعة المعالجة", f"{processing_time}s")
        
        # تحليل الكلمات الأكثر تكراراً
        if detailed_analysis:
            st.subheader("📊 تحليل المحتوى")
            
            all_text = " ".join([item['title'] + " " + item['summary'] for item in news_data])
            meaningful_words = extract_meaningful_words(all_text, min_length=3, max_words=100)
            
            if meaningful_words:
                word_counts = Counter(meaningful_words).most_common(20)
                
                st.markdown("**🔤 أهم الكلمات في الأخبار:**")
                
                cols = st.columns(4)
                for i, (word, count) in enumerate(word_counts):
                    with cols[i % 4]:
                        percentage = (count / len(news_data)) * 100
                        st.metric(word, f"{count}", f"{percentage:.1f}%")
        
        # عرض الأخبار
        st.subheader("📰 نتائج البحث")
        
        for i, article in enumerate(news_data, 1):
            with st.container():
                # العنوان والمعلومات الأساسية
                st.markdown(f"### {i}. {article['title']}")
                
                # معلومات سريعة
                info_cols = st.columns(4)
                with info_cols[0]:
                    st.markdown(f"**📡 {article['source']}**")
                with info_cols[1]:
                    st.markdown(f"**📁 {article['category']}**")
                with info_cols[2]:
                    st.markdown(f"**🎭 {article['sentiment']}**")
                with info_cols[3]:
                    st.markdown(f"**📅 {article['published'].strftime('%m-%d %H:%M')}**")
                
                # الصورة والملخص
                if show_images and article.get('image'):
                    col_img, col_text = st.columns([1, 4])
                    with col_img:
                        st.image(article['image'], width=100)
                    with col_text:
                        st.markdown("**📝 الملخص:**")
                        st.write(article['summary'])
                else:
                    st.markdown("**📝 الملخص:**")
                    st.info(article['summary'])
                
                # الرابط
                st.markdown(f"🔗 **[اقرأ المقال كاملاً]({article['link']})**")
                
                # إبراز الكلمات المطابقة
                if search_terms:
                    article_text = (article['title'] + " " + article['summary']).lower()
                    matched_terms = [term for term in search_terms if term.lower() in article_text]
                    if matched_terms:
                        st.success(f"🎯 كلمات مطابقة: {', '.join(matched_terms)}")
                
                st.markdown("---")
        
        # أدوات التصدير
        st.subheader("📤 تصدير النتائج")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            excel_file = export_to_excel(news_data)
            st.download_button(
                "📊 تحميل Excel",
                data=excel_file,
                file_name=f"news_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            word_file = export_to_word(news_data)
            st.download_button(
                "📄 تحميل Word",
                data=word_file,
                file_name=f"news_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        with col3:
            json_data = json.dumps(news_data, ensure_ascii=False, default=str, indent=2)
            st.download_button(
                "💾 تحميل JSON",
                data=json_data.encode('utf-8'),
                file_name=f"news_{selected_source}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
    else:
        st.warning("❌ لم يتم العثور على أخبار مطابقة لشروط البحث")
        
        st.markdown("### 💡 اقتراحات:")
        st.markdown("""
        - جرب كلمات بحث مختلفة أو أكثر عمومية
        - وسع الفترة الزمنية للبحث  
        - تأكد من كتابة الكلمات بشكل صحيح
        - جرب مصدر أخبار آخر
        """)

# معلومات في الشريط الجانبي
st.sidebar.markdown("---")
st.sidebar.success("✅ **بحث مفتوح 100%**")
st.sidebar.info("""
🔍 **مميزات البحث الجديد:**
- بحث حر بأي كلمة تريدها
- لا توجد كلمات محددة مسبقاً
- تنظيف ذكي للنصوص
- إزالة حروف الجر والكلمات الصغيرة
- تحليل محتوى متقدم
- استخراج الكلمات المفيدة فقط
""")

# معلومات تقنية
with st.expander("ℹ️ معلومات تقنية"):
    st.markdown("""
    ### 🔧 التحسينات التقنية:
    
    **البحث المفتوح:**
    - إزالة جميع القيود المسبقة على الكلمات
    - بحث مرن في أي نص أو كلمة
    - معالجة ذكية للنصوص العربية
    
    **تنظيف النصوص:**
    - إزالة حروف الجر والكلمات الصغيرة
    - فلترة الكلمات غير المفيدة
    - الاحتفاظ بالكلمات الطويلة والمفيدة فقط
    
    **التصنيف الذكي:**
    - تصنيف ديناميكي بناء على المحتوى
    - عدم الاعتماد على قوائم كلمات محددة
    - تحليل سياقي للنصوص
    """)
