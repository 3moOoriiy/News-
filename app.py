
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
st.set_page_config(page_title="أداة استخراج الأخبار من مصادر متعددة", layout="centered")

st.title("📰 استخراج آخر الأخبار من مصادر موثوقة عبر RSS")

# قائمة التصنيفات الجاهزة
rss_feeds = {
    "الجزيرة - كل الأخبار": "https://www.aljazeera.net/xml/rss/all.xml",
    "العربية - آخر الأخبار": "https://www.alarabiya.net/.mrss/ar.xml",
    "BBC عربي": "http://feeds.bbci.co.uk/arabic/rss.xml"
}

# اختيار التصنيف
selected_feed = st.selectbox("اختر مصدر الأخبار:", list(rss_feeds.keys()))

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
                file_name="آخر_الأخبار.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            if total_entries > 0:
                st.warning(f"⚠️ لم يتم العثور على أخبار تطابق الكلمات، ولكن تم تحميل {total_entries} خبر من المصدر.")
            else:
                st.error("❌ لم يتم العثور على أي أخبار في المصدر المحدد.")
