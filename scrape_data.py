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
from selenium.webdriver.common.action_chains import ActionChains
from utils.logging_utils import get_logger

load_dotenv(override=True)

logger = get_logger("scrape_data")

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
            # proxy=proxy_string,
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
        logger.info("Logging in...")
       # sb.click('[href*="accounts/login"]')
        sb.open(f"{website}/accounts/login/")
        sb.sleep(15)
        sb.type('[name="login"]', f"{site_email}")
        sb.type('[name="password"]', f"{site_password}")
        sb.sleep(5)

        sb.click('button[type*="submit"]')

        logger.info("Login submitted, waiting for redirect...")
        sb.sleep(30)
        
        sb.open(f"{website}/home/")
        sb.sleep(10)
        logger.info("Login successful. Opening market summary page...")
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
            logger.info("Current Data Date: %s", date)
        # GET DAILY NON RETAIL
        logger.info("Getting daily non-retail summary...")
        #sb.hover_and_click("#method", '[value = "nr"]', timeout=3)
        sb.select_option_by_text('#method', 'Non-Retail Flow')
        sb.send_keys('#method', Keys.RETURN)
        sb.execute_script("""
            var select = document.querySelector('#method');
            if (select) {
                select.dispatchEvent(new Event('change', {bubbles: true}));
            }
        """)
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
        logger.info("Liquid Index Column Position: %s", liquid_index)
        # APPLY LIQUID FILTER
        try:
            filter_selector = f'th.dash-filter.column-{str(liquid_index)} div input[type="text"]'
            
            # Give driver more time to stabilize before checking element
            logger.debug("Waiting for page to stabilize...")
            sb.sleep(5)
            
            # Check if element is present before attempting ActionChains
            sb.wait_for_element_present(filter_selector, timeout=15)
            logger.debug("Filter element is present in DOM")
            # breakpoint()
            # Use SeleniumBase's native type method which handles events properly
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.debug("Starting ActionChains attempt %s", attempt + 1)
                    element = sb.driver.find_element("css selector", filter_selector)
                    logger.debug("Element found: %s", element)
                    action = ActionChains(sb.driver)
                    logger.debug("ActionChains created")
                    action.move_to_element(element)
                    logger.debug("Moved to element")
                    action.click()
                    logger.debug("Click action added")
                    action.send_keys('v')
                    logger.debug("Send keys 'v' action added")
                    action.send_keys(Keys.RETURN)
                    logger.debug("Send keys RETURN action added")
                    action.perform()
                    logger.debug("ActionChains performed successfully")
                    logger.info("Filter applied successfully via ActionChains (attempt %s)", attempt + 1)
                    break
                except Exception as driver_error:
                    logger.error("ActionChains attempt %s failed: %s", attempt + 1, driver_error)
                    if attempt < max_retries - 1:
                        logger.info("Retrying... (%s/%s)", attempt + 2, max_retries)
                        sb.sleep(5)  # Increased sleep time between retries
                    else:
                        logger.error("All ActionChains attempts failed, falling back to JavaScript")
                        # Fallback to JavaScript if all attempts fail
                        js_selector = filter_selector.replace('"', '\\"')
                        sb.execute_script(f"""
                            var input = document.querySelector("{js_selector}");
                            if (input) {{
                                // Focus the input
                                input.focus();
                                input.click();
                                
                                // Use React's internal setter to bypass controlled input
                                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                nativeInputValueSetter.call(input, 'v');
                                
                                // Dispatch input event (React listens to this)
                                var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(inputEvent);
                                
                                // Also dispatch change event
                                var changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(changeEvent);
                                
                                // Simulate full Enter key sequence
                                var keydownEvent = new KeyboardEvent('keydown', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keydownEvent);
                                
                                var keypressEvent = new KeyboardEvent('keypress', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    charCode: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keypressEvent);
                                
                                var keyupEvent = new KeyboardEvent('keyup', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keyupEvent);
                            }}
                        """)
                        logger.info("JavaScript fallback executed")
            sb.sleep(15)
            nr_daily_liquid_html = sb.get_page_source()
            logger.info("Getting liquid filtered daily non-retail summary...")
            nr_daily_summary_liquid_df = get_summary_table(nr_daily_liquid_html,
                                                            today_date=date,
                                                            method='non-retail')
            sb.click('button[id*="reset-button"]')
            sb.sleep(60)
        except Exception as e:
            logger.error("Error applying liquid filter: %s", e)
            nr_daily_summary_liquid_df = None

       #breakpoint()

        # nr_daily_summary_df

        # GET DAILY MARKET MAKER
        logger.info("Getting daily market maker summary...")
        #sb.hover_and_click("#method", '[value = "m"]', timeout=1)
        sb.select_option_by_text('#method', 'Market Maker Analysis')
        sb.send_keys('#method', Keys.RETURN)
        sb.execute_script("""
            var select = document.querySelector('#method');
            if (select) {
                select.dispatchEvent(new Event('change', {bubbles: true}));
            }
        """)
        sb.sleep(40)
        sb.save_screenshot(f'screenshot/{date}_m_daily.png')
        m_daily_html = sb.get_page_source()
        m_daily_summary_df = get_summary_table(m_daily_html,
                                               today_date=date,
                                               method='market maker')
        
        try:
            filter_selector = f'th.dash-filter.column-{str(liquid_index)} div input[type="text"]'
            
            # Give driver more time to stabilize before checking element
            logger.debug("Waiting for page to stabilize...")
            sb.sleep(5)
            
            # Check if element is present before attempting ActionChains
            sb.wait_for_element_present(filter_selector, timeout=15)
            logger.debug("Filter element is present in DOM")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.debug("Starting ActionChains attempt %s", attempt + 1)
                    element = sb.driver.find_element("css selector", filter_selector)
                    logger.debug("Element found: %s", element)
                    action = ActionChains(sb.driver)
                    logger.debug("ActionChains created")
                    action.move_to_element(element)
                    logger.debug("Moved to element")
                    action.click()
                    logger.debug("Click action added")
                    action.send_keys('v')
                    logger.debug("Send keys 'v' action added")
                    action.send_keys(Keys.RETURN)
                    logger.debug("Send keys RETURN action added")
                    action.perform()
                    logger.debug("ActionChains performed successfully")
                    logger.info("Filter applied successfully via ActionChains (attempt %s)", attempt + 1)
                    break
                except Exception as driver_error:
                    logger.error("ActionChains attempt %s failed: %s", attempt + 1, driver_error)
                    if attempt < max_retries - 1:
                        logger.info("Retrying... (%s/%s)", attempt + 2, max_retries)
                        sb.sleep(2)
                    else:
                        logger.error("All ActionChains attempts failed, falling back to JavaScript")
                        # Fallback to JavaScript if all attempts fail
                        js_selector = filter_selector.replace('"', '\\"')
                        sb.execute_script(f"""
                            var input = document.querySelector("{js_selector}");
                            if (input) {{
                                // Focus the input
                                input.focus();
                                input.click();
                                
                                // Use React's internal setter to bypass controlled input
                                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                nativeInputValueSetter.call(input, 'v');
                                
                                // Dispatch input event (React listens to this)
                                var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(inputEvent);
                                
                                // Also dispatch change event
                                var changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(changeEvent);
                                
                                // Simulate full Enter key sequence
                                var keydownEvent = new KeyboardEvent('keydown', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keydownEvent);
                                
                                var keypressEvent = new KeyboardEvent('keypress', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    charCode: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keypressEvent);
                                
                                var keyupEvent = new KeyboardEvent('keyup', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keyupEvent);
                            }}
                        """)
                        logger.info("JavaScript fallback executed")
            sb.sleep(15)
            #breakpoint()
            m_daily_liquid_html = sb.get_page_source()
            logger.info("Getting liquid filtered daily market maker summary...")
            m_daily_summary_liquid_df = get_summary_table(m_daily_liquid_html,
                                                            today_date=date,
                                                            method='market maker')
            sb.click('button[id*="reset-button"]')
            time.sleep(40)
        except Exception as e:
            logger.error("Error applying liquid filter: %s", e)
            m_daily_summary_liquid_df = None

        #breakpoint()
        # m_daily_summary_df

        combined_daily_df = pd.concat(
            [nr_daily_summary_df, nr_daily_summary_liquid_df, m_daily_summary_df, m_daily_summary_liquid_df]).reset_index(drop=True)
        logger.info("Combined Daily DataFrame Length: %s", len(combined_daily_df))
        logger.info("Removing duplicates based on 'symbol' column...")
        combined_daily_df = combined_daily_df.drop_duplicates('symbol')\
            .reset_index(drop=True)
        logger.info("Length after removing duplicates: %s", len(combined_daily_df))
        combined_daily_df['link'] = combined_daily_df['symbol']\
            .apply(lambda x: f"{website}/stock_detail/{x}")
        combined_daily_df['price'] = combined_daily_df['price'].astype(int)
        combined_daily_df = combined_daily_df[combined_daily_df.price > 50]\
            .reset_index(drop=True)
        combined_daily_df

        symbol_set = set(combined_daily_df['symbol'].tolist())

        # GET CUMMULATIVE NON RETAIL
        logger.info("Getting cummulative non-retail summary...")
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
            filter_selector = f'th.dash-filter.column-{str(liquid_index)} div input[type="text"]'
            
            # Give driver more time to stabilize before checking element
            logger.debug("Waiting for page to stabilize...")
            sb.sleep(5)
            
            # Check if element is present before attempting ActionChains
            sb.wait_for_element_present(filter_selector, timeout=15)
            logger.debug("Filter element is present in DOM")
            # Use SeleniumBase's native type method which handles events properly
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.debug("Starting ActionChains attempt %s", attempt + 1)
                    element = sb.driver.find_element("css selector", filter_selector)
                    logger.debug("Element found: %s", element)
                    action = ActionChains(sb.driver)
                    logger.debug("ActionChains created")
                    action.move_to_element(element)
                    logger.debug("Moved to element")
                    action.click()
                    logger.debug("Click action added")
                    action.send_keys('v')
                    logger.debug("Send keys 'v' action added")
                    action.send_keys(Keys.RETURN)
                    logger.debug("Send keys RETURN action added")
                    action.perform()
                    logger.debug("ActionChains performed successfully")
                    logger.info("Filter applied successfully via ActionChains (attempt %s)", attempt + 1)
                    break
                except Exception as driver_error:
                    logger.error("ActionChains attempt %s failed: %s", attempt + 1, driver_error)
                    if attempt < max_retries - 1:
                        logger.info("Retrying... (%s/%s)", attempt + 2, max_retries)
                        sb.sleep(5)  # Increased sleep time between retries
                    else:
                        logger.error("All ActionChains attempts failed, falling back to JavaScript")
                        # Fallback to JavaScript if all attempts fail
                        js_selector = filter_selector.replace('"', '\\"')
                        sb.execute_script(f"""
                            var input = document.querySelector("{js_selector}");
                            if (input) {{
                                // Focus the input
                                input.focus();
                                input.click();
                                
                                // Use React's internal setter to bypass controlled input
                                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                nativeInputValueSetter.call(input, 'v');
                                
                                // Dispatch input event (React listens to this)
                                var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(inputEvent);
                                
                                // Also dispatch change event
                                var changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(changeEvent);
                                
                                // Simulate full Enter key sequence
                                var keydownEvent = new KeyboardEvent('keydown', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keydownEvent);
                                
                                var keypressEvent = new KeyboardEvent('keypress', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    charCode: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keypressEvent);
                                
                                var keyupEvent = new KeyboardEvent('keyup', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keyupEvent);
                            }}
                        """)
                        logger.info("JavaScript fallback executed")
            sb.sleep(15)
            nr_cummulative_liquid_html = sb.get_page_source()
            logger.info("Getting liquid filtered nr cummulative summary...")
            nr_cummulative_summary_liquid_df = get_summary_table(nr_cummulative_liquid_html,
                                                                 today_date=date,
                                                                 method='non-retail')
            sb.click('button[id*="reset-button"]')
            sb.sleep(40)
        except Exception as e:
            logger.error("Error applying liquid filter: %s", e)
            nr_cummulative_summary_liquid_df = None
        # nr_cummulative_summary_df

        # GET CUMMULATIVE MARKET MAKER
        logger.info("Getting cummulative market maker summary...")
        #sb.hover_and_click("#method", '[value = "m"]', timeout=1)
        sb.select_option_by_text('#method', 'Market Maker Analysis')
        sb.send_keys('#method', Keys.RETURN)
        sb.execute_script("""
            var select = document.querySelector('#method');
            if (select) {
                select.dispatchEvent(new Event('change', {bubbles: true}));
            }
        """)
        sb.sleep(40)
        #sb.hover_and_click("#summary-mode", '[value = "c"]', timeout=1)
        sb.select_option_by_text('#summary-mode', 'Cumulative')
        sb.send_keys('#summary-mode', Keys.RETURN)
        sb.execute_script("""
            var select = document.querySelector('#summary-mode');
            if (select) {
                select.dispatchEvent(new Event('change', {bubbles: true}));
            }
        """)
        sb.sleep(40)
        sb.save_screenshot(f'screenshot/{date}_m_cummulative.png')
        m_cummulative_html = sb.get_page_source()
        m_cummulative_summary_df = get_summary_table(m_cummulative_html,
                                                     today_date=date,
                                                     method='market maker')

        try:
            filter_selector = f'th.dash-filter.column-{str(liquid_index)} div input[type="text"]'
            
            # Give driver more time to stabilize before checking element
            logger.debug("Waiting for page to stabilize...")
            sb.sleep(5)
            
            # Check if element is present before attempting ActionChains
            sb.wait_for_element_present(filter_selector, timeout=15)
            logger.debug("Filter element is present in DOM")
            # Use SeleniumBase's native type method which handles events properly
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.debug("Starting ActionChains attempt %s", attempt + 1)
                    element = sb.driver.find_element("css selector", filter_selector)
                    logger.debug("Element found: %s", element)
                    action = ActionChains(sb.driver)
                    logger.debug("ActionChains created")
                    action.move_to_element(element)
                    logger.debug("Moved to element")
                    action.click()
                    logger.debug("Click action added")
                    action.send_keys('v')
                    logger.debug("Send keys 'v' action added")
                    action.send_keys(Keys.RETURN)
                    logger.debug("Send keys RETURN action added")
                    action.perform()
                    logger.debug("ActionChains performed successfully")
                    logger.info("Filter applied successfully via ActionChains (attempt %s)", attempt + 1)
                    break
                except Exception as driver_error:
                    logger.error("ActionChains attempt %s failed: %s", attempt + 1, driver_error)
                    if attempt < max_retries - 1:
                        logger.info("Retrying... (%s/%s)", attempt + 2, max_retries)
                        sb.sleep(5)  # Increased sleep time between retries
                    else:
                        logger.error("All ActionChains attempts failed, falling back to JavaScript")
                        # Fallback to JavaScript if all attempts fail
                        js_selector = filter_selector.replace('"', '\\"')
                        sb.execute_script(f"""
                            var input = document.querySelector("{js_selector}");
                            if (input) {{
                                // Focus the input
                                input.focus();
                                input.click();
                                
                                // Use React's internal setter to bypass controlled input
                                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                nativeInputValueSetter.call(input, 'v');
                                
                                // Dispatch input event (React listens to this)
                                var inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(inputEvent);
                                
                                // Also dispatch change event
                                var changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                                input.dispatchEvent(changeEvent);
                                
                                // Simulate full Enter key sequence
                                var keydownEvent = new KeyboardEvent('keydown', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keydownEvent);
                                
                                var keypressEvent = new KeyboardEvent('keypress', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    charCode: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keypressEvent);
                                
                                var keyupEvent = new KeyboardEvent('keyup', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                input.dispatchEvent(keyupEvent);
                            }}
                        """)
                        logger.info("JavaScript fallback executed")
            sb.sleep(15)
            m_cummulative_liquid_html = sb.get_page_source()
            logger.info("Getting liquid filtered m cummulative summary...")
            m_cummulative_summary_liquid_df = get_summary_table(m_cummulative_liquid_html,
                                                                 today_date=date,
                                                                 method='market maker')
            sb.click('button[id*="reset-button"]')
            sb.sleep(40)
        except Exception as e:
            logger.error("Error applying liquid filter: %s", e)
            m_cummulative_summary_liquid_df = None
        # m_cummulative_summary_df

        combined_cummulative_df = pd.concat(
            [nr_cummulative_summary_df, nr_cummulative_summary_liquid_df, m_cummulative_summary_df, m_cummulative_summary_liquid_df])\
            .reset_index(drop=True)
        logger.info("Cummulative DataFrame Length before filtering: %s", len(combined_cummulative_df))
        combined_cummulative_df = combined_cummulative_df.drop_duplicates('symbol')\
            .reset_index(drop=True)
        
        combined_cummulative_df = combined_cummulative_df[
            ~combined_cummulative_df.symbol.isin(symbol_set)].reset_index(drop=True)
        logger.info("Cummulative DataFrame Length after filtering: %s", len(combined_cummulative_df))
        combined_cummulative_df['link'] = combined_cummulative_df['symbol']\
            .apply(lambda x: f"{website}/stock_detail/{x}")
        
        combined_cummulative_df['price'] = combined_cummulative_df['price']\
            .astype(int)
        combined_cummulative_df = combined_cummulative_df[
            combined_cummulative_df.price > 50].reset_index(drop=True)
        combined_cummulative_df

        logger.info("Final Daily DataFrames Preparation...")
        final_daily_df = pd.concat([
            get_individual_stock(
                sb=sb, row=row)
            for index, row in combined_daily_df.iterrows()
        ], ignore_index=True)

        logger.info("Final Cummulative DataFrame Preparation...")
        try:
            final_cummulative_df = pd.concat([
                get_individual_stock(
                    sb=sb, row=row)
                for index, row in combined_cummulative_df.iterrows()
            ], ignore_index=True)
        except Exception as e:
            logger.error("Error preparing final cummulative DataFrame: %s", e)
            final_cummulative_df = pd.DataFrame()


# BOT_TOKEN = "8057278135:AAFdbJmz5bgiIOaE6MjVsCBXMmKp__NYGko"
BOT_TOKEN = os.environ['BOT_TOKEN']
TARGET_CHAT_ID = "1415309056"
bot = telegram.Bot(token=BOT_TOKEN)


async def send_all_daily_messages(df, bot, type, TARGET_CHAT_ID):
    for index, row in df.iterrows():
        try:
            logger.info("Processing %s row %s...", type, index)
            await send_daily_message(
                row=row,
                bot=bot,
                type=type,
                TARGET_CHAT_ID=TARGET_CHAT_ID
            )
            await asyncio.sleep(1)  # Add delay between messages
        except Exception as e:
            logger.error("❌ Failed for %s row %s: %s", type, index, e)
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
        logger.error("Error loading credentials from dictionary: %s", e)
        # Handle error appropriately, maybe exit
        exit(1)

    creds = gauth.credentials
    gc = None
    spreadsheet = None
    worksheet = None
    try:
        gc = gspread.authorize(creds)
        logger.info("Google Sheets client (gspread) initialized successfully.")
        sheet_key = "1z-46N5oUsMBwEufpV2uDdECHJetXy4DDe5PwTkozND0"
        spreadsheet = gc.open_by_key(sheet_key)

        logger.info("Successfully opened spreadsheet: '%s'", spreadsheet.title)
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error("Error: Spreadsheet not found. Check if the name/key/URL is correct.")
        exit(1)
    except gspread.exceptions.APIError as e:
        logger.error("Google Sheets API Error: %s", e)
        exit(1)
    except Exception as e:
        # Catch other potential errors during gspread initialization/opening
        logger.error("An error occurred during Google Sheets setup: %s", e)
        exit(1)

    logger.info("Updating Google Sheet..")
    export_to_sheets(spreadsheet=spreadsheet, sheet_name='Daily',
                     df=final_daily_df, mode='a')

    export_to_sheets(spreadsheet=spreadsheet, sheet_name='Cummulative',
                     df=final_cummulative_df, mode='a')
