from seleniumbase import SB
from bs4 import BeautifulSoup
import pandas as pd
import telegram
from utils.telegram_utils import send_nonreg_summary_message, \
    send_non_reg_message
import asyncio
from utils.scraping_utils import get_individual_stock
from dotenv import load_dotenv
import os
from pydrive2.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from utils.gsheet_utils import export_to_sheets
from datetime import datetime as dt
import pytz

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

raw_today_data = dt.now(pytz.timezone('Asia/Jakarta'))
today_date = raw_today_data.strftime("%Y-%m-%d")
today_date = '2025-11-18'
today_month_year = raw_today_data.strftime("%b %Y")


if __name__ == "__main__":
    with SB(uc=True, headless=False, xvfb=True,
            proxy=proxy_string,
            maximize=True,
            ) as sb:
        sb.driver.execute_cdp_cmd(
                "Network.setExtraHTTPHeaders",
                {
                    "headers": {
                        'Accept': 'text/html,application/xhtml+xml,application\
                            /xml;q=0.9,image/avif,image/webp,image/apng,*/*;\
                                q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br, zstd',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Cache-Control': "no-cache",
                        'Pragma': "no-cache",
                        'Priority': "u=0, i",
                        'Sec-Ch-Ua': '"Chromium";v="134", \
                            "Not:A-Brand";v="24","Google Chrome";v="134"',
                        'Sec-Ch-Mobile': "?0",
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': "document",
                        'Sec-Fetch-Mode': "navigate",
                        'Sec-Fetch-User': "?1",
                        'Upgrade-Insecure-Requests': '1',
                    }
                }
            )

        sb.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {
                    "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X \
                        10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) \
                            Chrome/134.0.0.0 Safari/537.36"
                },
            )

        sb.driver.execute_script("Object.defineProperty(navigator, \
                                 'webdriver',{get: () => undefined})")

        sb.open(f"{stock_website}")
        sb.sleep(5)

        sb.wait_for_element_present("span[class='bzi-bars']")
        sb.click("span[class='bzi-bars']")
        sb.sleep(1)
        sb.click("label[for='fltrAll']")
        sb.sleep(1)
        sb.click("div.actions.text-right.text-caps > button.btn--primary")
        sb.sleep(1)

        sb.wait_for_element_present("input[name='date']")
        sb.click("input[name='date']")

        sb.sleep(1)
        # sb.wait_for_element_present("input[name='date']")
        # sb.click("input[name='date']")
        sb.sleep(1)

        first_calendar_header = sb.find_element(
            "div[class='mx-calendar-header']").text
        # Remove all whitespace variations and normalize
        first_calendar_header = ' '.join(first_calendar_header.split())

        print(f"Today month year: {today_month_year}")
        print(f"First calendar header: {first_calendar_header}")
        if today_month_year != first_calendar_header:
            sb.click("button[class='mx-btn mx-btn-text mx-btn-icon-left']")

        sb.sleep(5)

        print("Clicking Date")
        sb.wait_for_element_present(f"td[title = '{today_date}']")
        today_date_button = sb.find_element(f"td[title = '{today_date}']")
        today_date_button.click()

        sb.sleep(5)

        sb.wait_for_element_present("select[name='perPageSelect']")
        #sb.click("select[name='perPageSelect']")
        #sb.sleep(5)
        #breakpoint()
        #sb.click("option[value='-1']")
        sb.select_option_by_value("select[name='perPageSelect']", "-1")
        sb.execute_script("""
            var select = document.querySelector("select[name='perPageSelect']");
            select.dispatchEvent(new Event('change', { bubbles: true }));
        """)
        sb.sleep(5)  # Wait for table to reload
        #sb.sleep(5)

        raw_html = sb.get_page_source()
        soup = BeautifulSoup(raw_html, 'html5lib')
        table = soup.find('table', id='vgt-table')

        headers = []
        for th in table.find('thead').find('tr').find_all('th'):
            span = th.find('span')
            if span:
                headers.append(span.get_text(strip=True))
            else:
                headers.append(th.get_text(strip=True))
        # Rename the first header to 'Line Number'
        headers[0] = 'No'
        # headers

        # Extract rows from the tbody
        rows = []
        for row in table.find('tbody').find_all('tr'):
            # Find all th and td elements in the row
            cells = row.find_all(['th', 'td'])
            # Extract text from each cell and strip whitespace
            row_data = [cell.get_text(strip=True) for cell in cells]
            rows.append(row_data)

        # Create a DataFrame
        df = pd.DataFrame(rows, columns=headers)
        raw_df = df[['Kode Saham', 'Tanggal Perdagangan Terakhir',
                     'Open Price', 'Penutupan', 'Terendah', 'Tertinggi',
                     'Selisih', 'Volume', 'Nilai', 'Frekuensi',
                     'Non Regular Volume', 'Non Regular Value',
                     'Non Regular Frequency', 'Listed Shares',
                     'Tradeble Shares', 'Offer', 'Offer Volume',
                     'Bid', 'Bid Volume']].copy()

        print(f"Raw DF count: {len(raw_df)}")
        print(raw_df.head())

        month_map = {'Januari': '01', 'Februari': '02', 'Maret': '03',
                     'April': '04', 'Mei': '05', 'Juni': '06',
                     'Juli': '07', 'Agustus': '08', 'September': '9',
                     'Oktober': '10', 'November': '11', 'Desember': '12'}

        for month_str, n_month in month_map.items():
            raw_df['Tanggal Perdagangan Terakhir'] = raw_df[
                'Tanggal Perdagangan Terakhir']\
                    .str.replace(month_str, str(n_month))
            raw_df['Tanggal Perdagangan Terakhir'] = raw_df[
                'Tanggal Perdagangan Terakhir']\
                .str.replace(" ", "-")

        raw_df['Volume'] = raw_df['Volume'].str.replace(".", "").astype(int)
        raw_df['Volume'] = raw_df['Volume'] / 100
        raw_df['Terendah'] = raw_df['Terendah'].str.replace(".", "")\
            .astype(int)
        raw_df['Tertinggi'] = raw_df['Tertinggi'].str.replace(".", "")\
            .astype(int)
        raw_df['Non Regular Volume'] = raw_df['Non Regular Volume']\
            .str.replace(".", "").astype(int)
        raw_df['Non Regular Volume'] = raw_df['Non Regular Volume'] / 100
        raw_df['Non Regular Value'] = raw_df['Non Regular Value']\
            .str.replace(".", "").astype(int)
        raw_df['Nilai'] = raw_df['Nilai'].str.replace(".", "").astype(int)
        raw_df['Non Regular Frequency'] = raw_df['Non Regular Frequency']\
            .str.replace(".", "").astype(int)
        raw_df['Penutupan'] = raw_df['Penutupan'].str.replace(".", "")\
            .astype(int)
        raw_df['Offer Volume'] = raw_df['Offer Volume'].str.replace(".", "")\
            .astype(int)
        raw_df['Offer Volume'] = raw_df['Offer Volume'] / 100
        raw_df['Bid Volume'] = raw_df['Bid Volume'].str.replace(".", "")\
            .astype(int)
        raw_df['Bid Volume'] = raw_df['Bid Volume'] / 100
        raw_df.rename(
            {'Kode Saham': 'symbol', 'Tanggal Perdagangan Terakhir': 'date'},
            axis=1, inplace=True)

        raw_df['value_ratio'] = raw_df.apply(
            lambda x:
            x['Non Regular Value'] / x['Nilai'] if x['Nilai'] != 0 else 0,
            axis=1)

        # if raw_df['Nilai'] != 0:
        #     raw_df['value_ratio'] = (raw_df['Non Regular Value'] /
        #                              raw_df['Nilai'])
        # else:
        #     raw_df['value_ratio'] = 0

        raw_df['avg_price'] = raw_df['Nilai'] / raw_df['Volume'] / 100
        raw_df['avg_nonreg_price'] = (raw_df['Non Regular Value']
                                      / raw_df['Non Regular Volume'] / 100)
        raw_df['avg_nonreg_diff_tertinggi'] = ((raw_df['avg_nonreg_price'] -
                                                raw_df['Tertinggi']) /
                                               raw_df['Tertinggi'] * 100)
        raw_df['link'] = raw_df['symbol']\
            .apply(lambda x: f"{website}/stock_detail/{x}")

        filtered_df = raw_df[
            (raw_df['Non Regular Value'] > raw_df['Nilai']) &
            (raw_df['Non Regular Frequency'] <= 5) &
            (raw_df['value_ratio'] >= 3) &
            (raw_df['Penutupan'] >= 60) &
            (raw_df['Offer Volume'] > 0) &
            (raw_df['Bid Volume'] > 0)]\
            .sort_values('value_ratio', ascending=False)\
            .reset_index(drop=True)
        
        print(f"Filtered DF count: {len(filtered_df)}")

        high_nonreg_price_df = raw_df[
            (raw_df['avg_nonreg_diff_tertinggi'] >= 1) &
            (raw_df['value_ratio'] >= 1) &
            (raw_df['Penutupan'] >= 60) &
            (raw_df['Offer Volume'] > 0) &
            (raw_df['Bid Volume'] > 0)]\
            .sort_values('avg_nonreg_diff_tertinggi', ascending=False)\
            .reset_index(drop=True)
        print(f"High Non-Reg Price DF count: {len(high_nonreg_price_df)}")

        sb.open(website)
        sb.click('[href*="accounts/login"]')
        sb.sleep(2)
        sb.type('[name="login"]', f"{site_email}")
        sb.type('[name="password"]', f"{site_password}")
        sb.sleep(2)
        sb.click('button[type*="submit"]')
        sb.sleep(2)

        try:
            final_high_nonreg_price_df = pd.concat([
                get_individual_stock(
                    sb=sb, row=row)
                for index, row in high_nonreg_price_df.iterrows()
            ], ignore_index=True)
        except Exception as e:
            print(f"Error processing high non-reg price df: {e}")
            final_high_nonreg_price_df = None

        try:
            final_filtered_df = pd.concat([
                get_individual_stock(
                    sb=sb, row=row)
                for index, row in filtered_df.iterrows()
            ], ignore_index=True)
        except Exception as e:
            print(f"Error processing filtered df: {e}")
            final_filtered_df = None


BOT_TOKEN = os.environ['BOT_TOKEN']
TARGET_CHAT_ID = "1415309056"
bot = telegram.Bot(token=BOT_TOKEN)


async def send_all_nonreg_messages(df, bot, TARGET_CHAT_ID):
    for index, row in df.iterrows():
        try:
            print(f"Processing {type} row {index}...")
            await send_non_reg_message(
                row=row,
                bot=bot,
                TARGET_CHAT_ID=TARGET_CHAT_ID
            )
            await asyncio.sleep(1)  # Add delay between messages
        except Exception as e:
            print(f"❌ Failed for {type} row {index}: {e}")


async def main():
    # 1. Send daily summary
    try:
        await send_nonreg_summary_message(
            df=final_high_nonreg_price_df,
            bot=bot,
            type='higher price',
            TARGET_CHAT_ID=TARGET_CHAT_ID
        )

        # 2. Send daily individual messages
        await send_all_nonreg_messages(final_high_nonreg_price_df,
                                    bot, TARGET_CHAT_ID)
    except Exception as e:
        print(f"Error sending higher price messages: {e}")

    # 3. Send cumulative summary
    try:
        await send_nonreg_summary_message(
            df=final_filtered_df,
            bot=bot,
            type='non regular',
            TARGET_CHAT_ID=TARGET_CHAT_ID
        )

        # 4. Send cumulative individual messages
        await send_all_nonreg_messages(final_filtered_df, bot,
                                    TARGET_CHAT_ID)
    except Exception as e:
        print(f"Error sending non regular messages: {e}")

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
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
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

        sheet_key = "1hZYjUl_ADkBgziBg6QALp7oOBPAr1pbTS9WVP_m4uKI"
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
    export_to_sheets(spreadsheet=spreadsheet, sheet_name='Higher Price',
                     df=final_high_nonreg_price_df, mode='a')

    export_to_sheets(spreadsheet=spreadsheet, sheet_name='Non Regular',
                     df=final_filtered_df, mode='a')
