import os
from telegram import InputMediaPhoto, InputFile
from telegram.error import BadRequest


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

    message_str = generate_high_level_summary_str(df, type)

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
        print("1. File paths: ", [os.path.abspath(p) for p in files_path])
        print("2. File sizes: ",
              [f"{os.path.getsize(p)/1e6:.2f} MB" for p in files_path])

    finally:
        # Step 6: Cleanup - close all files
        for f in file_handles:
            f.close()


def generate_daily_summary_str(row, type):
    message_str = f"<a href = '{row['link']}'>{row['symbol']}</a>"
    message_str += '\n\n'
    message_str += f"<b>Price</b>: {row['price']}"
    message_str += '\n'
    if type == 'daily':
        message_str += f'<b>1d Price Change</b>: {row["%1d"]}%'
    else:
        message_str += f'<b>3d Price Change</b>: {row["%3d"]}%'
        message_str += '\n'
        message_str += f'<b>5d Price Change</b>: {row["%5d"]}%'
        message_str += '\n'
        message_str += f'<b>10d Price Change</b>: {row["%10d"]}%'
        message_str += '\n'
        message_str += f'<b>20d Price Change</b>: {row["%20d"]}%'
    message_str += '\n'
    message_str += f'<b>pinky</b>: {row["pinky"]}'
    message_str += '\n'
    message_str += f'<b>crossing</b>: {row["crossing"]}'
    message_str += '\n'
    message_str += f'<b>unusual</b>: {row["unusual"]}'
    message_str += '\n'
    message_str += f'<b>likuid</b>: {row["likuid"]}'
    message_str += '\n\n'
    message_str += f"<b>{row['method'].upper()}</b>"
    message_str += '\n'
    if type == 'daily':
        message_str += f"<b>d-0</b>: {row['dn-0']}%"
        message_str += '\n'
        message_str += f"<b>d-1</b>: {row['dn-1']}%"
        message_str += '\n'
        message_str += f"<b>d-2</b>: {row['dn-2']}%"
        message_str += '\n'
        message_str += f"<b>d-3</b>: {row['dn-3']}%"
        message_str += '\n'
        message_str += f"<b>d-4</b>: {row['dn-4']}%"
        message_str += '\n\n'
        message_str += f"<b>w-1</b>: {row['wn-1']}%"
        message_str += '\n'
        message_str += f"<b>w-2</b>: {row['wn-2']}%"
        message_str += '\n'
        message_str += f"<b>w-3</b>: {row['wn-3']}%"
        message_str += '\n'
        message_str += f"<b>w-4</b>: {row['wn-4']}%"
    else:
        message_str += f"<b>cn-3</b>: {row['cn-3']}%"
        message_str += '\n'
        message_str += f"<b>cn-5</b>: {row['cn-5']}%"
        message_str += '\n'
        message_str += f"<b>cn-10</b>: {row['cn-10']}%"
        message_str += '\n'
        message_str += f"<b>cn-20</b>: {row['cn-20']}%"
        message_str += '\n'
    return message_str


# Define as an async function
async def send_daily_message(row, bot, type, TARGET_CHAT_ID):
    # Store open file handles to prevent premature closing
    file_handles = []
    media_group = []

    message_str = generate_daily_summary_str(row, type)

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
