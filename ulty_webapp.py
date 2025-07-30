import streamlit as st
import yfinance as yf
import requests
from streamlit_autorefresh import st_autorefresh
import json

def load_latest_dividend():
    try:
        with open("latest_dividend.json", "r") as f:
            return json.load(f).get("dividend", 0.0)
    except:
        return 0.0

weekly_dividend_usd = load_latest_dividend()

st_autorefresh(interval=5 * 60 * 1000, key="datarefresh")

ULTY_TICKER = "ULTY"
DIVIDEND_PER_SHARE_WEEKLY = 0.104

def get_stock_price():
    ticker = yf.Ticker(ULTY_TICKER)
    hist = ticker.history(period="1d")
    if not hist.empty:
        return round(hist["Close"].iloc[-1], 2)
    return None

def get_exchange_rate():
    try:
        res = requests.get("https://api.frankfurter.app/latest?from=USD&to=THB")
        data = res.json()
        return round(data["rates"]["THB"], 2)
    except:
        return None

def calculate_weekly_dividend(amount_thb, stock_price_usd, exchange_rate):
    usd = amount_thb / exchange_rate
    shares = usd / stock_price_usd
    dividend_usd = shares * DIVIDEND_PER_SHARE_WEEKLY
    return round(dividend_usd * exchange_rate, 2)

def calculate_required_investment(target_weekly_dividend_thb_net, stock_price_usd, exchange_rate):
    gross_weekly = target_weekly_dividend_thb_net / 0.85  # ✨ gross-up from net
    shares_needed = gross_weekly / (DIVIDEND_PER_SHARE_WEEKLY * exchange_rate)
    total_usd = shares_needed * stock_price_usd
    total_thb = total_usd * exchange_rate
    return round(shares_needed), round(total_thb, 2), round(gross_weekly * 4, 2)

def parse_comma_input(text, default=0.0):
    try:
        return float(text.replace(",", ""))
    except:
        return default

stock_price = get_stock_price()
exchange_rate = get_exchange_rate()

col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.image("yieldmax_logo.png", width=80)
with col_title:
    st.title(" Yieldmax ULTY Calculator (Real-time)")
st.markdown("อัปเดตราคาหุ้น อัตราแลกเปลี่ยน และปันผลรายสัปดาห์ พร้อมคำนวณเงินลงทุนแบบเรียลไทม์")

col1, col2, col3 = st.columns(3)
col1.metric("📉 ราคาหุ้น ULTY", f"{stock_price} USD" if stock_price else "-")
col2.metric("💱 อัตราแลกเปลี่ยน", f"{exchange_rate} THB/USD" if exchange_rate else "-")
col3.metric("💰 ปันผลล่าสุด/สัปดาห์", f"{DIVIDEND_PER_SHARE_WEEKLY} USD")

st.markdown("---")

mode = st.radio("เลือกโหมดคำนวณ", ["📍 อยากได้ปันผลเท่าไหร่", "💼 คำนวณจากต้นทุน", "🔄 จำลองจุดคุ้มทุนแบบ Reinvest"], horizontal=True)

if mode == "📍 อยากได้ปันผลเท่าไหร่":
    st.header("📌 คำนวณจำนวนเงินที่ต้องลงทุน")
    currency = st.selectbox("สกุลเงิน", ["THB", "USD"], index=0)

    div_mode = st.radio("เลือกรูปแบบการกรอกปันผลที่ต้องการ", ["🪙 รายสัปดาห์", "🗓️ รายเดือน"], horizontal=True)

    if div_mode == "🪙 รายสัปดาห์":
        weekly_input = st.text_input("💸 ปันผลที่ต้องการต่อสัปดาห์ (หลังหักภาษี 15%)", value="5,000.00")
        weekly_div_net = parse_comma_input(weekly_input, default=5000.0)
        monthly_div_net = weekly_div_net * 4
    else:
        monthly_input = st.text_input("📆 ปันผลที่ต้องการต่อเดือน (หลังหักภาษี 15%)", value="20,000.00")
        monthly_div_net = parse_comma_input(monthly_input, default=20000.0)
        weekly_div_net = monthly_div_net / 4

    if stock_price and exchange_rate:
        gross_weekly = weekly_div_net / 0.85  # ✨ gross-up
        gross_monthly = gross_weekly * 4
        shares_needed = gross_weekly / (DIVIDEND_PER_SHARE_WEEKLY * exchange_rate)
        total_usd = shares_needed * stock_price
        total_thb = total_usd * exchange_rate

        st.subheader("📊 ผลลัพธ์")
        st.markdown(f"- จำนวนหุ้นที่ต้องซื้อ: **{round(shares_needed):,} หุ้น**")
        st.markdown(f"- เงินลงทุนรวม: **{total_thb:,.2f} บาท**")

        st.markdown("#### 💵 รายได้ปันผล (คาดการณ์)")
        st.markdown(f"- **ก่อนหักภาษี 15%**: {gross_monthly:,.2f} บาท / เดือน")
        st.markdown(f"- **หลังหักภาษี 15%**: {monthly_div_net:,.2f} บาท / เดือน")
        st.caption(f"ระบบคำนวณโดย gross-up ยอดปันผลที่คุณต้องการ เพื่อหายอดเงินลงทุนที่เหมาะสม")
    else:
        st.error("ไม่สามารถดึงข้อมูลราคา/อัตราแลกเปลี่ยนได้ กรุณาตรวจสอบการเชื่อมต่อ")
