from seleniumbase import SB
import time
from bs4 import BeautifulSoup
import pandas as pd
import re
import telegram
from utils.telegram_utils import send_high_level_summary_message, \
    send_daily_message
import asyncio
from utils.scraping_utils import get_summary_table, get_individual_stock
from dotenv import load_dotenv
import os
from pydrive2.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from utils.gsheet_utils import export_to_sheets
from selenium.webdriver.common.keys import Keys

load_dotenv(override=True)

user = os.environ['PROXY_USER']
password = os.environ['PROXY_PASSWORD']
proxy_host = os.environ['PROXY_HOST']
proxy_port = os.environ['PROXY_PORT']

proxy_string = f"{user}:{password}@{proxy_host}:{proxy_port}"

website = os.environ['WEBSITE']
site_email = os.environ['SITE_EMAIL']
site_password = os.environ['SITE_PASSWORD']

if __name__ == "__main__":
    with SB(uc=True,
            headless=False,
            xvfb=False,
            #proxy=proxy_string,
            maximize=True,
            ) as sb:
        # sb.driver.execute_cdp_cmd(
        #         "Network.setExtraHTTPHeaders",
        #         {
        #             "headers": {
        #                 'Accept': 'text/html,application/xhtml+xml,application\
        #                     /xml;q=0.9,image/avif,image/webp,image/apng,*/*;\
        #                         q=0.8,application/signed-exchange;v=b3;q=0.7',
        #                 'Accept-Encoding': 'gzip, deflate, br, zstd',
        #                 'Accept-Language': 'en-US,en;q=0.9',
        #                 'Cache-Control': "no-cache",
        #                 'Pragma': "no-cache",
        #                 'Priority': "u=0, i",
        #                 'Sec-Ch-Ua': '"Chromium";v="134", \
        #                     "Not:A-Brand";v="24","Google Chrome";v="134"',
        #                 'Sec-Ch-Mobile': "?0",
        #                 'Sec-Ch-Ua-Platform': '"macOS"',
        #                 'Sec-Fetch-Dest': "document",
        #                 'Sec-Fetch-Mode': "navigate",
        #                 'Sec-Fetch-User': "?1",
        #                 'Upgrade-Insecure-Requests': '1',
        #             }
        #         }
        #     )

        # sb.driver.execute_cdp_cmd(
        #         "Network.setUserAgentOverride",
        #         {
        #             "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X \
        #                 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) \
        #                     Chrome/134.0.0.0 Safari/537.36"
        #         },
        #     )

        # sb.driver.execute_script("Object.defineProperty(navigator, \
        #                          'webdriver',{get: () => undefined})")

        sb.open("https://www.google.com")

        sb.open(website)
        # sb.wait_for_element(selector)
        print("Logging in...")
       # sb.click('[href*="accounts/login"]')
        sb.open(f"{website}/accounts/login/")
        sb.sleep(15)
        sb.type('[name="login"]', f"{site_email}")
        sb.type('[name="password"]', f"{site_password}")
        sb.sleep(5)

        sb.click('button[type*="submit"]')

        print("Login submitted, waiting for redirect...")
        sb.sleep(30)
        
        sb.open(f"{website}/home/")
        sb.sleep(10)
        print("Login successful. Opening market summary page...")
        sb.open(f"{website}/market_summary/")
        sb.sleep(60)

        #sb.refresh()
        #sb.sleep(30)

        sb.click('button[id*="reset-button"]')
        sb.sleep(60)
        summary_html = sb.get_page_source()

        soup = BeautifulSoup(summary_html, 'html5lib')

        raw_date = soup.find("div", {"id": "market-summary"}).find('label')\
            .get_text()

        match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', raw_date)

        if match:
            date = match.group(1)
            print(f"Current Data Date: {date}")

        # GET DAILY NON RETAIL
        print("Getting daily non-retail summary...")
        #breakpoint()
        #sb.hover_and_click("#method", '[value = "nr"]', timeout=3)
        sb.select_option_by_text('#method', 'Non-Retail Flow')
        sb.send_keys('#method', Keys.RETURN)
        sb.sleep(40)
        sb.save_screenshot(f'screenshot/{date}_nr_daily.png')
        nr_daily_html = sb.get_page_source()
        nr_daily_summary_df = get_summary_table(nr_daily_html,
                                                today_date=date,
                                                method='non-retail')
        
        table = soup.find('table')
        first_tr = table.find('tr')
        headers = [th.get('data-dash-column', '') for th in
                   first_tr.find_all('th')]
        liquid_index = headers.index('likuid')
        print(f"Liquid Index Column Position: {liquid_index}")
        # APPLY LIQUID FILTER
        try:
            likuid_filter_selector = f'#market-summary-table > div.dash-spreadsheet-container.dash-spreadsheet.dash-freeze-left.dash-empty-01.dash-fill-width > div > div.dt-table-container__row.dt-table-container__row-1 > div.cell.cell-1-1.dash-fixed-content > table > tbody > tr:nth-child(2) > th.dash-filter.column-{str(liquid_index)} > div > input[type=text]:nth-child(1)'
            sb.type(likuid_filter_selector, 'v\n')
            sb.send_keys(likuid_filter_selector, Keys.RETURN)
            sb.sleep(10)
            nr_daily_liquid_html = sb.get_page_source()
            print("Getting liquid filtered daily non-retail summary...")
            nr_daily_summary_liquid_df = get_summary_table(nr_daily_liquid_html,
                                                            today_date=date,
                                                            method='non-retail')
            sb.click('button[id*="reset-button"]')
            sb.sleep(60)
        except Exception as e:
            print(f"Error applying liquid filter: {e}")
            nr_daily_summary_liquid_df = None


        # nr_daily_summary_df

        # GET DAILY MARKET MAKER
        print("Getting daily market maker summary...")
        #sb.hover_and_click("#method", '[value = "m"]', timeout=1)
        sb.select_option_by_text('#method', 'Market Maker Analysis')
        sb.send_keys('#method', Keys.RETURN)
        sb.sleep(40)
        sb.save_screenshot(f'screenshot/{date}_m_daily.png')
        m_daily_html = sb.get_page_source()
        m_daily_summary_df = get_summary_table(m_daily_html,
                                               today_date=date,
                                               method='market maker')
        
        try:
            likuid_filter_selector = f'#market-summary-table > div.dash-spreadsheet-container.dash-spreadsheet.dash-freeze-left.dash-empty-01.dash-fill-width > div > div.dt-table-container__row.dt-table-container__row-1 > div.cell.cell-1-1.dash-fixed-content > table > tbody > tr:nth-child(2) > th.dash-filter.column-{str(liquid_index)} > div > input[type=text]:nth-child(1)'
            sb.type(likuid_filter_selector, 'v\n')
            sb.send_keys(likuid_filter_selector, Keys.RETURN)
            sb.sleep(10)
            m_daily_liquid_html = sb.get_page_source()
            print("Getting liquid filtered daily market maker summary...")
            m_daily_summary_liquid_df = get_summary_table(m_daily_liquid_html,
                                                            today_date=date,
                                                            method='market maker')
            sb.click('button[id*="reset-button"]')
            time.sleep(40)
        except Exception as e:
            print(f"Error applying liquid filter: {e}")
            m_daily_summary_liquid_df = None

        #breakpoint()
        # m_daily_summary_df

        combined_daily_df = pd.concat(
            [nr_daily_summary_df, nr_daily_summary_liquid_df, m_daily_summary_df, m_daily_summary_liquid_df]).reset_index(drop=True)
        print(f"Combined Daily DataFrame Length: {len(combined_daily_df)}")
        print("Removing duplicates based on 'symbol' column...")
        combined_daily_df = combined_daily_df.drop_duplicates('symbol')\
            .reset_index(drop=True)
        print(f"Length after removing duplicates: {len(combined_daily_df)}")
        combined_daily_df['link'] = combined_daily_df['symbol']\
            .apply(lambda x: f"{website}/stock_detail/{x}")
        combined_daily_df['price'] = combined_daily_df['price'].astype(int)
        combined_daily_df = combined_daily_df[combined_daily_df.price > 50]\
            .reset_index(drop=True)
        combined_daily_df

        symbol_set = set(combined_daily_df['symbol'].tolist())

        # GET CUMMULATIVE NON RETAIL
        print("Getting cummulative non-retail summary...")
        #sb.hover_and_click("#method", '[value = "nr"]', timeout=1)
        sb.select_option_by_text('#method', 'Non-Retail Flow')
        sb.send_keys('#method', Keys.RETURN)
        sb.sleep(40)
        #sb.hover_and_click("#summary-mode", '[value = "c"]', timeout=1)
        sb.select_option_by_text('#summary-mode', 'Cumulative')
        sb.send_keys('#summary-mode', Keys.RETURN)
        sb.sleep(40)
        sb.save_screenshot(f'screenshot/{date}_nr_cummulative.png')
        nr_cummulative_html = sb.get_page_source()
        nr_cummulative_summary_df = get_summary_table(nr_cummulative_html,
                                                      today_date=date,
                                                      method='non-retail')

        try:
            likuid_filter_selector = f'#market-summary-table > div.dash-spreadsheet-container.dash-spreadsheet.dash-freeze-left.dash-empty-01.dash-fill-width > div > div.dt-table-container__row.dt-table-container__row-1 > div.cell.cell-1-1.dash-fixed-content > table > tbody > tr:nth-child(2) > th.dash-filter.column-{str(liquid_index)} > div > input[type=text]:nth-child(1)'
            sb.type(likuid_filter_selector, 'v\n')
            sb.send_keys(likuid_filter_selector, Keys.RETURN)
            sb.sleep(10)
            nr_cummulative_liquid_html = sb.get_page_source()
            print("Getting liquid filtered nr cummulative summary...")
            nr_cummulative_summary_liquid_df = get_summary_table(nr_cummulative_liquid_html,
                                                                 today_date=date,
                                                                 method='non-retail')
            sb.click('button[id*="reset-button"]')
            sb.sleep(40)
        except Exception as e:
            print(f"Error applying liquid filter: {e}")
            nr_cummulative_summary_liquid_df = None
        # nr_cummulative_summary_df

        # GET CUMMULATIVE MARKET MAKER
        print("Getting cummulative market maker summary...")
        #sb.hover_and_click("#method", '[value = "m"]', timeout=1)
        sb.select_option_by_text('#method', 'Market Maker Analysis')
        sb.send_keys('#method', Keys.RETURN)
        sb.sleep(40)
        #sb.hover_and_click("#summary-mode", '[value = "c"]', timeout=1)
        sb.select_option_by_text('#summary-mode', 'Cumulative')
        sb.send_keys('#summary-mode', Keys.RETURN)
        sb.sleep(40)
        sb.save_screenshot(f'screenshot/{date}_m_cummulative.png')
        m_cummulative_html = sb.get_page_source()
        m_cummulative_summary_df = get_summary_table(m_cummulative_html,
                                                     today_date=date,
                                                     method='market maker')

        try:
            likuid_filter_selector = f'#market-summary-table > div.dash-spreadsheet-container.dash-spreadsheet.dash-freeze-left.dash-empty-01.dash-fill-width > div > div.dt-table-container__row.dt-table-container__row-1 > div.cell.cell-1-1.dash-fixed-content > table > tbody > tr:nth-child(2) > th.dash-filter.column-{str(liquid_index)} > div > input[type=text]:nth-child(1)'
            sb.type(likuid_filter_selector, 'v\n')
            sb.send_keys(likuid_filter_selector, Keys.RETURN)
            sb.sleep(10)
            m_cummulative_liquid_html = sb.get_page_source()
            print("Getting liquid filtered m cummulative summary...")
            m_cummulative_summary_liquid_df = get_summary_table(m_cummulative_liquid_html,
                                                                 today_date=date,
                                                                 method='market maker')
            sb.click('button[id*="reset-button"]')
            sb.sleep(40)
        except Exception as e:
            print(f"Error applying liquid filter: {e}")
            m_cummulative_summary_liquid_df = None
        # m_cummulative_summary_df

        combined_cummulative_df = pd.concat(
            [nr_cummulative_summary_df, nr_cummulative_summary_liquid_df, m_cummulative_summary_df, m_cummulative_summary_liquid_df])\
            .reset_index(drop=True)
        print(f"Cummulative DataFrame Length before filtering: {len(combined_cummulative_df)}")
        
        combined_cummulative_df = combined_cummulative_df.drop_duplicates('symbol')\
            .reset_index(drop=True)
        
        combined_cummulative_df = combined_cummulative_df[
            ~combined_cummulative_df.symbol.isin(symbol_set)].reset_index(drop=True)
        print(f"Cummulative DataFrame Length after filtering: {len(combined_cummulative_df)}")
        
        combined_cummulative_df['link'] = combined_cummulative_df['symbol']\
            .apply(lambda x: f"{website}/stock_detail/{x}")
        
        combined_cummulative_df['price'] = combined_cummulative_df['price']\
            .astype(int)
        combined_cummulative_df = combined_cummulative_df[
            combined_cummulative_df.price > 50].reset_index(drop=True)
        combined_cummulative_df

        print("Final Daily DataFrames Preparation...")
        final_daily_df = pd.concat([
            get_individual_stock(
                sb=sb, row=row)
            for index, row in combined_daily_df.iterrows()
        ], ignore_index=True)

        print("Final Cummulative DataFrame Preparation...")
        try:
            final_cummulative_df = pd.concat([
                get_individual_stock(
                    sb=sb, row=row)
                for index, row in combined_cummulative_df.iterrows()
            ], ignore_index=True)
        except Exception as e:
            print(f"Error preparing final cummulative DataFrame: {e}")
            final_cummulative_df = pd.DataFrame()


# BOT_TOKEN = "8057278135:AAFdbJmz5bgiIOaE6MjVsCBXMmKp__NYGko"
BOT_TOKEN = os.environ['BOT_TOKEN']
TARGET_CHAT_ID = "1415309056"
bot = telegram.Bot(token=BOT_TOKEN)


async def send_all_daily_messages(df, bot, type, TARGET_CHAT_ID):
    for index, row in df.iterrows():
        try:
            print(f"Processing {type} row {index}...")
            await send_daily_message(
                row=row,
                bot=bot,
                type=type,
                TARGET_CHAT_ID=TARGET_CHAT_ID
            )
            await asyncio.sleep(1)  # Add delay between messages
        except Exception as e:
            print(f"❌ Failed for {type} row {index}: {e}")


async def main():
    # 1. Send daily summary
    await send_high_level_summary_message(
        df=final_daily_df,
        bot=bot,
        type='daily',
        TARGET_CHAT_ID=TARGET_CHAT_ID
    )

    # 2. Send daily individual messages
    await send_all_daily_messages(final_daily_df, bot, 'daily', TARGET_CHAT_ID)

    # 3. Send cumulative summary
    await send_high_level_summary_message(
        df=final_cummulative_df,
        bot=bot,
        type='cummulative',
        TARGET_CHAT_ID=TARGET_CHAT_ID
    )

    # 4. Send cumulative individual messages
    await send_all_daily_messages(final_cummulative_df, bot, 'cummulative',
                                  TARGET_CHAT_ID)

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

        sheet_key = "1z-46N5oUsMBwEufpV2uDdECHJetXy4DDe5PwTkozND0"
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
    export_to_sheets(spreadsheet=spreadsheet, sheet_name='Daily',
                     df=final_daily_df, mode='a')

    export_to_sheets(spreadsheet=spreadsheet, sheet_name='Cummulative',
                     df=final_cummulative_df, mode='a')
