
import streamlit as st
import math
import yfinance as yf
import requests

st.set_page_config(page_title="ULTY Dividend Calculator", page_icon="💰")

st.title("💸 Yieldmax ULTY Dividend Calculator")
st.caption("แบบเรียลไทม์ พร้อมคำนวณจากราคาหุ้นและค่าเงินล่าสุด")

# ดึงราคาหุ้น
def get_ulty_price():
    try:
        ulty = yf.Ticker("ULTY")
        return ulty.info["regularMarketPrice"]
    except:
        return None

# ดึงอัตราแลกเปลี่ยน USD → THB
def get_usd_to_thb():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD")
        data = res.json()
        return data["rates"]["THB"]
    except:
        return None

ulty_price = get_ulty_price()
usd_to_thb = get_usd_to_thb()
dividend_per_share = 0.0875  # ปันผลรายสัปดาห์ต่อหุ้น (USD)

if ulty_price and usd_to_thb:
    st.success(f"📈 ราคาหุ้น ULTY ปัจจุบัน: {ulty_price:.2f} USD\n💱 อัตราแลกเปลี่ยน: {usd_to_thb:.2f} THB/USD")
else:
    st.warning("⚠️ ไม่สามารถดึงข้อมูลเรียลไทม์ได้")
    ulty_price = st.number_input("กรุณาใส่ราคาหุ้น ULTY (USD):", min_value=1.0, value=6.5)
    usd_to_thb = st.number_input("กรุณาใส่อัตราแลกเปลี่ยน USD → THB:", min_value=25.0, value=36.0)

mode = st.radio("เลือกโหมดคำนวณ", ["🎯 อยากได้ปันผลเท่าไหร่", "💼 มีเงินเท่านี้ ลงทุนได้กี่หุ้น"])

if mode == "🎯 อยากได้ปันผลเท่าไหร่":
    col1, col2 = st.columns([2, 1])
    with col1:
        amount = st.number_input("ปันผลที่ต้องการต่อสัปดาห์", min_value=0.0, value=5000.0)
    with col2:
        currency = st.selectbox("สกุลเงิน", ["THB", "USD"])

    if currency == "THB":
        amount_usd = amount / usd_to_thb
    else:
        amount_usd = amount

    shares_needed = math.ceil(amount_usd / dividend_per_share)
    total_cost_usd = shares_needed * ulty_price
    total_cost_thb = total_cost_usd * usd_to_thb
    monthly_dividend_thb = shares_needed * dividend_per_share * 4 * usd_to_thb

    st.subheader("📊 ผลลัพธ์")
    st.markdown(f"- จำนวนหุ้นที่ต้องซื้อ: **{shares_needed:,} หุ้น**")
    st.markdown(f"- เงินลงทุนรวม: **{total_cost_thb:,.2f} บาท**")
    st.markdown(f"- คาดว่าจะได้ปันผลต่อเดือน: **{monthly_dividend_thb:,.2f} บาท**")

elif mode == "💼 มีเงินเท่านี้ ลงทุนได้กี่หุ้น":
    capital_thb = st.number_input("เงินต้นทุนที่มี (บาท)", min_value=0.0, value=100000.0)
    capital_usd = capital_thb / usd_to_thb
    shares = math.floor(capital_usd / ulty_price)
    actual_cost_thb = shares * ulty_price * usd_to_thb
    monthly_dividend = shares * dividend_per_share * 4 * usd_to_thb

    st.subheader("📊 ผลลัพธ์")
    st.markdown(f"- ซื้อได้: **{shares:,} หุ้น**")
    st.markdown(f"- ปันผลต่อเดือนโดยประมาณ: **{monthly_dividend:,.2f} บาท**")
    st.markdown(f"- ใช้ทุนจริงประมาณ: **{actual_cost_thb:,.2f} บาท**")
