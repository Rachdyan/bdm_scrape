from bs4 import BeautifulSoup
import pandas as pd
import time
from selenium.webdriver.common.keys import Keys


def get_summary_table(raw_html, today_date, method):
    print(f"Getting {method} summary table for {today_date}")
    soup = BeautifulSoup(raw_html, 'html5lib')
    # html_table = soup.find('table')
    header_row = soup.find('tr')
    headers = [
        th.get('data-dash-column', '') for th in header_row.find_all('th')
        ]

    data_rows = soup.find_all('tr')[2:]  # Skip first two header/filter rows

    data = []
    for row in data_rows:
        cells = row.find_all('td')
        row_data = []
        for td in cells:
            cell_div = td.find('div', class_='dash-cell-value')
            if cell_div:
                # Handle markdown cells with <p> tags
                p_tag = cell_div.find('p')
                if p_tag:
                    text = p_tag.get_text(strip=True)
                else:
                    text = cell_div.get_text(strip=True)
            else:
                text = ''
            row_data.append(text)
        data.append(row_data)

    df = pd.DataFrame(data, columns=headers)
    df.drop_duplicates(inplace=True)
    df.dropna(axis=0, how="all", inplace=True)
    df.insert(0, 'method', method)
    df.insert(0, 'date', today_date)
    return df


def get_individual_stock(sb, row):
    link = row['link']
    print(f"Opening {row['symbol']}...")
    sb.open(link)
    # sb.execute_script("document.body.style.zoom='50%'")

    individual_html = sb.get_page_source()
    soup = BeautifulSoup(individual_html, 'html5lib')

    body = soup.find('body')
    sidebar_condition = body.get('class')[-1]
    # print(f"sidebar condition: {sidebar_condition}")
    # sidebar_mini = body.get('class')[0]
    # print(f"sidebar mini: {sidebar_mini}")
    if sidebar_condition in ['sidebar-open', 'dark-mode']:
        sb.click('a[id*="collapse-burger"]')

    time.sleep(1)
    tc_overview_pic_name = f"screenshot/{row['date']}_{row['symbol']}"\
        "_tc_overview.png"
    sb.save_screenshot(tc_overview_pic_name)
    time.sleep(0.5)
    sb.execute_script("document.body.style.zoom='80%'")
    time.sleep(1)
    sb.scroll_to('#balance-position-chart')
    time.sleep(1)
    sb.execute_script("window.scrollBy(0, -120);")
    time.sleep(1)
    bp_overview_pic_name = f"screenshot/{row['date']}_{row['symbol']}_bp.png"
    sb.save_screenshot(bp_overview_pic_name)
    time.sleep(0.5)
    sb.execute_script("document.body.style.zoom='60%'")
    time.sleep(1)
    sb.scroll_to('#card-transaction-chart')
    time.sleep(1)
    sb.click('button[id*="maximize-transaction-chart"]')
    time.sleep(1)
    tc_detail_pic_name = f"screenshot/{row['date']}_{row['symbol']}"\
        "_tc_detail.png"
    sb.save_screenshot(tc_detail_pic_name)
    time.sleep(1)
    sb.click('button[id*="maximize-transaction-chart"]')
    sb.scroll_to('#tradingview-price-chart')
    time.sleep(1)

    sb.click("div[class='tradingview-widget-container']")
    sb.send_keys('iframe', '1w')
    time.sleep(0.5)
    sb.send_keys('iframe', Keys.ENTER)
    time.sleep(0.5)

    submit_buttons = sb.find_elements('button[type="submit"]')
    if submit_buttons:
        last_submit_button = submit_buttons[-1]
        last_submit_button.click()  # Click it
    else:
        print("No submit buttons found!")

    time.sleep(1)
    pc_pic_name = f"screenshot/{row['date']}_{row['symbol']}_pc.png"
    sb.save_screenshot(pc_pic_name)

    row['ss_directory'] = [tc_overview_pic_name, tc_detail_pic_name,
                           bp_overview_pic_name, pc_pic_name]
    return pd.DataFrame([row])
