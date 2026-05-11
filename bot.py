import asyncio
import gspread
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ========== НАСТРОЙКИ (ТОЛЬКО ТОКЕН) ==========
TELEGRAM_TOKEN = '8393444744:AAH5NEZsWPRf4oSfyPKQF7lXrXUPQ0_BoNc'  # Ваш токен
SPREADSHEET_ID = '1GCOdl7SPHMb-mvQn411n7GbavOmynNqH6B6Bc7h5yEk'
GROUP_CHAT_ID = -1003594974106
# =============================================

# --- Подключение к Google Sheets (сервисный аккаунт) ---
gc = gspread.service_account(filename='service_account.json')
sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("УЧЁТ ВРЕМЕНИ")

# --- Дополнительное подключение для работы с цветом (через Google Sheets API v4) ---
creds = service_account.Credentials.from_service_account_file('service_account.json')
service = build('sheets', 'v4', credentials=creds)

# --- Бот ---
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

def set_cell_green(sheet_id, row, col):
    """Устанавливает зелёный фон для ячейки (использует API)"""
    requests = [{
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': row - 1,
                'endRowIndex': row,
                'startColumnIndex': col - 1,
                'endColumnIndex': col
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': {
                        'red': 0.7,
                        'green': 0.8,
                        'blue': 0.6
                    }
                }
            },
            'fields': 'userEnteredFormat.backgroundColor'
        }
    }]
    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': requests}).execute()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("✅ Бот готов. Отправляйте фото в общий чат — я запишу время и закрашу ячейку зелёным.")

@dp.message(lambda message: message.photo)
async def photo_handler(message: types.Message):
    if message.chat.id != GROUP_CHAT_ID:
        return

    user_id = message.from_user.id
    current_time = datetime.now().strftime("%H:%M:%S")
    today_day = datetime.now().day

    try:
        # 1. Поиск строки с user_id (столбец A)
        user_cell = sheet.find(str(user_id))
        if not user_cell:
            await message.reply(f"❌ {message.from_user.first_name}, ваш ID не найден в таблице.")
            return

        # 2. Поиск столбца с сегодняшним числом (в строке 13)
        day_cell = sheet.find(str(today_day), in_row=13)
        if not day_cell:
            await message.reply(f"❌ Число {today_day} не найдено в 13-й строке (даты).")
            return

        # 3. Запись времени в нужную ячейку
        target_row = user_cell.row   # строка сотрудника (14..18)
        target_col = day_cell.col    # столбец с числом (C, D, E...)
        sheet.update_cell(target_row, target_col, current_time)

        # 4. Закрашиваем ячейку зелёным
        # Сначала узнаём внутренний ID листа (обычно 0)
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheet_id = sheet_metadata['sheets'][0]['properties']['sheetId']
        set_cell_green(sheet_id, target_row, target_col)

        await message.reply(f"✅ {message.from_user.first_name}, приход в {current_time} записан, ячейка закрашена.")

    except Exception as e:
        print(f"Ошибка: {e}")
        await message.reply("⚠️ Ошибка записи. Сообщите администратору.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
