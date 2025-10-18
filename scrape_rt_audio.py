from seleniumbase import SB
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd
import telegram
from utils.telegram_utils import send_order_book_summary_message, \
    send_all_orderbook_messages
import asyncio
from utils.scraping_utils import fetch_sb_rt_data, \
    process_and_filter_rt_data, get_individual_stock
from dotenv import load_dotenv
import os
from pydrive2.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from utils.gsheet_utils import export_to_sheets
from datetime import datetime as dt
import pytz
import mycdp
from twocaptcha import TwoCaptcha
from utils.captcha_utils_debug import PageActions, CaptchaHelper
import imaplib
import email
from email.header import decode_header
import cloudscraper
import time
# import ast
# import colorama
from selenium_recaptcha_solver import RecaptchaSolver

load_dotenv(override=True)

user = os.environ['PROXY_USER']
password = os.environ['PROXY_PASSWORD']
proxy_host = os.environ['PROXY_HOST']
proxy_port = os.environ['PROXY_PORT']

proxy_string = f"{user}:{password}@{proxy_host}:{proxy_port}"

website = os.environ['WEBSITE']
site_email = os.environ['SITE_EMAIL']
site_password = os.environ['SITE_PASSWORD']
stock_website = os.environ['STOCK_WEBSITE']

sb_website = os.environ['SB_WEBSITE']
sb_user = os.environ['SB_USER']
sb_pass = os.environ['SB_PASSWORD']

raw_today_data = dt.now(pytz.timezone('Asia/Jakarta'))
today_date = raw_today_data.strftime("%Y-%m-%d")
# today_date = '2025-05-09'
today_month_year = raw_today_data.strftime("%b %Y")
today_date

captured_requests = []
# c1 = colorama.Fore.BLUE + colorama.Back.LIGHTYELLOW_EX
# c2 = colorama.Fore.BLUE + colorama.Back.LIGHTGREEN_EX
# cr = colorama.Style.RESET_ALL


async def send_handler(event: mycdp.network.RequestWillBeSent):
    r = event.request
    s = f"{r.method} {r.url}"
    for k, v in r.headers.items():
        s += f"\n\t{k} : {v}"

    request_data = {
        "url": r.url,
        "method": r.method,
        "headers": dict(r.headers),
    }
    captured_requests.append(request_data)
    # print(c1 + "*** ==> RequestWillBeSent <== ***" + cr)
    # print(s)


async def receive_handler(event: mycdp.network.ResponseReceived):
    # print(c2 + "*** ==> ResponseReceived <== ***" + cr)
    print(event.response)


xhr_requests = []
last_xhr_request = None


def listenXHR(page):
    async def handler(evt):
        # Get AJAX requests
        if evt.type_ is mycdp.network.ResourceType.XHR:
            xhr_requests.append([evt.response.url, evt.request_id])
            global last_xhr_request
            last_xhr_request = time.time()
    page.add_handler(mycdp.network.ResponseReceived, handler)


async def receiveXHR(page, requests):
    responses = []
    retries = 0
    max_retries = 5
    # Wait at least 2 seconds after last XHR request for more
    while True:
        if last_xhr_request is None or retries > max_retries:
            break
        if time.time() - last_xhr_request <= 2:
            retries = retries + 1
            time.sleep(2)
            continue
        else:
            break
    await page
    # Loop through gathered requests and get response body
    for request in requests:
        try:
            res = await page.send(mycdp.network.get_response_body(request[1]))
            if res is None:
                continue
            responses.append({
                "url": request[0],
                "body": res[0],
                "is_base64": res[1],
            })
        except Exception as e:
            print("Error getting response:", e)
    return responses


with SB(uc=True,
        headless=False,
        xvfb=False,
        proxy=proxy_string,
        maximize=True,
        is_mobile=True,
        # locale="id"
        ) as sb:

    # sb.activate_cdp_mode(f"{sb_website}/login")
    sb.uc_open_with_reconnect("https://google.com")
    sb.sleep(3)
    # breakpoint()
    sb.uc_open_with_reconnect(f"{sb_website}/login", 5)
    # sb.open("https://www.google.com/search?q=stockbit")
    sb.sleep(3)

    # sb.open(f"{sb_website}/login")
    # sb.execute_cdp_cmd(
    #         'Target.setAutoAttach',
    #         {'autoAttach': True, 'waitForDebuggerOnStart': False,
    #          'flatten': True}
    #     )
    # sb.execute_cdp_cmd('Network.enable', {})
    # sb.execute_cdp_cmd('Page.enable', {})
    sb.sleep(5)

    sb.type("input[id='username']", sb_user)
    sb.sleep(3)
    sb.type("input[id='password']", sb_pass)
    sb.sleep(3)
    # tab = sb.cdp.page
    # listenXHR(tab)
    # sb.cdp.add_handler(mycdp.network.RequestWillBeSent, send_handler)
    # sb.cdp.add_handler(mycdp.network.ResponseReceived, receive_handler)

    sb.uc_click('button[id*="email-login-button"]')
    # sb.cdp.click('button[id*="email-login-button"]')
    # sb.click('button[id*="email-login-button"]')
    sb.sleep(3)
    # breakpoint()
    current_url = sb.get_current_url()
    # current_url
    if 'verification' in current_url:
        captcha_api_key = os.environ['CAPTCHA_KEY']
        print("Recaptcha detected")
        # solver = TwoCaptcha(captcha_api_key,
        #                     defaultTimeout=120,
        #                     recaptchaTimeout=600)
        # page_actions = PageActions(sb.driver)
        # captcha_helper = CaptchaHelper(sb.driver, solver)

        # script_get_data_captcha = captcha_helper\
        #     .load_js_script('./js_scripts/get_captcha_data.js')
        # script_change_tracking = captcha_helper\
        #     .load_js_script('./js_scripts/track_image_updates.js')

        c_iframe_captcha = "//iframe[@title='reCAPTCHA']"

        print("Solving captcha...")
        try:
            # Check if the reCAPTCHA iframe is present before trying to interact with it
            if sb.is_element_visible(c_iframe_captcha):
                solver = RecaptchaSolver(driver=sb.driver)
                recaptcha_iframe = sb.driver.find_element(By.XPATH, c_iframe_captcha)
                print(f"recaptcha_iframe: {recaptcha_iframe}")
                solver.click_recaptcha_v2(iframe=recaptcha_iframe)
            else:
                print("reCAPTCHA iframe not found, continuing without solving...")
        except Exception as e:
            print(f"Error solving reCAPTCHA: {e}")
            print("Continuing without solving reCAPTCHA...")

        sb.uc_click('button[id*="email-login-button"]')


    sb.sleep(3)
    print("Finished solving captcha")
    current_url = sb.get_current_url()
    print(f"current_url:{current_url}")

    # Check if we need to handle OTP
    if "otp" in current_url:
        print("Email Verification Page..")
        sb.sleep(20)

        IMAP_SERVER = "imappro.zoho.com"
        IMAP_PORT = 993
        EMAIL_ACCOUNT = os.environ['EMAIL_ACCOUNT']
        EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD']

        print(f"Connecting to {IMAP_SERVER}...")

        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

        status, messages = imap.select("INBOX")

        print("Successfully connected and selected INBOX.")

        N = 1
        # total number of emails
        messages = int(messages[0])

        for i in range(messages, messages-N, -1):
            # fetch the email message by ID
            res, msg = imap.fetch(str(i), "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    # parse a bytes email into a message object
                    msg = email.message_from_bytes(response[1])
                    # decode the email subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        # if it's a bytes, decode to str
                        subject = subject.decode(encoding)
                    # decode email sender
                    From, encoding = decode_header(msg.get("From"))[0]
                    if isinstance(From, bytes):
                        From = From.decode(encoding)
                    print("Subject:", subject)
                    print("From:", From)
                    # if the email message is multipart

                    if "stockbit" in From:
                        # iterate over email parts
                        for part in msg.walk():
                            # extract content type of email
                            content_type = part.get_content_type()
                            content_disposition = str(
                                part.get("Content-Disposition"))
                            try:
                                # get the email body
                                body = part.get_payload(decode=True).decode()
                                # print(body)
                                email_soup = BeautifulSoup(body, "html5lib")
                                raw_div = email_soup.select_one(
                                    "div[style*='background-color:#f5f5f5']")
                                otp_code = raw_div.get_text(strip=True)
                                print(f"Otp Code is: {otp_code}")
                                # breakpoint()
                                first_otp_box = ("input[data-cy*='confirm-"
                                                 "otp-input-box']")
                                sb.type(first_otp_box, otp_code)
                                sb.sleep(2)
                                # sb.click("button[class*='ant-btn-primary'][2]")
                                sb.click("button[class*='ant-btn-block']")
                                sb.cdp.add_handler(
                                    mycdp.network.RequestWillBeSent,
                                    send_handler)
                            except Exception as e:
                                print(e)
                                pass

                            if content_type == "text/plain" and \
                               "attachment" not in content_disposition:
                                # print text/plain emails and skip attachments
                                print(body)
                                print("="*100)
                    else:
                        print("No stockbit email..")
                        break

    # Check if we're logged in successfully
    current_url = sb.get_current_url()
    if 'verification' in current_url or 'login' in current_url:
        print("Still not logged in after captcha/OTP. Exiting...")
        exit(1)

    sb.sleep(4)
    sb.cdp.add_handler(mycdp.network.RequestWillBeSent, send_handler)
    # sb.cdp.add_handler(mycdp.network.ResponseReceived, receive_handler)
    url = "https://stockbit.com/stream"
    sb.cdp.open(url)

    # Wait for requests to be captured
    sb.sleep(10)

    # Check if we captured any requests
    if not captured_requests:
        print("No requests captured. Trying to navigate again...")
        sb.cdp.open(url)
        sb.sleep(10)

    headers_list = [request['headers'] for request in captured_requests]
    df_headers = pd.DataFrame(headers_list)

    # Check if Authorization header exists
    if 'Authorization' not in df_headers.columns:
        print("Authorization header not found in captured requests")
        print("Available columns:", df_headers.columns.tolist())
        print("Trying to find authorization in other headers...")

        # Try to find authorization in lowercase or other variations
        auth_header = None
        for col in df_headers.columns:
            if 'auth' in col.lower():
                auth_header = col
                print(f"Found potential auth header: {col}")
                break

        if auth_header:
            bearer_token = df_headers[auth_header].dropna().unique()[0]
        else:
            print("No authorization header found. Exiting...")
            exit(1)
    else:
        bearer_token = df_headers['Authorization'].dropna().unique()[0]

    print(f"Bearer Token: {bearer_token}")

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': bearer_token,
        'cache-control': 'no-cache',
        'origin': 'https://stockbit.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://stockbit.com/',
        'sec-ch-ua': ('"Google Chrome";v="137", "Chromium";v="137", '
                      '"Not/A)Brand";v="24"'),
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/137.0.0.0 Safari/537.36'),
    }

    proxy = {
        "http": f"http://{proxy_string}",
        "https": f"http://{proxy_string}"
    }

    scraper = cloudscraper.create_scraper()

    # Fetch data for 5000 lots and process it
    five_thousands_raw_df = fetch_sb_rt_data(scraper, 5000, 60, headers, proxy)
    five_thousands_filtered_df = process_and_filter_rt_data(
        five_thousands_raw_df, website, today_date)

    # Fetch data for 1000 lots and process it
    # one_thousand_raw_df = fetch_sb_rt_data(scraper, 1000, 1000, headers,
    # proxy)
    # one_thousands_filtered_df = process_and_filter_rt_data(
    #    one_thousand_raw_df, website, today_date)

    print("\n--- Filtered 5000+ Lot Data ---")
    print(five_thousands_filtered_df.head())

    # print("\n--- Filtered 1000+ Lot Data ---")
    # print(one_thousands_filtered_df.head())

    sb.open(website)
    sb.click('[href*="accounts/login"]')
    sb.type('[name="login"]', f"{site_email}")
    sb.type('[name="password"]', f"{site_password}")
    sb.click('button[type*="submit"]')
    sb.sleep(2)

    final_five_thousand_df = pd.concat([
        get_individual_stock(
            sb=sb, row=row)
        for index, row in five_thousands_filtered_df.iterrows()
        ], ignore_index=True)

    # final_one_thousand_df = pd.concat([
    #    get_individual_stock(
    #        sb=sb, row=row)
    #    for index, row in five_thousands_filtered_df.iterrows()
    #    ], ignore_index=True)

BOT_TOKEN = os.environ['BOT_TOKEN']
TARGET_CHAT_ID = "1415309056"
bot = telegram.Bot(token=BOT_TOKEN)


async def main():
    # 1. Send daily summary
    await send_order_book_summary_message(
        df=final_five_thousand_df,
        bot=bot,
        type='5000',
        TARGET_CHAT_ID=TARGET_CHAT_ID
    )

    # 2. Send daily individual messages
    await send_all_orderbook_messages(final_five_thousand_df,
                                      bot, TARGET_CHAT_ID)


if __name__ == "__main__":
    asyncio.run(main())

private_key_id = os.environ['SA_PRIVKEY_ID']
sa_client_email = os.environ['SA_CLIENTMAIL']
sa_client_x509_url = os.environ['SA_CLIENT_X509_URL']

private_key = os.environ['SA_PRIVKEY']

private_key = private_key.replace('\\n', '\n')
full_private_key = f"-----BEGIN PRIVATE KEY-----\n"\
                    f"{private_key}\n-----END PRIVATE KEY-----\n"

service_account_dict = {
    "type": "service_account",
    "project_id": "keterbukaan-informasi-idx",
    "private_key_id": private_key_id,
    "private_key": full_private_key,
    "client_email": sa_client_email,
    "client_id": "116805150468350492730",
    "auth_uri": "https://accounts.google.com/oauth2/auth",
    "token_uri": 'https://oauth2.googleapis.com/token',
    "auth_provider_x509_cert_url":
    "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": sa_client_x509_url,
    "universe_domain": "googleapis.com"
}

scope = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

gauth = GoogleAuth()

try:
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        service_account_dict, scope
    )
except Exception as e:
    print(f"Error loading credentials from dictionary: {e}")
    # Handle error appropriately, maybe exit
    exit(1)

creds = gauth.credentials
gc = None
spreadsheet = None
worksheet = None
try:
    gc = gspread.authorize(creds)
    print("Google Sheets client (gspread) initialized successfully.")

    sheet_key = "1hZCPCVf6xw0w9LS_8Cr1i_VXp6bZfw7gAK255srhvi4"
    spreadsheet = gc.open_by_key(sheet_key)

    print(f"Successfully opened spreadsheet: '{spreadsheet.title}'")

except gspread.exceptions.SpreadsheetNotFound:
    print("Error: Spreadsheet not found. \n"
          "1. Check if the name/key/URL is correct.\n")
    # Decide if you want to exit or continue without sheet access
    exit(1)
except gspread.exceptions.APIError as e:
    print(f"Google Sheets API Error: {e}")
    exit(1)
except Exception as e:
    # Catch other potential errors during gspread initialization/opening
    print(f"An error occurred during Google Sheets setup: {e}")
    exit(1)

print("Updating Google Sheet..")
export_to_sheets(spreadsheet=spreadsheet, sheet_name='> 5000 Lot',
                 df=final_five_thousand_df, mode='a')
