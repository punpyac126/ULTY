import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import datetime as dt

# --- Live weekly dividend fetcher with caching and fallbacks ---
@st.cache_data(ttl=60*60, show_spinner=False)
def fetch_latest_weekly_dividend_usd(ticker: str = "ULTY"):
    try:
        s = yf.Ticker(ticker).dividends
        if s is not None and len(s) > 0:
            last_amt = float(s.iloc[-1])
            if last_amt > 0:
                return last_amt, s.index[-1].to_pydatetime()
    except Exception:
        pass
    try:
        url = "https://yieldmaxetfs.com/ulty"
        tables = pd.read_html(url)
        for df in tables:
            cols = [str(c).lower() for c in df.columns]
            if any(k in ''.join(cols) for k in ["amount", "distribution", "dividend"]):
                for c in df.columns:
                    if any(k in str(c).lower() for k in ["amount", "distribution", "dividend"]):
                        series = (
                            df[c].astype(str)
                            .str.replace("$", "", regex=False)
                            .str.replace(",", "", regex=False)
                            .str.extract(r"([0-9]*\.?[0-9]+)")[0]
                            .astype(float)
                            .dropna()
                        )
                        if len(series) > 0:
                            return float(series.iloc[0]), None
    except Exception:
        pass
    try:
        hdr = {"User-Agent": "Mozilla/5.0"}
        url = f"https://api.nasdaq.com/api/quote/{ticker}/dividends?assetclass=etf"
        r = requests.get(url, headers=hdr, timeout=10)
        js = r.json()
        rows = js.get("data", {}).get("dividends", {}).get("rows", [])
        if rows:
            amt_str = rows[0].get("cashAmount") or rows[0].get("amount") or ""
            amt = float(str(amt_str).replace("$", "").replace(",", ""))
            if amt > 0:
                return amt, None
    except Exception:
        pass
    return None, None

import yfinance as yf
import requests
from streamlit_autorefresh import st_autorefresh
import json
import pandas as pd

# === โหลดปันผลล่าสุด ===
def load_latest_dividend():
    try:
        with open("latest_dividend.json", "r") as f:
            return json.load(f).get("dividend", 0.0)
    except:
        return 0.0

weekly_dividend_usd = load_latest_dividend()

st_autorefresh(interval=5 * 60 * 1000, key="datarefresh")

ULTY_TICKER = "ULTY"
DIVIDEND_PER_SHARE_WEEKLY_DEFAULT = 0.104  # fallback
live_div_amt, live_div_date = fetch_latest_weekly_dividend_usd("ULTY")
DIVIDEND_PER_SHARE_WEEKLY = live_div_amt if live_div_amt is not None else DIVIDEND_PER_SHARE_WEEKLY_DEFAULT

# === ราคาหุ้น & อัตราแลกเปลี่ยน ===
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

# === คำนวณ ===
def calculate_weekly_dividend(amount_thb, stock_price_usd, exchange_rate):
    usd = amount_thb / exchange_rate
    shares = usd / stock_price_usd
    dividend_usd = shares * DIVIDEND_PER_SHARE_WEEKLY
    return round(dividend_usd * exchange_rate, 2)

def calculate_required_investment(target_weekly_dividend_thb, stock_price_usd, exchange_rate):
    shares_needed = target_weekly_dividend_thb / (DIVIDEND_PER_SHARE_WEEKLY * exchange_rate)
    total_usd = shares_needed * stock_price_usd
    total_thb = total_usd * exchange_rate
    return round(shares_needed), round(total_thb, 2)

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
col1.metric("\U0001F4C9 ราคาหุ้น ULTY", f"{stock_price} USD" if stock_price else "-")
col2.metric("\U0001F4B1 อัตราแลกเปลี่ยน", f"{exchange_rate} THB/USD" if exchange_rate else "-")
col3.metric("\U0001F4B0 ปันผลล่าสุด/สัปดาห์", f"{DIVIDEND_PER_SHARE_WEEKLY} USD")

st.markdown("---")

mode = st.radio("เลือกโหมดคำนวณ", [
    "\U0001F4CD อยากได้ปันผลเท่าไหร่",
    "💼 คำนวณจากต้นทุน",
    "🔄 จำลองจุดคุ้มทุนแบบ Reinvest",
    "📈 จำลองผลตอบแทนแบบ Reinvest ระยะยาว (DRIP)"
], horizontal=True)

# === MODE 1: อยากได้ปันผลเท่าไหร่ ===
if mode == "\U0001F4CD อยากได้ปันผลเท่าไหร่":
    st.header("\U0001F4CC คำนวณจำนวนเงินที่ต้องลงทุน")
    div_mode = st.radio("เลือกรูปแบบการกรอกปันผลที่ต้องการ", ["\U0001F4B5 รายสัปดาห์", "📋 รายเดือน"], horizontal=True)

    if div_mode == "\U0001F4B5 รายสัปดาห์":
        weekly_input = st.text_input("\U0001F4B8 ปันผลที่ต้องการต่อสัปดาห์", value="5,000.00")
        weekly_div = parse_comma_input(weekly_input, default=5000.0)
    else:
        monthly_input = st.text_input("📆 ปันผลที่ต้องการต่อเดือน", value="20,000.00")
        monthly_div = parse_comma_input(monthly_input, default=20000.0)
        weekly_div = monthly_div / 4

    if stock_price and exchange_rate:
        shares_needed, total_investment = calculate_required_investment(weekly_div / 0.85, stock_price, exchange_rate)
        st.subheader("\U0001F4C9 ผลลัพธ์")
        st.markdown(f"- จำนวนหุ้นที่ต้องซื้อ: **{shares_needed:,} หุ้น**")
        st.markdown(f"- เงินลงทุนรวม: **{total_investment:,.2f} บาท**")
        st.markdown(f"- ปันผลก่อนหักภาษี: **{weekly_div / 0.85:,.2f} บาท/สัปดาห์**")
        st.markdown(f"- ปันผลหลังหักภาษี: **{weekly_div:,.2f} บาท/สัปดาห์**")
        st.markdown(f"- ปันผลต่อเดือน (หลังภาษี): **{weekly_div * 4:,.2f} บาท**")
    else:
        st.error("ไม่สามารถดึงข้อมูลราคา/อัตราแลกเปลี่ยนได้ กรุณาตรวจสอบการเชื่อมต่อ")

# === MODE 2: คำนวณจากต้นทุน ===
elif mode == "💼 คำนวณจากต้นทุน":
    st.header("📌 คำนวณจำนวนปันผลที่ได้รับ")
    investment_input = st.text_input("จำนวนเงินที่ลงทุน (THB)", value="1,000.00")
    investment = parse_comma_input(investment_input, default=1000.0)

    if stock_price and exchange_rate:
        weekly = calculate_weekly_dividend(investment, stock_price, exchange_rate)
        tax_amount = weekly * 0.15
        weekly_after_tax = weekly * 0.85
        st.success(f"✅ ปันผลรายสัปดาห์ (ก่อนหักภาษี) ≈ {weekly:,.2f} บาท")
        st.success(f"✅ ปันผลรายสัปดาห์ (หลังหักภาษี 15%) ≈ {weekly_after_tax:,.2f} บาท")
        st.info(f"📅 ปันผลรายเดือน ≈ {weekly_after_tax * 4:,.2f} บาท")
        st.warning(f"📆 ปันผลรายปี ≈ {weekly_after_tax * 52:,.2f} บาท")
        st.error(f"🔻 จำนวนเงินที่ถูกหักภาษี (บาท): {tax_amount:,.2f}")
    else:
        st.error("ไม่สามารถดึงข้อมูลราคา/อัตราแลกเปลี่ยนได้ กรุณาตรวจสอบการเชื่อมต่อ")

# === MODE 3: จำลอง Reinvest สั้น ===
elif mode == "🔄 จำลองจุดคุ้มทุนแบบ Reinvest":
    st.header("🔁 จำลองการคืนทุนโดย Reinvest ปันผลทุกสัปดาห์")
    investment_input = st.text_input("💵 เงินลงทุนเริ่มต้น (บาท)", value="100,000.00")
    investment = parse_comma_input(investment_input, default=100000.0)

    reinvest_stock_price = 6.40
    reinvest_dividend_usd = 0.0875

    if exchange_rate:
        shares = (investment / exchange_rate) / reinvest_stock_price
        total_received_thb = 0
        weeks = 0

        while total_received_thb < investment and weeks < 1000:
            dividend_thb = shares * reinvest_dividend_usd * exchange_rate * 0.85
            total_received_thb += dividend_thb
            shares += (dividend_thb / exchange_rate) / reinvest_stock_price
            weeks += 1

        years = weeks // 52
        months = (weeks % 52) // 4
        days = (weeks % 52) % 4 * 7

        st.success(f"📆 คาดว่าจะคืนทุนได้ใน {weeks:,} สัปดาห์ ≈ **{years} ปี {months} เดือน {days} วัน**")
        st.info(f"📈 ปันผลรวมสะสม: **{total_received_thb:,.2f} บาท**")
    else:
        st.error("ไม่สามารถดึงอัตราแลกเปลี่ยนได้")


# === MODE 4: จำลองระยะยาวแบบ DRIP ===
elif mode == "📈 จำลองผลตอบแทนแบบ Reinvest ระยะยาว (DRIP)":
    st.header("📈 จำลองผลตอบแทนแบบ Reinvest ระยะยาว (DRIP)")

    # Latest dividend + last updated
    try:
        div_amt_display = float(DIVIDEND_PER_SHARE_WEEKLY)
        st.metric(label="💰 Latest Dividend (USD per period)", value=f"{div_amt_display:.3f} USD")
        if live_div_date is not None:
            ts = live_div_date.strftime("%Y-%m-%d")
        else:
            ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        st.caption(f"Last updated at: {ts}")
    except Exception:
        st.metric(label="💰 Latest Dividend (USD per period)", value="N/A")
        st.caption("Last updated at: --")

    # --- UI ---
    currency = st.radio("💱 เลือกสกุลเงิน", ["THB", "USD"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        init_invest_input = st.text_input("💰 Initial Investment", value="100,000.00" if currency == "THB" else "3,000.00")
        share_price_input = st.number_input("🏷️ Share Price ($)", value=float(stock_price) if stock_price else 0.0, min_value=0.0)
        use_live_div = st.checkbox("Use live latest dividend", value=True)
        colA, colB = st.columns([2,1])
        with colA:
            dividend_amount_input = st.number_input("💵 Dividend Amount ($ per period)", value=float(DIVIDEND_PER_SHARE_WEEKLY), min_value=0.0, disabled=use_live_div)
        with colB:
            if st.button("Refresh live"):
                fetch_latest_weekly_dividend_usd.clear()
                st.rerun()
        dividend_freq = st.selectbox("🗓️ Dividend Frequency", ["Weekly", "Monthly", "Quarterly"], index=0)
    with col2:
        years_input = st.number_input("⏳ Length of Investment (years)", min_value=1, max_value=50, value=10)
        dividend_growth_input = st.number_input("📈 Dividend Growth Rate (%/yr, step-yearly)", value=0.0)
        extra_invest = st.number_input("➕ Extra Investment", value=0.0)
        extra_invest_freq = st.selectbox("🗓️ Extra Invest Frequency", ["Weekly", "Monthly"], index=0)
    share_price_growth_input = st.number_input("🏷️ Share Price Growth (%/yr, comp-weekly)", value=0.0)

    # Reality guardrails toggle
    guardrails_on = st.checkbox("🛡️ Enable Reality guardrails", value=True)
    if guardrails_on:
        with st.expander("Reality guardrails (advanced)"):
            price_floor_usd = st.number_input("Price floor (USD)", value=0.50, min_value=0.0, step=0.01)
            cut_threshold_usd = st.number_input("Dividend cut when price < (USD)", value=1.00, min_value=0.0, step=0.01)
            cut_percent = st.number_input("Cut percentage (%)", value=50.0, min_value=0.0, max_value=100.0, step=1.0)
            max_shares_growth_y = st.number_input("Cap shares growth per year (%) (0=off)", value=300.0, min_value=0.0, step=10.0)
    else:
        price_floor_usd = None
        cut_threshold_usd = None
        cut_percent = 0.0
        max_shares_growth_y = 0.0

    if not stock_price or not exchange_rate:
        st.error("❌ ไม่สามารถดึงข้อมูลราคาหุ้นหรืออัตราแลกเปลี่ยน")
    else:
        # --- Parse inputs & set context ---
        init_invest = parse_comma_input(init_invest_input)
        total_weeks = int(years_input * 52)

        is_thb = currency == "THB"
        exch = exchange_rate if is_thb else 1.0
        label_currency = "฿" if is_thb else "$"

        price0 = float(share_price_input) if share_price_input and share_price_input > 0 else float(stock_price)
        g_div = dividend_growth_input / 100.0       # per year (step yearly)
        g_px  = share_price_growth_input / 100.0    # per year (comp weekly)

        # Frequency mappings (weekly sim)
        freq_to_weeks = {"Weekly": 1, "Monthly": 4, "Quarterly": 13}
        div_interval = freq_to_weeks.get(dividend_freq, 1)
        extra_interval = 1 if extra_invest_freq == "Weekly" else 4

        base_div_per_period_usd_y0 = float(DIVIDEND_PER_SHARE_WEEKLY) if use_live_div else float(dividend_amount_input)

        # --- Initial state ---
        shares = (init_invest / exch) / price0
        total_div_cum = 0.0
        div_this_year = 0.0
        total_contrib = init_invest
        records = []
        shares_year_start = shares

        # --- Simulation (weekly) ---
        for week in range(1, total_weeks + 1):
            year_idx = (week - 1) // 52  # 0-based year index

            # Price evolves weekly (compounding weekly based on annual rate)
            px = price0 * ((1 + g_px) ** (week / 52.0))

            # Apply price floor if guardrails are on
            if guardrails_on and price_floor_usd is not None and px < price_floor_usd:
                px = price_floor_usd

            # Dividend per period (USD) grows step-yearly
            div_per_period_usd = base_div_per_period_usd_y0 * ((1 + g_div) ** year_idx)
            # Apply dividend cut if price below threshold
            if guardrails_on and cut_threshold_usd is not None and px < cut_threshold_usd:
                div_per_period_usd *= (1 - (cut_percent / 100.0))

            # Pay dividend only on specified frequency weeks
            if week % div_interval == 0 and div_per_period_usd > 0:
                div_net_ccy = shares * div_per_period_usd * exch * 0.85
            else:
                div_net_ccy = 0.0

            # Receive dividend and DRIP
            weekly_div_net_ccy = div_net_ccy
            total_div_cum += weekly_div_net_ccy
            div_this_year += weekly_div_net_ccy
            shares += (weekly_div_net_ccy / exch) / px

            # Extra invest based on frequency
            if extra_invest and extra_invest != 0.0 and (week % extra_interval == 0):
                total_contrib += extra_invest
                shares += (extra_invest / exch) / px

            # Close year (every 52 weeks): record end-of-year snapshot
            if week % 52 == 0:
                # Cap shares growth per year if enabled
                if guardrails_on and max_shares_growth_y and max_shares_growth_y > 0:
                    cap_multiplier = 1.0 + (max_shares_growth_y / 100.0)
                    max_allowed_shares = shares_year_start * cap_multiplier
                    if shares > max_allowed_shares:
                        shares = max_allowed_shares

                end_balance = shares * px * exch

                # Next 12M run-rate uses dividend rate of the next year & correct number of periods
                next_year_div_runrate = shares * (base_div_per_period_usd_y0 * ((1 + g_div) ** (year_idx + 1))) * int(52/div_interval) * exch * 0.85

                record = {
                    "Year": year_idx + 1,
                    "End-of-Year Balance": round(end_balance, 2),
                    "Shares (end)": round(shares, 6),
                    "Price (end)": round(px, 4),
                    "Dividends Received (this year)": round(div_this_year, 2),
                    "Total Dividends (cum)": round(total_div_cum, 2),
                    "Next 12M Run-rate": round(next_year_div_runrate, 2),
                    "YoC (initial)": round((next_year_div_runrate / init_invest) * 100, 2) if init_invest > 0 else 0.0,
                    "YoC (contrib)": round((next_year_div_runrate / total_contrib) * 100, 2) if total_contrib > 0 else 0.0,
                }
                records.append(record)
                # reset yearly trackers
                div_this_year = 0.0
                shares_year_start = shares

        df = pd.DataFrame(records)

        # --- Table ---
        st.subheader("📋 Annual Results")
        st.dataframe(df.style.format({
            "End-of-Year Balance": f"{label_currency}" + "{:,.2f}",
            "Dividends Received (this year)": f"{label_currency}" + "{:,.2f}",
            "Total Dividends (cum)": f"{label_currency}" + "{:,.2f}",
            "Next 12M Run-rate": f"{label_currency}" + "{:,.2f}",
            "Price (end)": "${:,.4f}",
            "Shares (end)": "{:,.6f}",
            "YoC (initial)": "{:,.2f}%",
            "YoC (contrib)": "{:,.2f}%",
        }))

        # --- Chart --- (single plot, default colors)
        st.subheader("📊 Portfolio Chart (End of Year)")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5))
        x = df["Year"].astype(str)
        ax.bar(x, df["End-of-Year Balance"], label="Portfolio Value (End of Year)")
        ax.bar(x, df["Total Dividends (cum)"], label="Cumulative Dividends", alpha=0.5)
        ax.plot(x, df["Next 12M Run-rate"], label="Next 12M Dividend Run-rate", linewidth=2, marker="o")
        ax.set_ylabel(f"Value ({label_currency})")
        ax.set_xlabel("Year")
        ax.set_title("Portfolio Growth with DRIP")
        ax.legend()
        st.pyplot(fig)
