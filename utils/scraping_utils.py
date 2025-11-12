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
                    text = p_tag.get_text(strip=True).replace('⭐', '')
                else:
                    text = cell_div.get_text(strip=True).replace('⭐', '')
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
    try:
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
        try:
            if sidebar_condition in ['sidebar-open', 'dark-mode']:
                sb.click('a[id*="collapse-burger"]')
        except Exception as e:
            print(f"Error while collapsing sidebar: {e}")

        time.sleep(1)
        tc_overview_pic_name = f"screenshot/{row['date']}_{row['symbol']}"\
            "_tc_overview.png"
        sb.save_screenshot(tc_overview_pic_name)
        time.sleep(0.5)
        sb.execute_script("document.body.style.zoom='80%'")
        time.sleep(1)

        # sb.scroll_to('#balance-position-chart')
        if sb.is_element_present('#balance-position-chart'):
            sb.scroll_to('#balance-position-chart')
            time.sleep(1)
            sb.execute_script("window.scrollBy(0, -120);")
            time.sleep(1)
            bp_overview_pic_name = (f"screenshot/"
                                    f"{row['date']}_{row['symbol']}_bp.png")
            sb.save_screenshot(bp_overview_pic_name)
            time.sleep(0.5)

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
    except Exception as e:
        print(f"Error processing {row['symbol']}: {e}")
        return pd.DataFrame()


def fetch_sb_rt_data(scraper, min_lot, price_from, headers, proxies):
    """Fetches and paginates through trade data until no more results are
    returned."""
    print(f"Getting data for minimum lot: {min_lot}")
    all_trades = []
    last_trade_number = None

    params = {
        'limit': '100',
        'order_by': 'ORDER_BY_TIME',
        'action_type': 'ACTION_TYPE_ALL',
        'minimum_lot': str(min_lot),
        'price_range_from': str(price_from),
    }

    while True:
        if last_trade_number:
            params['trade_number'] = last_trade_number

        time.sleep(2)
        response = scraper.get(
            'https://exodus.stockbit.com/company-price-feed/v2/running-trade',
            params=params, headers=headers, proxies=proxies
        )
        response.raise_for_status()

        trades = response.json().get('data', {}).get('running_trade', [])
        if not trades:
            print("Done fetching.")
            break

        current_df = pd.DataFrame(trades)
        all_trades.append(current_df)
        last_trade_number = current_df.iloc[-1]['trade_number']
        print(f"Last Trade Number: {last_trade_number}")

    return pd.concat(all_trades, ignore_index=True) if all_trades \
        else pd.DataFrame()


def process_and_filter_rt_data(df, website, today_date):
    """Cleans, aggregates, and filters the raw trade data."""
    if df.empty:
        return df

    # --- Vectorized Cleaning & Feature Engineering ---
    df['price'] = pd.to_numeric(df['price'].str.replace(',', ''))
    df['lot'] = pd.to_numeric(df['lot'].str.replace(',', ''))
    df['value'] = df['price'] * df['lot']

    is_buy = df['action'] == 'buy'
    df['buy_lot'] = df['lot'].where(is_buy)
    df['sell_lot'] = df['lot'].where(~is_buy)
    df['buy_value'] = df['value'].where(is_buy)
    df['sell_value'] = df['value'].where(~is_buy)

    # --- Aggregation ---
    agg_df = df.groupby('code').agg(
        price=('price', 'last'),
        change=('change', 'last'),
        total_count=('code', 'size'),
        total_lot=('lot', 'sum'),
        total_value=('value', 'sum'),
        buy_count=('buy_lot', 'count'),
        sell_count=('sell_lot', 'count'),
        buy_lot=('buy_lot', 'sum'),
        sell_lot=('sell_lot', 'sum'),
        buy_value=('buy_value', 'sum'),
        sell_value=('sell_value', 'sum')
    )

    # --- Filtering and Combining ---
    buy_higher_than_sell = agg_df[
        (agg_df['buy_count'] > agg_df['sell_count']) &
        (agg_df['change'].str.contains("-")) &
        (agg_df['total_count'] > 10)
    ]

    sell_zero = agg_df[
        (agg_df['sell_count'] == 0) &
        (agg_df['total_count'] >= 3)
    ]

    top_15_count = agg_df.nlargest(15, 'total_count')
    top_15_lot = agg_df.nlargest(15, 'total_lot')

    filtered_df = pd.concat([
        top_15_count, top_15_lot, buy_higher_than_sell, sell_zero
    ]).drop_duplicates().reset_index()

    # --- Final Touches ---
    filtered_df = filtered_df.rename(columns={'code': 'symbol'})
    filtered_df['link'] = filtered_df['symbol']\
        .apply(lambda x: f"{website}/stock_detail/{x}")
    filtered_df.insert(0, 'date', today_date)

    return filtered_df
