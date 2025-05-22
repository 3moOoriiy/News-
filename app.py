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

from camel_tools.sentiment import SentimentAnalyzer
from transformers import pipeline

# إعداد الصفحة
st.set_page_config(page_title=":newspaper: أداة الأخبار العربية الذكية", layout="wide")
st.title(":rolled_up_newspaper: أداة إدارة وتحليل الأخبار المتطورة (RSS + Web Scraping)")

# تحميل نماذج التحليل
@st.cache_resource
def get_sentiment_model():
    return SentimentAnalyzer.pretrained()

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
        output = sentiment_model.predict_sentence(text)
        if output == 'pos':
            return ":smiley: إيجابي"
        elif output == 'neg':
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

# --- بقية الكود الذي كتبته سابقًا ---
# كل ما يتعلق بجلب الأخبار، عرضها، الفلاتر، التحليلات، التصدير إلى Word/Excel/JSON
# لا يحتاج تغيير إلا في الدوال التي تم تعديلها أعلاه.
# يمكنك ببساطة نسخ الجزء المتبقي من تطبيقك الأصلي بعد هذا القسم وسيعمل بالكامل.

# إذا أردت، يمكنني دمج كل شيء معًا في ملف نهائي لك بصيغة app.py.
