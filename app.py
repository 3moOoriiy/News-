import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import io

# -------- استخراج الأخبار باستخدام requests و BeautifulSoup --------
def fetch_news(url, keywords):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        st.error(f"❌ مشكلة في تحميل الصفحة: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    news_list = []

    # نحاول نلاقي قسم "آخر الأخبار"
    section = soup.find('section', class_='latest-news')  # نحاول نلاقي أقرب Section لو موجود
    if not section:
        st.warning("⚠️ مش لاقي قسم 'آخر الأخبار' بالطريقة العادية، بحاول أجيب أول الكروت.")
        cards = soup.select('div.comp_1_item')
    else:
        cards = section.select('div.comp_1_item')

    cards = cards[:10]  # أول 10 أخبار فقط

    for card in cards:
        title_el = card.find('h3', class_='comp_1_item_header')
        link_el = card.find('a')

        if title_el and link_el:
            title = title_el.get_text(strip=True)
            link = link_el.get('href')
            if not link.startswith("http"):
                link = "https://www.skynewsarabia.com" + link  # لو الرابط نسبي

            if keywords:
                if any(keyword.lower() in title.lower() for keyword in keywords):
                    news_list.append({
                        "تاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "العنوان": title,
                        "الرابط": link
                    })
            else:
                news_list.append({
                    "تاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "العنوان": title,
                    "الرابط": link
                })

    return news_list

# -------- Streamlit App --------
st.set_page_config(page_title="سكاي نيوز - استخراج آخر الأخبار", layout="centered")

st.title("📰 استخراج آخر الأخبار من Sky News Arabia (بدون Selenium)")

# إدخال الرابط
url = st.text_input("ادخل رابط صفحة الأخبار:", value="https://www.skynewsarabia.com/")

# إدخال الكلمات المفتاحية
keywords_input = st.text_input("ادخل الكلمات المفتاحية (مفصولة بفواصل):", value="")
keywords = [kw.strip() for kw in keywords_input.split(",")] if keywords_input else []

# زرار البحث
if st.button("🔍 استخراج الأخبار"):
    with st.spinner("جاري استخراج الأخبار..."):
        news = fetch_news(url, keywords)
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
