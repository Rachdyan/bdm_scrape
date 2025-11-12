import os
from telegram import InputMediaPhoto, InputFile
from telegram.error import BadRequest
import asyncio


def generate_high_level_summary_str(df, type):
    if type == 'daily':
        summary_str = f'<b>{df.date.unique()[0]} - TOP DAILY ACUM</b>'
    else:
        summary_str = f'<b>{df.date.unique()[0]} - TOP CUMMULATIVE ACUM</b>'

    summary_str += '\n\n'
    summary_str += '<b>NON RETAIL</b>'
    summary_str += '\n'

    nr_stock = df[df.method == 'non-retail'].symbol.to_list()
    summary_str += ', '.join(nr_stock)

    summary_str += '\n\n'
    summary_str += '<b>MARKET MAKER</b>'
    summary_str += '\n'
    m_stock = df[df.method == 'market maker'].symbol.to_list()
    summary_str += ', '.join(m_stock)
    return summary_str


# Define as an async function
async def send_high_level_summary_message(df, bot, type, TARGET_CHAT_ID):
    # Store open file handles to prevent premature closing
    file_handles = []
    media_group = []

    msg_str = generate_high_level_summary_str(df, type)

    date = df.date.unique()[0]
    nr_path = f"screenshot/{date}_nr_{type}.png"
    m_path = f"screenshot/{date}_m_{type}.png"
    files_path = [nr_path, m_path]

    try:
        for idx, file_path in enumerate(files_path):
            # Step 1: Validate absolute path
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                print(f"🚫 File not found: {abs_path}")
                continue

            # Step 2: Normalize path (critical for Windows)
            abs_path = abs_path.replace("\\", "/")  # Force forward slashes

            # Step 3: Open file and retain handle
            file = open(abs_path, "rb")
            file_handles.append(file)  # Keep track of open files

            # Step 4: Create media with HTML caption parsing
            media = InputMediaPhoto(
                media=InputFile(file, filename=os.path.basename(abs_path),
                                attach=True),
                caption=msg_str if idx == 0 else None,
                parse_mode='HTML' if idx == 0 else None
            )
            media_group.append(media)
            print(f"✅ Added {abs_path} to media group")

        # Step 5: Send media group (await inside async function)
        await bot.send_media_group(chat_id=TARGET_CHAT_ID, media=media_group)
        print("Media group sent successfully!")

    except BadRequest as e:
        print(f"💥 Telegram API Error: {e.message}")
        print("Debug Checklist:")
        print("1. File paths: ", [os.path.abspath(p) for p in files_path])
        print("2. File sizes: ",
              [f"{os.path.getsize(p)/1e6:.2f} MB" for p in files_path])

    finally:
        # Step 6: Cleanup - close all files
        for f in file_handles:
            f.close()


def generate_daily_summary_str(row, type):
    msg_str = f"<a href = '{row['link']}'>{row['symbol']}</a>"
    msg_str += '\n\n'
    msg_str += f"<b>Price</b>: {row['price']}"
    msg_str += '\n'
    if type == 'daily':
        msg_str += f'<b>1d Price Change</b>: {row["%1d"]}%'
    else:
        msg_str += f'<b>3d Price Change</b>: {row["%3d"]}%'
        msg_str += '\n'
        msg_str += f'<b>5d Price Change</b>: {row["%5d"]}%'
        msg_str += '\n'
        msg_str += f'<b>10d Price Change</b>: {row["%10d"]}%'
        msg_str += '\n'
        msg_str += f'<b>20d Price Change</b>: {row["%20d"]}%'
    msg_str += '\n'
    msg_str += f'<b>pinky</b>: {row["pinky"]}'
    msg_str += '\n'
    msg_str += f'<b>crossing</b>: {row["crossing"]}'
    msg_str += '\n'
    msg_str += f'<b>unusual</b>: {row["unusual"]}'
    msg_str += '\n'
    msg_str += f'<b>likuid</b>: {row["likuid"]}'
    msg_str += '\n\n'
    msg_str += f"<b>{row['method'].upper()}</b>"
    msg_str += '\n'
    if type == 'daily':
        msg_str += f"<b>d-0</b>: {row['dn-0']}%"
        msg_str += '\n'
        msg_str += f"<b>d-1</b>: {row['dn-1']}%"
        msg_str += '\n'
        msg_str += f"<b>d-2</b>: {row['dn-2']}%"
        msg_str += '\n'
        msg_str += f"<b>d-3</b>: {row['dn-3']}%"
        msg_str += '\n'
        msg_str += f"<b>d-4</b>: {row['dn-4']}%"
        msg_str += '\n\n'
        msg_str += f"<b>w-1</b>: {row['wn-1']}%"
        msg_str += '\n'
        msg_str += f"<b>w-2</b>: {row['wn-2']}%"
        msg_str += '\n'
        msg_str += f"<b>w-3</b>: {row['wn-3']}%"
        msg_str += '\n'
        msg_str += f"<b>w-4</b>: {row['wn-4']}%"
    else:
        msg_str += f"<b>cn-3</b>: {row['cn-3']}%"
        msg_str += '\n'
        msg_str += f"<b>cn-5</b>: {row['cn-5']}%"
        msg_str += '\n'
        msg_str += f"<b>cn-10</b>: {row['cn-10']}%"
        msg_str += '\n'
        msg_str += f"<b>cn-20</b>: {row['cn-20']}%"
        msg_str += '\n'
    return msg_str


# Define as an async function
async def send_daily_message(row, bot, type, TARGET_CHAT_ID):
    # Store open file handles to prevent premature closing
    file_handles = []
    media_group = []

    msg_str = generate_daily_summary_str(row, type)

    try:
        for idx, file_path in enumerate(row['ss_directory']):
            # Step 1: Validate absolute path
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                print(f"🚫 File not found: {abs_path}")
                continue

            # Step 2: Normalize path (critical for Windows)
            abs_path = abs_path.replace("\\", "/")  # Force forward slashes

            # Step 3: Open file and retain handle
            file = open(abs_path, "rb")
            file_handles.append(file)  # Keep track of open files

            # Step 4: Create media with HTML caption parsing
            media = InputMediaPhoto(
                media=InputFile(file, filename=os.path.basename(abs_path),
                                attach=True),
                caption=msg_str if idx == 0 else None,
                parse_mode='HTML' if idx == 0 else None
            )
            media_group.append(media)
            print(f"✅ Added {abs_path} to media group")

        # Step 5: Send media group (await inside async function)
        await bot.send_media_group(chat_id=TARGET_CHAT_ID, media=media_group)
        print("Media group sent successfully!")

    except BadRequest as e:
        print(f"💥 Telegram API Error: {e.message}")
        print("Debug Checklist:")
        print("1. File paths: ",
              [os.path.abspath(p) for p in row['ss_directory']])
        print("2. File sizes: ",
              [f"{os.path.getsize(p)/1e6:.2f} MB"
               for p in row['ss_directory']])

    finally:
        # Step 6: Cleanup - close all files
        for f in file_handles:
            f.close()


def generate_non_regular_summary_str(df, type):
    if type == 'non regular':
        summary_str = f'<b>{df.date.unique()[0]}'\
            ' - TOP NON REGULAR TRANSACTION VALUE</b>'
    if type == 'higher price':
        summary_str = f'<b>{df.date.unique()[0]}'\
            ' - TOP NON REGULAR HIGHER PRICE</b>'

    summary_str += '\n\n'
    all_stock = df.symbol.to_list()
    summary_str += ', '.join(all_stock)

    return summary_str


async def send_nonreg_summary_message(df, bot, type, TARGET_CHAT_ID):
    # Store open file handles to prevent premature closing
    msg_str = generate_non_regular_summary_str(df, type)
    try:
        await bot.send_message(chat_id=TARGET_CHAT_ID,
                               text=msg_str,
                               parse_mode='HTML')
        print("Media group sent successfully!")

    except BadRequest as e:
        print(f"💥 Telegram API Error: {e.message}")


def generate_non_reg_str(row):
    msg_str = f"<a href = '{row['link']}'>{row['symbol']}</a>"
    msg_str += '\n\n'
    msg_str += f"<b>Last Price</b>: {row['Penutupan']}"
    msg_str += '\n'
    msg_str += f"<b>Highest Price</b>: {row['Tertinggi']}"
    msg_str += '\n'
    msg_str += (
        f"<b>Avg Non Reg Price</b>: {row['avg_nonreg_price']:.0f} "
        f"({'+' if row['avg_nonreg_diff_tertinggi'] > 0 else ''}"
        f"{row['avg_nonreg_diff_tertinggi']:.1f}%)"
    )
    msg_str += '\n\n'
    msg_str += f"<b>Volume</b>: {row['Volume']:,.0f} Lot"
    msg_str += '\n'
    msg_str += f"<b>Value</b>: Rp{row['Nilai']:,}"
    msg_str += '\n'
    msg_str += f"<b>Frekuensi</b>: {row['Frekuensi']}"
    msg_str += '\n\n'
    msg_str += f"<b>Non Reg Volume</b>: {row['Non Regular Volume']:,.0f}"\
        " Lot"
    msg_str += '\n'
    msg_str += f"<b>Non Reg Value</b>: Rp{row['Non Regular Value']:,}"
    msg_str += '\n'
    msg_str += f"<b>Non Reg Frekuensi</b>: {row['Non Regular Frequency']:,}"
    msg_str += '\n'
    msg_str += f"<b>Non Reg Value Ratio</b>: {row['value_ratio']:,.1f}x"

    return msg_str


async def send_non_reg_message(row, bot, TARGET_CHAT_ID):
    # Store open file handles to prevent premature closing
    file_handles = []
    media_group = []

    message_str = generate_non_reg_str(row)

    try:
        for idx, file_path in enumerate(row['ss_directory']):
            # Step 1: Validate absolute path
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                print(f"🚫 File not found: {abs_path}")
                continue

            # Step 2: Normalize path (critical for Windows)
            abs_path = abs_path.replace("\\", "/")  # Force forward slashes

            # Step 3: Open file and retain handle
            file = open(abs_path, "rb")
            file_handles.append(file)  # Keep track of open files

            # Step 4: Create media with HTML caption parsing
            media = InputMediaPhoto(
                media=InputFile(file, filename=os.path.basename(abs_path),
                                attach=True),
                caption=message_str if idx == 0 else None,
                parse_mode='HTML' if idx == 0 else None
            )
            media_group.append(media)
            print(f"✅ Added {abs_path} to media group")

        # Step 5: Send media group (await inside async function)
        await bot.send_media_group(chat_id=TARGET_CHAT_ID, media=media_group)
        print("Media group sent successfully!")

    except BadRequest as e:
        print(f"💥 Telegram API Error: {e.message}")
        print("Debug Checklist:")
        print("1. File paths: ",
              [os.path.abspath(p) for p in row['ss_directory']])
        print("2. File sizes: ",
              [f"{os.path.getsize(p)/1e6:.2f} MB"
               for p in row['ss_directory']])

    finally:
        # Step 6: Cleanup - close all files
        for f in file_handles:
            f.close()


def generate_order_book_summary_str(df, type):
    if type == '5000':
        summary_str = f'<b>{df.date.unique()[0]}'\
            ' - TOP MIN 5000 LOT FILTERED</b>'
    if type == '1000':
        summary_str = f'<b>{df.date.unique()[0]}'\
            ' - TOP MIN 1000 LOT PRICE > 1000 FILTERED</b>'

    summary_str += '\n\n'
    all_stock = df.symbol.to_list()
    summary_str += ', '.join(all_stock)

    return summary_str


async def send_order_book_summary_message(df, bot, type, TARGET_CHAT_ID):
    # Store open file handles to prevent premature closing
    msg_str = generate_order_book_summary_str(df, type)
    try:
        await bot.send_message(chat_id=TARGET_CHAT_ID,
                               text=msg_str,
                               parse_mode='HTML')
        print("Media group sent successfully!")

    except Exception as e:
        print(f"💥 Telegram API Error: {e.message}")


def generate_orderbook_str(row):
    msg_str = f"<a href = '{row['link']}'>{row['symbol']}</a>"
    msg_str += '\n\n'
    msg_str += f"<b>Price</b>: {row['price']} ({row['change']})"
    msg_str += '\n'
    msg_str += f"<b>Total Count</b>: {row['total_count']}"
    msg_str += '\n'
    msg_str += f"<b>Total Lot</b>: {row['total_lot']:,.0f} Lot"
    msg_str += '\n'
    msg_str += f"<b>Total Value</b>: Rp{row['total_value']:,.0f} Ribu"
    msg_str += '\n\n'
    msg_str += f"<b>Buy Count</b>: {row['buy_count']}"
    msg_str += '\n'
    msg_str += f"<b>Sell Count</b>: {row['sell_count']}"
    msg_str += '\n\n'
    msg_str += f"<b>Buy Lot</b>: {row['buy_lot']:,.0f} Lot"
    msg_str += '\n'
    msg_str += f"<b>Sell Lot</b>: {row['sell_lot']:,.0f} Lot"
    msg_str += '\n\n'
    msg_str += f"<b>Buy Value</b>: Rp{row['buy_value']:,.0f} Ribu"
    msg_str += '\n'
    msg_str += f"<b>Sell Value</b>: Rp{row['sell_value']:,.0f} Ribu"

    return msg_str


async def send_orderbook_message(row, bot, TARGET_CHAT_ID):
    # Store open file handles to prevent premature closing
    file_handles = []
    media_group = []

    message_str = generate_orderbook_str(row)

    try:
        for idx, file_path in enumerate(row['ss_directory']):
            # Step 1: Validate absolute path
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                print(f"🚫 File not found: {abs_path}")
                continue

            # Step 2: Normalize path (critical for Windows)
            abs_path = abs_path.replace("\\", "/")  # Force forward slashes

            # Step 3: Open file and retain handle
            file = open(abs_path, "rb")
            file_handles.append(file)  # Keep track of open files

            # Step 4: Create media with HTML caption parsing
            media = InputMediaPhoto(
                media=InputFile(file, filename=os.path.basename(abs_path),
                                attach=True),
                caption=message_str if idx == 0 else None,
                parse_mode='HTML' if idx == 0 else None
            )
            media_group.append(media)
            print(f"✅ Added {abs_path} to media group")

        # Step 5: Send media group (await inside async function)
        await bot.send_media_group(chat_id=TARGET_CHAT_ID, media=media_group, write_timeout=35)
        print("Media group sent successfully!")

    except Exception as e:
        print(f"💥 Telegram API Error: {e.message}")
        print("Debug Checklist:")
        print("1. File paths: ",
              [os.path.abspath(p) for p in row['ss_directory']])
        print("2. File sizes: ",
              [f"{os.path.getsize(p)/1e6:.2f} MB"
               for p in row['ss_directory']])

    finally:
        # Step 6: Cleanup - close all files
        for f in file_handles:
            f.close()


async def send_all_orderbook_messages(df, bot, TARGET_CHAT_ID):
    for index, row in df.iterrows():
        try:
            print(f"Processing {type} row {index}...")
            await send_orderbook_message(
                row=row,
                bot=bot,
                TARGET_CHAT_ID=TARGET_CHAT_ID
            )
            await asyncio.sleep(1)  # Add delay between messages
        except Exception as e:
            print(f"❌ Failed for {type} row {index}: {e}")
