import streamlit as st
import feedparser
import pandas as pd
import io
from datetime import datetime

# -------- استخراج الأخبار من RSS --------
def fetch_news_from_rss(rss_url, keywords):
    feed = feedparser.parse(rss_url)
    news_list = []

    for entry in feed.entries:
        title = entry.title
        link = entry.link
        published = entry.get("published", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if keywords:
            if any(keyword.lower() in title.lower() for keyword in keywords):
                news_list.append({
                    "تاريخ النشر": published,
                    "العنوان": title,
                    "الرابط": link
                })
        else:
            news_list.append({
                "تاريخ النشر": published,
                "العنوان": title,
                "الرابط": link
            })

    return news_list

# -------- Streamlit App --------
st.set_page_config(page_title="سكاي نيوز - آخر الأخبار (RSS)", layout="centered")

st.title("📰 استخراج آخر الأخبار من Sky News Arabia عبر RSS")

# إدخال رابط RSS
rss_url = st.text_input("ادخل رابط RSS:", value="https://www.skynewsarabia.com/rss")

# إدخال الكلمات المفتاحية
keywords_input = st.text_input("ادخل الكلمات المفتاحية (مفصولة بفواصل):", value="")
keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []

# زرار البحث
if st.button("🔍 استخراج الأخبار"):
    with st.spinner("جاري استخراج الأخبار..."):
        news = fetch_news_from_rss(rss_url, keywords)
        if news:
            df = pd.DataFrame(news)
            st.success(f"✅ تم استخراج {len(df)} خبر.")

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
            st.warning("⚠️ لم يتم العثور على أخبار تطابق الشروط.")
