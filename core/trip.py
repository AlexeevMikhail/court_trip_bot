from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.database import is_registered, save_trip_start, adjust_to_work_hours
from datetime import datetime
import sqlite3

# Порядок важен — используем обычный словарь (Python 3.7+ сохраняет порядок)
ORGANIZATIONS = {
    'vidnoye': "Видновский городской суд",
    'domodedovo': "Домодедовский городской суд",
    'requests': "Иные запросы",
    'kuzminsky': "Кузьминский районный суд",
    'kassatsionny2': "Второй кассационный суд общей юрисдикции",
    'lefortovsky': "Лефортовский районный суд",
    'lyuberetsky': "Люберецкий городской суд",
    'lyublinsky': "Люблинский районный суд",
    'meshchansky': "Мещанский районный суд",
    'msk_city': "Московский городской суд",
    'justice_peace': "Мировые судьи (судебный участок)",
    'nagatinsky': "Нагатинский районный суд",
    'perovsky': "Перовский районный суд",
    'post': "Почта России",
    'rosreestr': "Росреестр",
    'shcherbinsky': "Щербинский районный суд",
    'tverskoy': "Тверской районный суд",
    'chertanovsky': "Чертановский районный суд",
    'cheremushkinsky': "Черемушкинский районный суд",
    'gibdd': "ГИБДД",
    'other': "Другая организация (указать)"
}

async def start_trip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_registered(user_id):
        await update.message.reply_text(
            "❌ Вы не зарегистрированы!\n"
            "Отправьте команду: `/register Иванов Иван`",
            parse_mode="Markdown"
        )
        return

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"org_{org_id}")]
        for org_id, name in ORGANIZATIONS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🚗 *Куда вы отправляетесь?*\n"
        "Пожалуйста, выберите организацию ниже:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_custom_org_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    custom_org = update.message.text.strip()

    if not custom_org:
        await update.message.reply_text("❌ Название организации не может быть пустым.")
        return

    if not is_registered(user_id):
        await update.message.reply_text("❌ Вы не зарегистрированы.")
        return

    success = save_trip_start(user_id, "other", custom_org)
    time_now = datetime.now().strftime("%H:%M")

    if success:
        await update.message.reply_text(
            f"🚀 Поездка в *{custom_org}* начата в *{time_now}*\nХорошей дороги! 🚗",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Не удалось начать поездку. Возможно, вы уже в пути.")

async def end_trip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = adjust_to_work_hours(datetime.now())

    conn = sqlite3.connect('court_tracking.db')
    cursor = conn.cursor()

    cursor.execute('''
    UPDATE trips 
    SET end_datetime = ?, status = 'completed'
    WHERE user_id = ? AND status = 'in_progress'
    ''', (now, user_id))

    if cursor.rowcount > 0:
        await update.message.reply_text(
            f"🏁 Вы успешно вернулись в офис!\nПоездка завершена в *{now.strftime('%H:%M')}*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ *У вас нет активной поездки*",
            parse_mode="Markdown"
        )

    conn.commit()
    conn.close()

async def handle_trip_save(update: Update, context, org_id: str, org_name: str):
    user_id = update.effective_user.id
    success = save_trip_start(user_id, org_id, org_name)
    time_now = datetime.now().strftime('%H:%M')

    if success:
        await update.callback_query.edit_message_text(
            f"🚌 Поездка в *{org_name}* начата в *{time_now}*\nХорошей дороги! 🚗",
            parse_mode="Markdown"
        )
    else:
        await update.callback_query.edit_message_text(
            "❌ *Не удалось начать поездку.*\nВозможно, вы уже в пути.",
            parse_mode="Markdown"
        )
