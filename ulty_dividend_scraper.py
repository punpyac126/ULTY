import requests
from bs4 import BeautifulSoup
import datetime
import json

def get_latest_ulty_dividend():
    url = "https://stockanalysis.com/etf/ulty/dividend/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.find("table")
    rows = table.find_all("tr")[1:]  # Skip header
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            ex_div_date = cols[0].text.strip()
            payment_date = cols[1].text.strip()
            dividend = cols[2].text.strip().replace("$", "")

            try:
                # Convert to datetime object
                pay_date = datetime.datetime.strptime(payment_date, "%b %d, %Y").date()
                if (datetime.date.today() - pay_date).days <= 14:  # ตรวจสอบว่าข้อมูลใหม่
                    return float(dividend)
            except Exception as e:
                continue
    return None

def save_to_json(dividend):
    with open("latest_dividend.json", "w") as f:
        json.dump({"dividend": dividend, "timestamp": str(datetime.datetime.now())}, f)

if __name__ == "__main__":
    latest = get_latest_ulty_dividend()
    if latest:
        save_to_json(latest)
        print(f"✅ Updated latest dividend: {latest} USD")
    else:
        print("⚠️ Could not fetch dividend.")

