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

from transformers import pipeline

# إعداد الصفحة
st.set_page_config(page_title=":newspaper: أداة الأخبار العربية الذكية", layout="wide")
st.title(":rolled_up_newspaper: أداة إدارة وتحليل الأخبار المتطورة (RSS + Web Scraping)")

# تحميل نماذج التحليل
@st.cache_resource
def get_sentiment_model():
    return pipeline("sentiment-analysis", model="aubmindlab/bert-base-arabertv02-twitter")

@st.cache_resource
def get_summarizer():
    return pipeline("summarization", model="csebuetnlp/mT5_multilingual_XLSum")

sentiment_model = get_sentiment_model()
summarizer = get_summarizer()

# تصنيفات الأخبار
category_keywords = {
    "سياسة": ["رئيس", "وزير", "انتخابات", "برلمان", "سياسة", "حكومة", "نائب", "مجلس", "دولة", "حزب"],
    "رياضة": ["كرة", "لاعب", "مباراة", "دوري", "هدف", "فريق", "بطولة", "رياضة", "ملعب", "تدريب"],
    "اقتصاد": ["سوق", "اقتصاد", "استثمار", "بنك", "مال", "تجارة", "صناعة", "نفط", "غاز", "بورصة"],
    "تكنولوجيا": ["تقنية", "تطبيق", "هاتف", "ذكاء", "برمجة", "إنترنت", "رقمي", "حاسوب", "شبكة", "آيفون"],
    "صحة": ["طب", "مرض", "علاج", "مستشفى", "دواء", "صحة", "طبيب", "فيروس", "لقاح", "وباء"],
    "تعليم": ["تعليم", "جامعة", "مدرسة", "طالب", "دراسة", "كلية", "معهد", "تربية", "أكاديمي", "بحث"]
}

def analyze_sentiment(text):
    if not text:
        return ":neutral_face: محايد"
    try:
        result = sentiment_model(text)
        label = result[0]['label']
        if 'POS' in label or 'pos' in label or 'إيجابي' in label:
            return ":smiley: إيجابي"
        elif 'NEG' in label or 'neg' in label or 'سلبي' in label:
            return ":angry: سلبي"
        else:
            return ":neutral_face: محايد"
    except:
        return ":neutral_face: محايد"

def summarize(text, max_words=40):
    if not text or len(text.strip().split()) < 10:
        return "لا يوجد ملخص متاح"
    try:
        result = summarizer(text, max_length=max_words, min_length=15, do_sample=False)
        return result[0]['summary_text']
    except:
        return text[:max_words] + "..."

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

# دالة لجلب الأخبار من RSS

def fetch_rss_news(source_name, url, keywords, date_from, date_to, chosen_category):
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

                try:
                    published_dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
                except:
                    try:
                        published_dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S%z")
                    except:
                        published_dt = datetime.now()

                if not (date_from <= published_dt.date() <= date_to):
                    continue

                full_text = title + " " + summary
                if keywords and not any(k.lower() in full_text.lower() for k in keywords):
                    continue

                auto_category = detect_category(full_text)
                if chosen_category != "الكل" and auto_category != chosen_category:
                    continue

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
            except:
                continue
        return news_list
    except:
        return []

# يمكنك الآن استخدام الدوال السابقة ضمن واجهة Streamlit التي قمت بإنشائها مسبقًا.
