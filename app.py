import streamlit as st
import feedparser
import pandas as pd
import io
from datetime import datetime

# -------- استخراج الأخبار من RSS --------
def fetch_news_from_rss(rss_url, keywords):
    feed = feedparser.parse(rss_url)
    news_list = []
    total_entries = len(feed.entries)

    for entry in feed.entries:
        title = entry.title
        summary = entry.get("summary", "")
        link = entry.link
        published = entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if keywords:
            if any(keyword.lower() in (title + " " + summary).lower() for keyword in keywords):
                news_list.append({
                    "تاريخ النشر": published,
                    "العنوان": title,
                    "الوصف": summary,
                    "الرابط": link
                })
        else:
            news_list.append({
                "تاريخ النشر": published,
                "العنوان": title,
                "الوصف": summary,
                "الرابط": link
            })

    return news_list, total_entries

# -------- Streamlit App --------
st.set_page_config(page_title="سكاي نيوز - استخراج الأخبار", layout="centered")

st.title("📰 استخراج آخر الأخبار من Sky News Arabia عبر RSS (محسن)")

# قائمة التصنيفات الجاهزة
rss_feeds = {
    "آخر الأخبار": "https://www.skynewsarabia.com/web/rss/latest",
    "أخبار العالم": "https://www.skynewsarabia.com/web/rss/world",
    "الاقتصاد": "https://www.skynewsarabia.com/web/rss/business",
    "الرياضة": "https://www.skynewsarabia.com/web/rss/sports",
    "التكنولوجيا": "https://www.skynewsarabia.com/web/rss/technology",
    "الصحة": "https://www.skynewsarabia.com/web/rss/health",
    "العلوم": "https://www.skynewsarabia.com/web/rss/science",
    "الفن والترفيه": "https://www.skynewsarabia.com/web/rss/entertainment"
}

# اختيار التصنيف
selected_feed = st.selectbox("اختر قسم الأخبار:", list(rss_feeds.keys()))

# أو أدخل رابط RSS مخصص
custom_rss = st.text_input("🛠️ أو أدخل رابط RSS مخصص (اختياري):", value="")

# إدخال الكلمات المفتاحية
keywords_input = st.text_input("🔎 ادخل الكلمات المفتاحية (مفصولة بفواصل):", value="")
keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []

# زرار البحث
if st.button("🔍 استخراج الأخبار"):
    with st.spinner("جاري استخراج الأخبار..."):
        rss_url = custom_rss if custom_rss else rss_feeds[selected_feed]
        
        news, total_entries = fetch_news_from_rss(rss_url, keywords)
        
        if news:
            st.success(f"✅ تم العثور على {len(news)} خبر يطابق الكلمات المفتاحية من أصل {total_entries} خبر متاح.")
            df = pd.DataFrame(news)
            st.dataframe(df)

            # حفظ الملف
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="📥 تحميل الأخبار كملف Excel",
                data=output.getvalue(),
                file_name="آخر_الأخبار_skynews.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            if total_entries > 0:
                st.warning(f"⚠️ لم يتم العثور على أخبار تطابق الكلمات، ولكن تم تحميل {total_entries} خبر من المصدر.")
            else:
                st.error("❌ لم يتم العثور على أي أخبار في المصدر المحدد.")
