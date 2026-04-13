#!/usr/bin/env python
# coding: utf-8

# In[2]:


import re
import time
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URL = "https://ioirankings.com/ioi-2020/"
OUTPUT_CSV = "ioi2020_rankings_extracted.csv"


def clean_text(x):
    if x is None:
        return None
    x = re.sub(r"\s+", " ", x).strip()
    return x if x else None


def extract_numeric_id(text_or_href):
    """
    Tries to pull a user ID from text/href/attribute.
    Adjust if you discover the site uses a specific pattern.
    """
    if not text_or_href:
        return None

    # common patterns like /user/123 or user_id=123 or #123
    patterns = [
        r"/user/(\d+)",
        r"user[_-]?id=(\d+)",
        r"\bID[:# ]+(\d+)\b",
        r"^(\d+)$",
    ]
    for pat in patterns:
        m = re.search(pat, text_or_href, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def get_medal_from_row(row):
    """
    Tries multiple ways to detect medal from a row.
    Keeps it flexible because site structure may differ after rendering.
    """
    row_text = clean_text(row.get_text(" ", strip=True)) or ""
    text_lower = row_text.lower()

    # direct text in row
    if "gold" in text_lower:
        return "Gold"
    if "silver" in text_lower:
        return "Silver"
    if "bronze" in text_lower:
        return "Bronze"
    if "honourable mention" in text_lower or "honorable mention" in text_lower:
        return "Honourable Mention"

    # attributes / classes / titles
    medal_candidates = []
    for el in row.find_all(True):
        for attr in ["title", "aria-label", "alt", "class"]:
            val = el.get(attr)
            if not val:
                continue
            if isinstance(val, list):
                val = " ".join(val)
            medal_candidates.append(str(val))

    joined = " ".join(medal_candidates).lower()
    if "gold" in joined:
        return "Gold"
    if "silver" in joined:
        return "Silver"
    if "bronze" in joined:
        return "Bronze"
    if "honourable mention" in joined or "honorable mention" in joined:
        return "Honourable Mention"

    return None


def parse_rendered_table(html):
    soup = BeautifulSoup(html, "html.parser")

    # Try several common table selectors
    table = (
        soup.select_one("table") or
        soup.select_one(".table") or
        soup.select_one('[role="table"]')
    )
    if table is None:
        raise RuntimeError("Could not find a rendered rankings table on the page.")

    # headers
    headers = []
    thead = table.find("thead")
    if thead:
        headers = [clean_text(th.get_text(" ", strip=True)) for th in thead.find_all(["th", "td"])]
    else:
        first_row = table.find("tr")
        if first_row:
            headers = [clean_text(x.get_text(" ", strip=True)) for x in first_row.find_all(["th", "td"])]

    headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]

    rows = table.find_all("tr")
    data_rows = []

    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue

        values = [clean_text(td.get_text(" ", strip=True)) for td in cells]

        # pad / trim to header count
        if len(values) < len(headers):
            values += [None] * (len(headers) - len(values))
        elif len(values) > len(headers):
            # keep all columns if site has more cells than detected headers
            extra_headers = [f"extra_col_{i}" for i in range(len(values) - len(headers))]
            headers_extended = headers + extra_headers
        else:
            headers_extended = headers

        if len(values) != len(headers):
            record = dict(zip(headers_extended, values))
        else:
            record = dict(zip(headers, values))

        # try to capture link-based ID
        user_id = None
        links = row.find_all("a", href=True)
        for a in links:
            href = a["href"]
            user_id = extract_numeric_id(href)
            if user_id:
                break

        # fallback: any row attrs
        if not user_id:
            attrs_to_try = []
            for attr_name, attr_val in row.attrs.items():
                if isinstance(attr_val, list):
                    attr_val = " ".join(attr_val)
                attrs_to_try.append(f"{attr_name}={attr_val}")
            user_id = extract_numeric_id(" ".join(attrs_to_try))

        # fallback: first cell text
        if not user_id and values:
            user_id = extract_numeric_id(values[0] or "")

        record["extracted_user_id"] = user_id
        record["extracted_medal"] = get_medal_from_row(row)

        data_rows.append(record)

    df = pd.DataFrame(data_rows)
    return df


# ---------- browser setup ----------
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,3000")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)

try:
    driver.get(URL)


    WebDriverWait(driver, 30).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tr")) > 5
                  or len(d.find_elements(By.CSS_SELECTOR, "[role='row']")) > 5
    )

    time.sleep(3)  # extra buffer for JS rendering

    html = driver.page_source
    df = parse_rendered_table(html)

finally:
    driver.quit()


# ---------- post-processing ----------
rename_map = {
    "User": "user",
    "Username": "user",
    "Contestant": "user",
    "Name": "user",
    "ID": "user_id",
    "Rank": "rank",
    "Score": "total_score",
    "Total": "total_score",
    "Day 1": "day1_total",
    "Day 2": "day2_total",
    "Medal": "medal",
}

df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

if "medal" not in df.columns:
    df["medal"] = df["extracted_medal"]
else:
    df["medal"] = df["medal"].fillna(df["extracted_medal"])

if "user_id" not in df.columns:
    df["user_id"] = df["extracted_user_id"]
else:
    df["user_id"] = df["user_id"].fillna(df["extracted_user_id"])

# Save raw extracted table
df.to_csv(OUTPUT_CSV, index=False)

print("Saved:", OUTPUT_CSV)
print("\nColumns found:")
print(df.columns.tolist())
print("\nPreview:")
print(df.head(10).to_string(index=False))


# In[14]:


df2 = df.copy()

# make one full user column
df2["user"] = (
    df2["First Name"].fillna("").astype(str).str.strip()
    + " "
    + df2["Last Name"].fillna("").astype(str).str.strip()
).str.strip()

final_df = df2[
    [
        "user_id",
        "user",
        "Team",
        "rank",
        "plants",
        "supertrees",
        "tickets",
        "day1_total",
        "biscuits",
        "mushrooms",
        "stations",
        "day2_total",
        "medal",
    ]
].copy()

final_df.to_csv("ioi2020_user_scores_medals_clean.csv", index=False)
print(final_df.head(20).to_string(index=False))


# In[10]:





# In[6]:


print(df.columns.tolist())


# In[16]:


medals_df = df2[["user_id", "medal"]].copy()

medals_df.to_csv("ioi2020_user_medals.csv", index=False)
print(medals_df.head(20).to_string(index=False))


# In[ ]:




