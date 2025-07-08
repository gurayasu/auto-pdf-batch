import os
import time
import datetime
import base64
import pytz

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger

import requests

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth import default

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# ==== 環境変数・定数 ====
CHROME_PATH = os.environ.get('CHROME_PATH', '/usr/bin/chromium')
CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
DOWNLOAD_DIR = './pdf_output'
CLOUD_FOLDER_ID = os.environ.get('CLOUD_FOLDER_ID')
USER_ID = os.environ.get('SERVICE_USER_ID')
PASSWORD = os.environ.get('SERVICE_PASSWORD')
CHAT_BOT_TOKEN = os.environ.get('CHAT_BOT_TOKEN')
CHAT_CHANNEL_ID = os.environ.get('CHAT_CHANNEL_ID')
BASE_URL = "https://example.com"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_today_str():
    timezone = pytz.timezone('Asia/Somewhere')
    now = datetime.datetime.now(timezone)
    return now.strftime('%Y-%m-%d')

def login_and_get_driver():
    options = Options()
    options.binary_location = CHROME_PATH
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)
    wait = WebDriverWait(driver, 30)
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.presence_of_element_located((By.ID, "user_code"))).send_keys(USER_ID)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(text(),'ログイン')]").click()
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'はい')]"))
        ).click()
    except:
        pass
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
    return driver

def get_cookies_dict(driver):
    return {c['name']: c['value'] for c in driver.get_cookies()}

def to_full_url(url):
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("/"):
        return BASE_URL + url
    return BASE_URL + "/" + url

def fetch_articles_api(cookies_dict, today_str, max_page=10):
    all_articles = []
    headers = {"User-Agent": "Mozilla/5.0", "Referer": BASE_URL + "/"}
    for page in range(1, max_page + 1):
        params = {
            "page": str(page),
            "limit": "100",
            "date": today_str,
            # 必要に応じて追加パラメータ
        }
        res = requests.get(f"{BASE_URL}/api/article_list",
                           params=params, cookies=cookies_dict, headers=headers)
        if res.status_code != 200:
            break
        data = res.json()
        items = data.get("articles", [])
        if not items:
            break
        all_articles.extend(items)
        time.sleep(0.8)
    return all_articles

def sanitize_filename(text):
    for c in r'\/:*?"<>|':
        text = text.replace(c, '_')
    return text.strip()[:150]

def save_pdf_by_cdp(driver, filename):
    data = driver.execute_cdp_cmd("Page.printToPDF", {
        "printBackground": True, "paperWidth": 8.27, "paperHeight": 11.69
    })
    pdf_bytes = base64.b64decode(data['data'])
    path = os.path.join(DOWNLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path

def upload_pdf_to_cloud(service, pdf_path, filename, folder_id):
    media = MediaFileUpload(pdf_path, mimetype="application/pdf")
    file = service.files().create(
        body={"name": filename, "parents": [folder_id]},
        media_body=media,
        fields="id, webViewLink"
    ).execute()
    service.permissions().create(
        fileId=file["id"], body={"type": "anyone", "role": "reader"}
    ).execute()
    return file["id"], file["webViewLink"]

def send_pdf_to_chat(token, channel, pdf_path, comment=""):
    client = WebClient(token=token)
    try:
        resp = client.files_upload_v2(
            channel=channel,
            file=pdf_path,
            title=os.path.basename(pdf_path),
            initial_comment=comment
        )
        print("チャットツールにPDF送信完了:", resp["file"]["id"])
    except SlackApiError as e:
        print("チャットアップロード失敗:", e.response["error"])

def main():
    today = get_today_str()  # 'YYYY-MM-DD'
    pdf_filename = f"ニュースまとめ_{today.replace('-', '')}.pdf"  # 'ニュースまとめ_YYYYMMDD.pdf'

    driver = login_and_get_driver()
    cookies = get_cookies_dict(driver)
    articles = fetch_articles_api(cookies, today)

    pdf_pages = []
    for idx, item in enumerate(articles):
        title = item.get("title", f"untitled_{idx+1}")
        # 例: 特定キーワード含むタイトルは除外
        if "除外キーワード" in title:
            continue
        raw_url = item["url"]
        full_url = to_full_url(raw_url)
        if not full_url:
            continue
        driver.get(full_url)
        time.sleep(2)
        filename = sanitize_filename(title) + ".pdf"
        pdf_pages.append(save_pdf_by_cdp(driver, filename))

    driver.quit()

    if not pdf_pages:
        print("対象の記事がありません")
        return

    merger = PdfMerger()
    for p in pdf_pages:
        merger.append(p)
    merged_path = os.path.join(DOWNLOAD_DIR, pdf_filename)
    merger.write(merged_path)
    merger.close()

    cloud_service = build(
        "drive", "v3",
        credentials=default(scopes=["https://www.googleapis.com/auth/drive.file"])[0]
    )
    _, web_url = upload_pdf_to_cloud(cloud_service, merged_path, pdf_filename, CLOUD_FOLDER_ID)

    send_pdf_to_chat(
        CHAT_BOT_TOKEN,
        CHAT_CHANNEL_ID,
        merged_path,
        f"{pdf_filename} をアップロードしました！\n<{web_url}|クラウドストレージで見る>"
    )

if __name__ == "__main__":
    main()
