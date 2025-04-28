
import streamlit as st
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import pandas as pd
from datetime import datetime
import time
import io

# -------- تهيئة Microsoft Edge --------
def initialize_driver():
    edge_options = webdriver.EdgeOptions()
    edge_options.use_chromium = True
    edge_options.add_argument("--headless")  # تشغيل المتصفح في الخلفية
    edge_options.add_argument("--start-maximized")
    return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=edge_options)

# -------- استخراج الأخبار --------
def fetch_news(url, keywords):
    driver = initialize_driver()
    driver.get(url)
    time.sleep(5)  # استنى الموقع يحمل

    news_list = []
    
    try:
        latest_section = driver.find_element(By.XPATH, '//h2/a[@title="آخر الأخبار"]')
        ActionChains(driver).move_to_element(latest_section).perform()
        time.sleep(3)
    except Exception as e:
        st.error(f"❌ مش لاقي قسم آخر الأخبار: {e}")
        driver.quit()
        return []

    # استخراج أول 10 أخبار
    news_items = driver.find_elements(By.CSS_SELECTOR, 'div.comp_1_item')[:10]

    for item in news_items:
        try:
            title_el = item.find_element(By.CSS_SELECTOR, 'h3.comp_1_item_header')
            link_el = item.find_element(By.TAG_NAME, 'a')
            title = title_el.text.strip()
            link = link_el.get_attribute('href')

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

        except:
            continue

    driver.quit()
    return news_list

# -------- Streamlit App --------
st.set_page_config(page_title="سكاي نيوز - استخراج آخر الأخبار", layout="centered")

st.title("📰 استخراج آخر الأخبار من Sky News Arabia")

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
