# index.py - With Advanced Stock Management
import os
import sqlite3
import json
import time
from datetime import datetime
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import zipfile

# ======================= CONFIGURATION =======================
BOT_TOKEN = "8571008347:AAGqbmrpSrhvBEL9dOypOqLhhJh0YIM1q0Q"
ADMIN_ID = 6986785327  # তোমার User ID
SUPPORT_USERNAME = "@HANIF11ss"
BINANCE_ID = "1139934779"
USDT_ADDRESS = "0xca0b6e096126ccbf5780bc6d65772ad6395d1fe6"

# ======================= PRICES (JSON File Based) =======================
PRICES_FILE = "prices.json"

def load_prices():
    if os.path.exists(PRICES_FILE):
        with open(PRICES_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default prices
        prices = {
            "two_step": {
                "0+": 3.0,
                "1-9+": 3.5,
                "10+": 9.0,
                "50+": 14.0,
                "100+": 20.0,
                "300+": 23.0,
                "500+": 35.0,
                "500+Verified": 40.0
            },
            "hotmail": {
                "0+": 3.5,
                "1-9+": 4.0,
                "10+": 10.0,
                "50+": 15.0,
                "100+": 20.0,
                "300+": 24.0,
                "500+": 35.0,
                "500+Verified": 40.0
            }
        }
        save_prices(prices)
        return prices

def save_prices(prices):
    with open(PRICES_FILE, 'w') as f:
        json.dump(prices, f, indent=4)

PRICES = load_prices()

# ======================= DATABASE =======================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                total_spent REAL DEFAULT 0.0,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_type TEXT,
                connection_type TEXT,
                price REAL,
                account_details TEXT,
                status TEXT DEFAULT 'completed',
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                status TEXT DEFAULT 'pending',
                proof TEXT,
                trx_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock (
                account_type TEXT,
                connection_type TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (account_type, connection_type)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS direct_delivery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_type TEXT,
                connection_type TEXT,
                account_details TEXT,
                delivered_by INTEGER,
                delivery_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def add_user(self, user_id, username):
        try:
            self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
            self.conn.commit()
        except:
            pass
    
    def get_balance(self, user_id):
        self.cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0.0
    
    def update_balance(self, user_id, amount):
        self.cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def add_order(self, user_id, account_type, connection_type, price, account_details):
        self.cursor.execute('''
            INSERT INTO orders (user_id, account_type, connection_type, price, account_details)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, account_type, connection_type, price, account_details))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_direct_delivery(self, user_id, account_type, connection_type, account_details, delivered_by):
        self.cursor.execute('''
            INSERT INTO direct_delivery (user_id, account_type, connection_type, account_details, delivered_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, account_type, connection_type, account_details, delivered_by))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_direct_deliveries(self, limit=50):
        self.cursor.execute('''
            SELECT dd.*, u.username 
            FROM direct_delivery dd
            LEFT JOIN users u ON dd.user_id = u.user_id
            ORDER BY dd.delivery_time DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def update_stock(self, account_type, connection_type, count):
        self.cursor.execute('''
            INSERT OR REPLACE INTO stock (account_type, connection_type, count)
            VALUES (?, ?, ?)
        ''', (account_type, connection_type, count))
        self.conn.commit()
    
    def get_stock(self, account_type, connection_type):
        self.cursor.execute('SELECT count FROM stock WHERE account_type = ? AND connection_type = ?', 
                          (account_type, connection_type))
        result = self.cursor.fetchone()
        return result[0] if result else 0
    
    def get_all_stock(self):
        self.cursor.execute('SELECT * FROM stock ORDER BY account_type, connection_type')
        return self.cursor.fetchall()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id, username, balance FROM users ORDER BY join_date DESC')
        return self.cursor.fetchall()
    
    def clear_stock(self, account_type, connection_type):
        self.cursor.execute('UPDATE stock SET count = 0 WHERE account_type = ? AND connection_type = ?', 
                          (account_type, connection_type))
        self.conn.commit()

# ======================= BOT INITIALIZATION =======================
bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

# ======================= URL FIX FUNCTION =======================
def fix_url_format(url):
    """Fix URL format if it has issues"""
    if not url:
        return url
    
    # Remove any leading/trailing spaces
    url = url.strip()
    
    # Remove "https" or "http" if they appear in the middle
    if " https" in url:
        url = url.replace(" https", "https")
    if " http" in url:
        url = url.replace(" http", "http")
    
    # If URL starts with "https " or "http ", remove the space
    if url.startswith("https "):
        url = url.replace("https ", "https://", 1)
    elif url.startswith("http "):
        url = url.replace("http ", "http://", 1)
    
    # If URL starts with "//", add "https:"
    if url.startswith("//"):
        url = "https:" + url
    
    # Ensure URL has proper protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    return url

# ======================= KEYBOARDS =======================
def main_menu_keyboard(is_admin=False):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("🛒 Buy LinkedIn Accounts"),
        KeyboardButton("💰 Check My Balance")
    )
    keyboard.add(
        KeyboardButton("💳 Add Balance"),
        KeyboardButton("📞 Support")
    )
    if is_admin:
        keyboard.add(KeyboardButton("👑 Admin Panel"))
    return keyboard

def admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 Statistics"),
        KeyboardButton("📦 Stock Management")
    )
    keyboard.add(
        KeyboardButton("👥 Users List"),
        KeyboardButton("💰 Price Management")
    )
    keyboard.add(
        KeyboardButton("🚚 Direct Delivery"),
        KeyboardButton("📥 Add Stock")
    )
    keyboard.add(
        KeyboardButton("🗑️ Clear Stock"),
        KeyboardButton("📤 Export Stock")
    )
    keyboard.add(KeyboardButton("⬅️ Main Menu"))
    return keyboard

def price_management_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔐 Two-Step Prices", callback_data="price_two_step"),
        InlineKeyboardButton("📧 Hotmail Prices", callback_data="price_hotmail")
    )
    keyboard.add(InlineKeyboardButton("📊 View All Prices", callback_data="view_prices"))
    return keyboard

def account_type_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔐 LinkedIn Two-Step Authentication", callback_data="type_two_step"),
        InlineKeyboardButton("📧 LinkedIn Hotmail/Outlook Login", callback_data="type_hotmail")
    )
    return keyboard

def connection_keyboard(account_type):
    keyboard = InlineKeyboardMarkup(row_width=2)
    prices = PRICES[account_type]
    
    for conn_type, price in prices.items():
        keyboard.add(
            InlineKeyboardButton(
                f"{conn_type} - ${price}", 
                callback_data=f"buy_{account_type}_{conn_type}"
            )
        )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_types"))
    return keyboard

def stock_management_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Add Single Account", callback_data="add_single_stock"),
        InlineKeyboardButton("📦 Add Bulk Accounts", callback_data="add_bulk_stock")
    )
    keyboard.add(
        InlineKeyboardButton("📝 Manual Add", callback_data="manual_add_stock"),
        InlineKeyboardButton("📋 View All Stock", callback_data="view_all_stock")
    )
    keyboard.add(
        InlineKeyboardButton("🗑️ Clear Stock", callback_data="clear_stock_menu"),
        InlineKeyboardButton("📤 Export Stock", callback_data="export_stock")
    )
    keyboard.add(InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin"))
    return keyboard

def stock_type_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔐 Two-Step", callback_data="stock_two_step"),
        InlineKeyboardButton("📧 Hotmail", callback_data="stock_hotmail")
    )
    return keyboard

def connection_selection_keyboard(account_type, is_bulk=False):
    keyboard = InlineKeyboardMarkup(row_width=2)
    for conn_type in PRICES[account_type].keys():
        prefix = "bulk_stock_" if is_bulk else "stock_"
        keyboard.add(
            InlineKeyboardButton(conn_type, callback_data=f"{prefix}{account_type}_{conn_type}")
        )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_stock"))
    return keyboard

# ======================= FOLDER & FILE MANAGEMENT =======================
def ensure_folders():
    folders = ["accounts/two_step_auth", "accounts/hotmail_outlook", "exports", "backups", "user_deliveries"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    conn_types = ["0+", "1-9+", "10+", "50+", "100+", "300+", "500+", "500+Verified"]
    
    for conn in conn_types:
        two_step_file = f"accounts/two_step_auth/{conn} Connection.txt"
        if not os.path.exists(two_step_file):
            open(two_step_file, 'w').close()
        
        hotmail_file = f"accounts/hotmail_outlook/{conn} Connection.txt"
        if not os.path.exists(hotmail_file):
            open(hotmail_file, 'w').close()

def get_account_from_file(account_type, connection_type):
    folder = "accounts/two_step_auth" if account_type == "two_step" else "accounts/hotmail_outlook"
    filename = f"{connection_type} Connection.txt"
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            accounts = [line.strip() for line in f if line.strip()]
        
        if accounts:
            # Get first account
            account_details = accounts[0]
            remaining_accounts = accounts[1:]
            
            # Update file
            with open(filepath, 'w', encoding='utf-8') as f:
                for acc in remaining_accounts:
                    f.write(acc + '\n')
            
            return account_details, len(remaining_accounts)
    
    return None, 0

def add_account_to_file(account_type, connection_type, account_details):
    folder = "accounts/two_step_auth" if account_type == "two_step" else "accounts/hotmail_outlook"
    filename = f"{connection_type} Connection.txt"
    filepath = os.path.join(folder, filename)
    
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(account_details + '\n')
    
    with open(filepath, 'r', encoding='utf-8') as f:
        count = len([line.strip() for line in f if line.strip()])
    
    return count

def get_all_accounts_from_file(account_type, connection_type):
    folder = "accounts/two_step_auth" if account_type == "two_step" else "accounts/hotmail_outlook"
    filename = f"{connection_type} Connection.txt"
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def export_stock_to_file(account_type, connection_type):
    folder = "accounts/two_step_auth" if account_type == "two_step" else "accounts/hotmail_outlook"
    filename = f"{connection_type} Connection.txt"
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        export_folder = "exports"
        if not os.path.exists(export_folder):
            os.makedirs(export_folder)
        
        export_filename = f"{account_type}_{connection_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        export_path = os.path.join(export_folder, export_filename)
        
        with open(filepath, 'r', encoding='utf-8') as source:
            with open(export_path, 'w', encoding='utf-8') as dest:
                dest.write(source.read())
        
        return export_path
    return None

def clear_stock_file(account_type, connection_type):
    folder = "accounts/two_step_auth" if account_type == "two_step" else "accounts/hotmail_outlook"
    filename = f"{connection_type} Connection.txt"
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        # Backup before clearing
        backup_folder = "backups"
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        
        backup_filename = f"backup_{account_type}_{connection_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        backup_path = os.path.join(backup_folder, backup_filename)
        
        with open(filepath, 'r', encoding='utf-8') as source:
            with open(backup_path, 'w', encoding='utf-8') as dest:
                dest.write(source.read())
        
        # Clear the file
        open(filepath, 'w').close()
        db.update_stock(account_type, connection_type, 0)
        return True
    return False

# ======================= HANDLERS =======================
@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    db.add_user(user_id, username)
    is_admin = (user_id == ADMIN_ID)
    
    welcome_msg = f"""👋 <b>Welcome to LinkedIn Accounts Bot!</b>

💰 <b>Your Balance:</b> ${db.get_balance(user_id):.2f}
👤 <b>Your User ID:</b> <code>{user_id}</code>

<b>Features:</b>
• Buy LinkedIn Accounts
• Bulk Orders (1-100)
• Secure Payments
• 24/7 Support
• Instant Delivery as .txt file (One-line format)

<b>Support:</b> {SUPPORT_USERNAME}"""
    
    bot.send_message(message.chat.id, welcome_msg, 
                    reply_markup=main_menu_keyboard(is_admin),
                    parse_mode="HTML")

@bot.message_handler(commands=['myid'])
def myid_command(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"👤 <b>Your User ID:</b> <code>{user_id}</code>", 
                    parse_mode="HTML")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👑 <b>Admin Panel</b>", 
                        reply_markup=admin_keyboard(), parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Access denied!")

# ======================= STOCK MANAGEMENT =======================
@bot.message_handler(func=lambda msg: msg.text == "📥 Add Stock")
def add_stock_menu(msg):
    if msg.from_user.id == ADMIN_ID:
        bot.send_message(msg.chat.id, "📥 <b>Stock Management</b>\n\nSelect option:", 
                        reply_markup=stock_management_keyboard(), parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

@bot.message_handler(func=lambda msg: msg.text == "📦 Stock Management")
def stock_management(msg):
    if msg.from_user.id == ADMIN_ID:
        stock = db.get_all_stock()
        
        if not stock:
            bot.send_message(msg.chat.id, "📭 No stock available!", 
                           reply_markup=stock_management_keyboard())
            return
        
        response = "📦 <b>Current Stock</b>\n\n"
        for item in stock:
            acc_type, conn_type, count = item
            acc_name = "Two-Step" if acc_type == "two_step" else "Hotmail"
            response += f"• {acc_name} - {conn_type}: {count} accounts\n"
        
        response += "\nSelect option below:"
        bot.send_message(msg.chat.id, response, 
                        reply_markup=stock_management_keyboard(), parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

@bot.callback_query_handler(func=lambda call: call.data == "add_bulk_stock")
def add_bulk_stock_start(call):
    bot.edit_message_text(
        "📦 <b>Add Bulk Accounts</b>\n\n"
        "Send multiple accounts in this format:\n"
        "<code>email:pass:linkedinpass:recovery:url</code>\n\n"
        "<b>Put each account on a new line:</b>\n"
        "<code>\n"
        "test1@gmail.com:pass123:linkedinpass:recovery1@gmail.com:url1\n"
        "test2@gmail.com:pass456:linkedinpass:recovery2@gmail.com:url2\n"
        "test3@gmail.com:pass789:linkedinpass:recovery3@gmail.com:url3\n"
        "</code>\n\n"
        "<b>First select account type:</b>",
        call.message.chat.id, call.message.message_id,
        reply_markup=stock_type_keyboard(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "stock_two_step")
def handle_stock_two_step(call):
    bot.edit_message_text(
        "📦 <b>Add Single Account – Two-Step</b>\n\nSelect connection type:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=connection_selection_keyboard("two_step", is_bulk=False),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "stock_hotmail")
def handle_stock_hotmail(call):
    bot.edit_message_text(
        "📦 <b>Add Single Account – Hotmail</b>\n\nSelect connection type:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=connection_selection_keyboard("hotmail", is_bulk=False),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('stock_') and not call.data.startswith('stock_two_step') and not call.data.startswith('stock_hotmail'))
def handle_stock_connection_selection(call):
    data = call.data.replace("stock_", "", 1)
    
    if data.startswith("two_step_"):
        account_type = "two_step"
        connection_type = data.replace("two_step_", "", 1)
    elif data.startswith("hotmail_"):
        account_type = "hotmail"
        connection_type = data.replace("hotmail_", "", 1)
    else:
        bot.answer_callback_query(call.id, "❌ Invalid stock type!")
        return
    
    msg = bot.edit_message_text(
        f"📝 <b>Add Single Account</b>\n\n"
        f"<b>Type:</b> {account_type}\n"
        f"<b>Connection:</b> {connection_type}\n\n"
        f"Send account details in ONE LINE format:\n\n"
        f"<b>For Two-Step:</b>\n"
        f"<code>email:mail_pass:linkedin_pass:2fa_code:url</code>\n\n"
        f"<b>For Hotmail:</b>\n"
        f"<code>email:mail_pass:linkedin_pass:recovery_email:url</code>\n\n"
        f"<b>Example (Two-Step):</b>\n"
        f"<code>leonardomorris1481i@gmail.com:%Date10.07%:CEZFD3U5VF64IPMWVKQMZQ5VNH75EUE3:2fa_code_here:https://www.linkedin.com/in/leonardo-morris-5a2898332/</code>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    
    bot.register_next_step_handler(
        msg,
        lambda m: process_single_stock(m, account_type, connection_type)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("bulk_stock_"))
def bulk_connection_select(call):
    _, account_type, connection_type = call.data.split("_", 2)
    
    msg = bot.edit_message_text(
        f"📦 <b>Bulk Add Accounts</b>\n\n"
        f"Type: {account_type}\n"
        f"Connection: {connection_type}\n\n"
        "Send multiple accounts (one per line):\n\n"
        f"<b>Format for {'Two-Step' if account_type == 'two_step' else 'Hotmail'}:</b>\n"
        f"<code>email:mail_pass:linkedin_pass:{'2fa_code' if account_type == 'two_step' else 'recovery_email'}:url</code>\n\n"
        f"<b>Example ({'Two-Step' if account_type == 'two_step' else 'Hotmail'}):</b>\n"
        f"<code>leonardomorris1481i@gmail.com:%Date10.07%:CEZFD3U5VF64IPMWVKQMZQ5VNH75EUE3:{'2fa_code_here' if account_type == 'two_step' else 'recovery@gmail.com'}:https://www.linkedin.com/in/leonardo-morris-5a2898332/</code>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML"
    )
    
    bot.register_next_step_handler(
        msg,
        lambda m: process_bulk_stock(m, account_type, connection_type)
    )

def process_single_stock(message, account_type, connection_type):
    try:
        account_details = message.text.strip()
        
        if not account_details:
            bot.send_message(message.chat.id, "❌ Empty account details!")
            return
        
        # Validate format - must have exactly 4 colons (5 parts)
        if account_details.count(':') != 4:
            bot.send_message(message.chat.id, 
                           f"❌ Invalid format! Must have exactly 5 parts separated by ':'\n\n"
                           f"<b>Correct Format for {'Two-Step' if account_type == 'two_step' else 'Hotmail'}:</b>\n"
                           f"<code>email:mail_pass:linkedin_pass:{'2fa_code' if account_type == 'two_step' else 'recovery_email'}:url</code>\n\n"
                           f"<b>Example:</b>\n"
                           f"<code>leonardomorris1481i@gmail.com:%Date10.07%:CEZFD3U5VF64IPMWVKQMZQ5VNH75EUE3:{'2fa_code_here' if account_type == 'two_step' else 'recovery@gmail.com'}:https://www.linkedin.com/in/leonardo-morris-5a2898332/</code>",
                           parse_mode="HTML")
            return
        
        # Add to file
        count = add_account_to_file(account_type, connection_type, account_details)
        db.update_stock(account_type, connection_type, count)
        
        response = f"""✅ <b>Account Added Successfully!</b>

🔐 <b>Type:</b> {account_type}
🔗 <b>Connection:</b> {connection_type}
📥 <b>Added:</b> 1 account
📦 <b>Total Stock:</b> {count} accounts

🔐 <b>Added Account:</b>
<code>{account_details}</code>"""
        
        bot.send_message(message.chat.id, response, parse_mode="HTML")
        
        # Show stock management options again
        bot.send_message(message.chat.id, "📥 <b>Stock Management</b>", 
                        reply_markup=stock_management_keyboard(), parse_mode="HTML")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def process_bulk_stock(message, account_type, connection_type):
    try:
        accounts_text = message.text.strip()
        if not accounts_text:
            bot.send_message(message.chat.id, "❌ Empty input!")
            return
        
        accounts = accounts_text.split('\n')
        added_count = 0
        failed_count = 0
        
        for account_line in accounts:
            account_line = account_line.strip()
            if not account_line:
                continue
                
            # Validate format - must have exactly 4 colons (5 parts)
            if account_line.count(':') != 4:
                bot.send_message(message.chat.id, 
                               f"❌ Skipping invalid format: {account_line[:50]}...\n"
                               f"Must have exactly 5 parts: email:mail_pass:linkedin_pass:{'2fa_code' if account_type == 'two_step' else 'recovery_email'}:url",
                               parse_mode="HTML")
                failed_count += 1
                continue
            
            # Add to file
            count = add_account_to_file(account_type, connection_type, account_line)
            db.update_stock(account_type, connection_type, count)
            added_count += 1
        
        total_count = db.get_stock(account_type, connection_type)
        
        response = f"""✅ <b>Bulk Accounts Added Successfully!</b>

🔐 <b>Type:</b> {account_type}
🔗 <b>Connection:</b> {connection_type}
📥 <b>Successfully Added:</b> {added_count} accounts
❌ <b>Failed:</b> {failed_count} accounts
📦 <b>Total Stock:</b> {total_count} accounts"""
        
        bot.send_message(message.chat.id, response, parse_mode="HTML")
        
        # Show stock management options again
        bot.send_message(message.chat.id, "📥 <b>Stock Management</b>", 
                        reply_markup=stock_management_keyboard(), parse_mode="HTML")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "add_single_stock")
def add_single_stock_menu(call):
    bot.edit_message_text(
        "➕ <b>Add Single Account</b>\n\nSelect account type:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=stock_type_keyboard(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "view_all_stock")
def view_all_stock(call):
    stock = db.get_all_stock()
    
    if not stock:
        bot.edit_message_text("📭 No stock available!", 
                            call.message.chat.id, call.message.message_id,
                            parse_mode="HTML")
        return
    
    response = "📦 <b>Complete Stock Details</b>\n\n"
    
    # Group by account type
    two_step_stock = [s for s in stock if s[0] == "two_step"]
    hotmail_stock = [s for s in stock if s[0] == "hotmail"]
    
    if two_step_stock:
        response += "🔐 <b>Two-Step Accounts:</b>\n"
        for item in two_step_stock:
            _, conn_type, count = item
            response += f"• {conn_type}: {count} accounts\n"
        
        # Calculate total
        two_step_total = sum(item[2] for item in two_step_stock)
        response += f"📊 <b>Total:</b> {two_step_total} accounts\n\n"
    
    if hotmail_stock:
        response += "📧 <b>Hotmail Accounts:</b>\n"
        for item in hotmail_stock:
            _, conn_type, count = item
            response += f"• {conn_type}: {count} accounts\n"
        
        # Calculate total
        hotmail_total = sum(item[2] for item in hotmail_stock)
        response += f"📊 <b>Total:</b> {hotmail_total} accounts\n\n"
    
    # Overall total
    overall_total = sum(item[2] for item in stock)
    response += f"📈 <b>Overall Total Stock:</b> {overall_total} accounts"
    
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id,
                         parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "clear_stock_menu")
def clear_stock_menu(call):
    bot.edit_message_text(
        "🗑️ <b>Clear Stock</b>\n\n"
        "⚠️ <b>Warning:</b> This will remove ALL accounts from stock!\n\n"
        "Select what to clear:",
        call.message.chat.id, call.message.message_id,
        reply_markup=clear_stock_options_keyboard(),
        parse_mode="HTML"
    )

def clear_stock_options_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔐 Clear Two-Step", callback_data="clear_two_step"),
        InlineKeyboardButton("📧 Clear Hotmail", callback_data="clear_hotmail")
    )
    keyboard.add(
        InlineKeyboardButton("🗑️ Clear All Stock", callback_data="clear_all_stock"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_stock")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith('clear_') and not call.data.startswith('clear_two_step_') and not call.data.startswith('clear_hotmail_'))
def handle_clear_stock(call):
    if call.data == "clear_two_step":
        msg = bot.edit_message_text(
            "🗑️ <b>Clear Two-Step Stock</b>\n\n"
            "Select connection type to clear:",
            call.message.chat.id, call.message.message_id,
            reply_markup=clear_connection_keyboard("two_step"),
            parse_mode="HTML"
        )
    
    elif call.data == "clear_hotmail":
        msg = bot.edit_message_text(
            "🗑️ <b>Clear Hotmail Stock</b>\n\n"
            "Select connection type to clear:",
            call.message.chat.id, call.message.message_id,
            reply_markup=clear_connection_keyboard("hotmail"),
            parse_mode="HTML"
        )
    
    elif call.data == "clear_all_stock":
        msg = bot.edit_message_text(
            "⚠️ <b>Clear ALL Stock</b>\n\n"
            "Are you sure? This will remove ALL accounts from ALL categories!\n\n"
            "Type 'YES' to confirm:",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, confirm_clear_all_stock)

def clear_connection_keyboard(account_type):
    keyboard = InlineKeyboardMarkup(row_width=2)
    for conn_type in PRICES[account_type].keys():
        keyboard.add(
            InlineKeyboardButton(conn_type, callback_data=f"clear_{account_type}_{conn_type}")
        )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="clear_stock_menu"))
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith('clear_two_step_') or call.data.startswith('clear_hotmail_'))
def clear_specific_stock(call):
    parts = call.data.split('_')
    account_type = parts[1]  # two_step or hotmail
    connection_type = parts[2]  # 0+, 10+, etc.
    
    # Get current count
    current_count = db.get_stock(account_type, connection_type)
    
    msg = bot.edit_message_text(
        f"🗑️ <b>Clear Stock</b>\n\n"
        f"<b>Type:</b> {account_type}\n"
        f"<b>Connection:</b> {connection_type}\n"
        f"<b>Current Stock:</b> {current_count} accounts\n\n"
        f"⚠️ <b>This action cannot be undone!</b>\n\n"
        f"Type 'YES' to confirm:",
        call.message.chat.id, call.message.message_id,
        parse_mode="HTML"
    )
    
    bot.register_next_step_handler(msg, lambda m: confirm_clear_stock(m, account_type, connection_type))

def confirm_clear_stock(message, account_type, connection_type):
    if message.text.upper() == "YES":
        # Clear the stock
        if clear_stock_file(account_type, connection_type):
            response = f"""✅ <b>Stock Cleared Successfully!</b>

🔐 <b>Type:</b> {account_type}
🔗 <b>Connection:</b> {connection_type}
🗑️ <b>Cleared:</b> All accounts removed
📦 <b>Current Stock:</b> 0 accounts

⚠️ A backup has been saved in the 'backups' folder."""
            
            bot.send_message(message.chat.id, response, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ Failed to clear stock!", parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Clear operation cancelled!")
    
    # Return to stock management
    bot.send_message(message.chat.id, "📥 <b>Stock Management</b>", 
                    reply_markup=stock_management_keyboard(), parse_mode="HTML")

def confirm_clear_all_stock(message):
    if message.text.upper() == "YES":
        # Clear all stock files
        cleared_count = 0
        
        # Clear two_step files
        for conn_type in PRICES["two_step"].keys():
            if clear_stock_file("two_step", conn_type):
                cleared_count += 1
        
        # Clear hotmail files
        for conn_type in PRICES["hotmail"].keys():
            if clear_stock_file("hotmail", conn_type):
                cleared_count += 1
        
        response = f"""✅ <b>All Stock Cleared Successfully!</b>

🗑️ <b>Cleared:</b> {cleared_count} categories
📦 <b>Current Stock:</b> 0 accounts total

⚠️ Backups have been saved in the 'backups' folder."""
        
        bot.send_message(message.chat.id, response, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Clear operation cancelled!")
    
    # Return to stock management
    bot.send_message(message.chat.id, "📥 <b>Stock Management</b>", 
                    reply_markup=stock_management_keyboard(), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "export_stock")
def export_stock_menu(call):
    bot.edit_message_text(
        "📤 <b>Export Stock</b>\n\n"
        "Select what to export:",
        call.message.chat.id, call.message.message_id,
        reply_markup=export_options_keyboard(),
        parse_mode="HTML"
    )

def export_options_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔐 Export Two-Step", callback_data="export_two_step"),
        InlineKeyboardButton("📧 Export Hotmail", callback_data="export_hotmail")
    )
    keyboard.add(
        InlineKeyboardButton("📤 Export All", callback_data="export_all"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_stock")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith('export_') and not call.data.startswith('export_two_step_') and not call.data.startswith('export_hotmail_'))
def handle_export_stock(call):
    if call.data == "export_two_step":
        bot.edit_message_text(
            "📤 <b>Export Two-Step Stock</b>\n\n"
            "Select connection type:",
            call.message.chat.id, call.message.message_id,
            reply_markup=export_connection_keyboard("two_step"),
            parse_mode="HTML"
        )
    
    elif call.data == "export_hotmail":
        bot.edit_message_text(
            "📤 <b>Export Hotmail Stock</b>\n\n"
            "Select connection type:",
            call.message.chat.id, call.message.message_id,
            reply_markup=export_connection_keyboard("hotmail"),
            parse_mode="HTML"
        )
    
    elif call.data == "export_all":
        # Export all stock
        export_all_stock(call.message.chat.id, call.message.message_id)

def export_connection_keyboard(account_type):
    keyboard = InlineKeyboardMarkup(row_width=2)
    for conn_type in PRICES[account_type].keys():
        count = db.get_stock(account_type, conn_type)
        if count > 0:
            keyboard.add(
                InlineKeyboardButton(f"{conn_type} ({count})", callback_data=f"export_{account_type}_{conn_type}")
            )
    keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="export_stock"))
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith('export_two_step_') or call.data.startswith('export_hotmail_'))
def export_specific_stock(call):
    parts = call.data.split('_')
    account_type = parts[1]  # two_step or hotmail
    connection_type = parts[2]  # 0+, 10+, etc.
    
    # Export the stock
    export_path = export_stock_to_file(account_type, connection_type)
    
    if export_path and os.path.exists(export_path):
        # Get count
        count = db.get_stock(account_type, connection_type)
        
        try:
            with open(export_path, 'rb') as file:
                bot.send_document(
                    call.message.chat.id,
                    file,
                    caption=f"📤 <b>Exported Stock</b>\n\n"
                           f"🔐 <b>Type:</b> {account_type}\n"
                           f"🔗 <b>Connection:</b> {connection_type}\n"
                           f"📦 <b>Total Accounts:</b> {count}\n"
                           f"📅 <b>Exported:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode="HTML"
                )
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Error exporting: {str(e)}")
    else:
        bot.send_message(call.message.chat.id, f"❌ No stock found for {account_type} - {connection_type}")

def export_all_stock(chat_id, message_id):
    try:
        # Create a zip file with all stock
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"exports/all_stock_{timestamp}.zip"
        
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            # Add two_step files
            for conn_type in PRICES["two_step"].keys():
                folder = "accounts/two_step_auth"
                filename = f"{conn_type} Connection.txt"
                filepath = os.path.join(folder, filename)
                
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    zipf.write(filepath, f"two_step/{filename}")
            
            # Add hotmail files
            for conn_type in PRICES["hotmail"].keys():
                folder = "accounts/hotmail_outlook"
                filename = f"{conn_type} Connection.txt"
                filepath = os.path.join(folder, filename)
                
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    zipf.write(filepath, f"hotmail/{filename}")
        
        # Calculate totals
        stock = db.get_all_stock()
        total_accounts = sum(item[2] for item in stock)
        
        with open(zip_filename, 'rb') as file:
            bot.send_document(
                chat_id,
                file,
                caption=f"📤 <b>All Stock Exported</b>\n\n"
                       f"📦 <b>Total Categories:</b> {len(stock)}\n"
                       f"👤 <b>Total Accounts:</b> {total_accounts}\n"
                       f"📅 <b>Exported:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="HTML"
            )
        
        # Clean up
        os.remove(zip_filename)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error exporting all stock: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_stock")
def back_to_stock_management(call):
    bot.edit_message_text(
        "📥 <b>Stock Management</b>\n\nSelect option:",
        call.message.chat.id, call.message.message_id,
        reply_markup=stock_management_keyboard(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin")
def back_to_admin_panel(call):
    bot.edit_message_text(
        "👑 <b>Admin Panel</b>",
        call.message.chat.id, call.message.message_id,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "manual_add_stock")
def manual_add_stock(call):
    msg = bot.edit_message_text(
        "📝 <b>Manual Add Stock</b>\n\n"
        "Send in format:\n"
        "<code>[account_type] [connection_type] [quantity] [account_details]</code>\n\n"
        "<b>Example:</b>\n"
        "<code>two_step 10+ 5 leonardomorris1481i@gmail.com:%Date10.07%:CEZFD3U5VF64IPMWVKQMZQ5VNH75EUE3:2fa_code_here:https://www.linkedin.com/in/leonardo-morris-5a2898332/</code>",
        call.message.chat.id, call.message.message_id,
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_manual_stock)

def process_manual_stock(message):
    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) == 4:
            account_type = parts[0]
            connection_type = parts[1]
            quantity = int(parts[2])
            account_details = parts[3]
            
            if account_type not in ["two_step", "hotmail"]:
                bot.send_message(message.chat.id, "❌ Invalid account type! Use 'two_step' or 'hotmail'", parse_mode="HTML")
                return
            
            if quantity < 1:
                bot.send_message(message.chat.id, "❌ Quantity must be at least 1!", parse_mode="HTML")
                return
            
            # Add multiple accounts
            total_count = 0
            for i in range(quantity):
                count = add_account_to_file(account_type, connection_type, account_details)
                db.update_stock(account_type, connection_type, count)
                total_count = count
            
            response = f"""✅ <b>Stock added successfully!</b>

📋 <b>Type:</b> {account_type}
🔗 <b>Connection:</b> {connection_type}
📥 <b>Added:</b> {quantity} accounts
📦 <b>Total Stock:</b> {total_count} accounts

🔐 <b>Account Details:</b>
<code>{account_details}</code>"""
            
            bot.send_message(message.chat.id, response, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ Invalid format! Use: [type] [conn] [qty] [details]", parse_mode="HTML")
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        bot.send_message(message.chat.id, error_msg, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "🗑️ Clear Stock")
def clear_stock_button(msg):
    if msg.from_user.id == ADMIN_ID:
        bot.send_message(msg.chat.id, "🗑️ <b>Clear Stock</b>", 
                        reply_markup=clear_stock_options_keyboard(), parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

@bot.message_handler(func=lambda msg: msg.text == "📤 Export Stock")
def export_stock_button(msg):
    if msg.from_user.id == ADMIN_ID:
        bot.send_message(msg.chat.id, "📤 <b>Export Stock</b>", 
                        reply_markup=export_options_keyboard(), parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

# ======================= DIRECT DELIVERY =======================
@bot.message_handler(func=lambda msg: msg.text == "🚚 Direct Delivery")
def direct_delivery_menu(msg):
    if msg.from_user.id == ADMIN_ID:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📤 Deliver Account", callback_data="direct_deliver"),
            InlineKeyboardButton("📋 Delivery History", callback_data="delivery_history")
        )
        
        bot.send_message(msg.chat.id, "🚚 <b>Direct Delivery System</b>\n\nSelect option:",
                        reply_markup=keyboard, parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

@bot.callback_query_handler(func=lambda call: call.data == "direct_deliver")
def direct_deliver_start(call):
    msg = bot.edit_message_text(
        "🚚 <b>Direct Account Delivery</b>\n\n"
        "Send in this format:\n"
        "<code>[user_id] [account_type] [connection_type] [quantity] [account_details]</code>\n\n"
        "<b>Example (Two-Step):</b>\n"
        "<code>123456789 two_step 10+ 5 leonardomorris1481i@gmail.com:%Date10.07%:CEZFD3U5VF64IPMWVKQMZQ5VNH75EUE3:2fa_code_here:https://www.linkedin.com/in/leonardo-morris-5a2898332/</code>\n\n"
        "<b>For single account, quantity = 1</b>\n"
        "<b>Account Types:</b> <code>two_step</code> or <code>hotmail</code>\n"
        "<b>Connection Types:</b> <code>0+</code>, <code>1-9+</code>, <code>10+</code>, etc.\n"
        "<b>Quantity:</b> 1-100",
        call.message.chat.id, call.message.message_id,
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_direct_delivery)

def process_direct_delivery(message):
    try:
        parts = message.text.split(maxsplit=4)
        if len(parts) == 5:
            user_id = int(parts[0])
            account_type = parts[1]
            connection_type = parts[2]
            quantity = int(parts[3])
            account_details = parts[4]
            
            if account_type not in ["two_step", "hotmail"]:
                bot.send_message(message.chat.id, "❌ Invalid account type! Use 'two_step' or 'hotmail'")
                return
            
            if connection_type not in PRICES[account_type]:
                bot.send_message(message.chat.id, f"❌ Invalid connection type!")
                return
            
            if quantity < 1 or quantity > 100:
                bot.send_message(message.chat.id, "❌ Quantity must be 1-100!")
                return
            
            # Create delivery folder if not exists
            delivery_folder = "user_deliveries"
            if not os.path.exists(delivery_folder):
                os.makedirs(delivery_folder)
            
            # Create .txt file for delivery
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{account_type}_{connection_type}_{quantity}_accounts_{timestamp}.txt"
            filepath = os.path.join(delivery_folder, filename)
            
            # Parse account details
            try:
                all_parts = account_details.split(':')
                if len(all_parts) >= 5:
                    email = all_parts[0]
                    mail_pass = all_parts[1]
                    linkedin_pass = all_parts[2]
                    recovery_or_2fa = all_parts[3]
                    url = ':'.join(all_parts[4:])
                    url = fix_url_format(url)
                else:
                    email, mail_pass, linkedin_pass, recovery_or_2fa, url = "N/A", "N/A", "N/A", "N/A", "N/A"
            except:
                email, mail_pass, linkedin_pass, recovery_or_2fa, url = "N/A", "N/A", "N/A", "N/A", "N/A"
            
            # Write accounts to file
            with open(filepath, 'w', encoding='utf-8') as f:
                for i in range(quantity):
                    f.write(f"Account #{i+1}:\n")
                    f.write(f"Email: {email}\n")
                    f.write(f"Mail Password: {mail_pass}\n")
                    f.write(f"LinkedIn Password: {linkedin_pass}\n")
                    if account_type == "two_step":
                        f.write(f"Two-Step Auth: {recovery_or_2fa}\n")
                    else:
                        f.write(f"Recovery Email: {recovery_or_2fa}\n")
                    f.write(f"Profile URL: {url}\n")
                    f.write(f"{'='*40}\n")
            
            # Add to direct delivery table (multiple entries)
            delivery_ids = []
            for i in range(quantity):
                delivery_id = db.add_direct_delivery(user_id, account_type, connection_type, 
                                                   account_details, message.from_user.id)
                delivery_ids.append(delivery_id)
                
                # Add to file for stock
                count = add_account_to_file(account_type, connection_type, account_details)
                db.update_stock(account_type, connection_type, count)
            
            # Send to user
            try:
                acc_name = "Two-Step Authentication" if account_type == "two_step" else "Hotmail/Outlook"
                
                # Send file to user
                with open(filepath, 'rb') as file:
                    caption = f"""✅ <b>Bulk Accounts Delivered!</b>

📦 <b>Delivery ID:</b> #{delivery_ids[0]}-#{delivery_ids[-1]}
🔐 <b>Type:</b> {acc_name}
🔗 <b>Connection:</b> {connection_type}
📦 <b>Quantity:</b> {quantity} accounts
📅 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📄 <b>File:</b> {filename}

⚠️ <b>Important:</b> 
1. Change passwords immediately
2. Enable 2FA if available
3. Report issues within 24 hours

<b>Support:</b> {SUPPORT_USERNAME}"""
                    
                    bot.send_document(user_id, file, caption=caption, parse_mode="HTML")
                
                # Send confirmation to admin
                bot.send_message(message.chat.id,
                               f"✅ {quantity} accounts delivered to user {user_id}\n"
                               f"Delivery IDs: #{delivery_ids[0]}-#{delivery_ids[-1]}\n"
                               f"File: {filename}",
                               parse_mode="HTML")
                
                # Clean up file after sending
                os.remove(filepath)
                
            except Exception as e:
                bot.send_message(message.chat.id,
                               f"❌ Could not send to user {user_id}\n"
                               f"But added to delivery history. Error: {str(e)}")
        else:
            bot.send_message(message.chat.id, 
                           "❌ Invalid format! Use: [user_id] [type] [conn] [quantity] [details]")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "delivery_history")
def show_delivery_history(call):
    deliveries = db.get_direct_deliveries(limit=20)
    
    if not deliveries:
        bot.edit_message_text("📭 No delivery history found.",
                            call.message.chat.id, call.message.message_id,
                            parse_mode="HTML")
        return
    
    response = "📋 <b>Recent Deliveries</b>\n\n"
    for delivery in deliveries:
        delivery_id, user_id, acc_type, conn_type, details, delivered_by, delivery_time, username = delivery
        response += f"🆔 #{delivery_id}\n"
        response += f"👤 User: {user_id} (@{username or 'N/A'})\n"
        response += f"📦 {acc_type} - {conn_type}\n"
        response += f"📅 {delivery_time}\n"
        response += "─" * 30 + "\n"
    
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id,
                         parse_mode="HTML")

# ======================= PRICE MANAGEMENT =======================
@bot.message_handler(func=lambda msg: msg.text == "💰 Price Management")
def price_management(msg):
    if msg.from_user.id == ADMIN_ID:
        bot.send_message(msg.chat.id, "💰 <b>Price Management</b>\n\nSelect option:",
                        reply_markup=price_management_keyboard(),
                        parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

@bot.callback_query_handler(
    func=lambda call: (
        call.data.startswith("price_")
        or call.data.startswith("edit_price_")
        or call.data == "view_prices"
    )
)
def handle_price_management(call):
    # ================= Price Menu =================
    if call.data == "price_two_step":
        keyboard = InlineKeyboardMarkup(row_width=2)
        for conn_type in PRICES["two_step"].keys():
            keyboard.add(
                InlineKeyboardButton(
                    f"Edit {conn_type}",
                    callback_data=f"edit_price_two_step_{conn_type}"
                )
            )

        bot.edit_message_text(
            "🔐 <b>Edit Two-Step Prices</b>\nSelect connection to edit:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    if call.data == "price_hotmail":
        keyboard = InlineKeyboardMarkup(row_width=2)
        for conn_type in PRICES["hotmail"].keys():
            keyboard.add(
                InlineKeyboardButton(
                    f"Edit {conn_type}",
                    callback_data=f"edit_price_hotmail_{conn_type}"
                )
            )

        bot.edit_message_text(
            "📧 <b>Edit Hotmail Prices</b>\nSelect connection to edit:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    if call.data == "view_prices":
        response = "💰 <b>Current Prices</b>\n\n"

        response += "🔐 <b>Two-Step Authentication:</b>\n"
        for conn, price in PRICES["two_step"].items():
            response += f"• {conn}: ${price}\n"

        response += "\n📧 <b>Hotmail/Outlook:</b>\n"
        for conn, price in PRICES["hotmail"].items():
            response += f"• {conn}: ${price}\n"

        bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML"
        )
        return

    # ================= Edit Single Price =================
    if call.data.startswith("edit_price_"):
        data = call.data.replace("edit_price_", "", 1)

        if data.startswith("two_step_"):
            account_type = "two_step"
            connection_type = data.replace("two_step_", "", 1)
        elif data.startswith("hotmail_"):
            account_type = "hotmail"
            connection_type = data.replace("hotmail_", "", 1)
        else:
            bot.answer_callback_query(call.id, "❌ Invalid price edit data!")
            return

        current_price = PRICES[account_type][connection_type]

        msg = bot.edit_message_text(
            f"✏️ <b>Edit Price</b>\n\n"
            f"Type: {'Two-Step' if account_type == 'two_step' else 'Hotmail'}\n"
            f"Connection: {connection_type}\n"
            f"Current Price: ${current_price}\n\n"
            f"Send new price (number only):",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML"
        )

        bot.register_next_step_handler(
            msg,
            lambda m: update_price_step(m, account_type, connection_type)
        )

def update_price_step(message, account_type, connection_type):
    try:
        new_price = float(message.text)
        PRICES[account_type][connection_type] = new_price
        save_prices(PRICES)
        
        bot.send_message(message.chat.id,
                        f"✅ Price updated!\n"
                        f"{connection_type} is now ${new_price}",
                        parse_mode="HTML")
        
        # Show price management again
        bot.send_message(message.chat.id, "💰 <b>Price Management</b>",
                        reply_markup=price_management_keyboard(),
                        parse_mode="HTML")
    except:
        bot.send_message(message.chat.id, "❌ Invalid price! Send a number only.")

# ======================= OTHER ADMIN FUNCTIONS =======================
@bot.message_handler(commands=['addbalance'])
def addbalance_command(message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            if len(parts) == 3:
                user_id = int(parts[1])
                amount = float(parts[2])
                
                old_balance = db.get_balance(user_id)
                db.update_balance(user_id, amount)
                new_balance = db.get_balance(user_id)
                
                response = f"""✅ <b>Balance Added!</b>

👤 <b>User ID:</b> <code>{user_id}</code>
💰 <b>Amount:</b> ${amount:.2f}
📊 <b>Old Balance:</b> ${old_balance:.2f}
💳 <b>New Balance:</b> ${new_balance:.2f}"""
                
                bot.send_message(message.chat.id, response, parse_mode="HTML")
                
                # Notify user
                try:
                    bot.send_message(user_id, 
                                   f"💰 Admin added ${amount:.2f} to your balance.\nNew balance: ${new_balance:.2f}",
                                   parse_mode="HTML")
                except:
                    pass
            else:
                bot.send_message(message.chat.id, 
                               "❌ Format: /addbalance [user_id] [amount]")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
    else:
        bot.send_message(message.chat.id, "❌ Access denied!")

@bot.message_handler(func=lambda msg: msg.text == "📊 Statistics")
def statistics_button(msg):
    if msg.from_user.id == ADMIN_ID:
        users = db.get_all_users()
        total_users = len(users)
        total_balance = sum(user[2] for user in users)
        
        deliveries = db.get_direct_deliveries()
        total_deliveries = len(deliveries)
        
        stock = db.get_all_stock()
        total_stock = sum(item[2] for item in stock)
        
        response = f"""📊 <b>Statistics</b>

👥 <b>Total Users:</b> {total_users}
💰 <b>Total Balance:</b> ${total_balance:.2f}
🚚 <b>Direct Deliveries:</b> {total_deliveries}
📦 <b>Total Stock:</b> {total_stock} accounts
👑 <b>Admin ID:</b> <code>{ADMIN_ID}</code>"""
        
        bot.send_message(msg.chat.id, response, parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

@bot.message_handler(func=lambda msg: msg.text == "👥 Users List")
def users_list_button(msg):
    if msg.from_user.id == ADMIN_ID:
        users = db.get_all_users()
        if not users:
            bot.send_message(msg.chat.id, "📭 No users found!")
            return
        
        response = "👥 <b>All Users</b>\n\n"
        for user in users:
            user_id, username, balance = user
            response += f"🆔 <code>{user_id}</code>\n👤 @{username or 'N/A'}\n💰 ${balance:.2f}\n────────────\n"
        
        bot.send_message(msg.chat.id, response, parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

# ======================= USER FUNCTIONS =======================
@bot.message_handler(func=lambda msg: msg.text == "🛒 Buy LinkedIn Accounts")
def buy_accounts_button(msg):
    bot.send_message(msg.chat.id,
                    "📋 <b>Select Account Type:</b>\n\n"
                    "🔐 <b>Two-Step Authentication:</b>\n"
                    "• More secure accounts\n\n"
                    "📧 <b>Hotmail/Outlook:</b>\n"
                    "• Hotmail/Outlook email based",
                    reply_markup=account_type_keyboard(),
                    parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "💰 Check My Balance")
def check_balance_button(msg):
    balance = db.get_balance(msg.from_user.id)
    bot.send_message(msg.chat.id,
                    f"💰 <b>Your Balance:</b> ${balance:.2f}\n👤 <b>Your ID:</b> <code>{msg.from_user.id}</code>",
                    parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "💳 Add Balance")
def add_balance_user_button(msg):
    user_id = msg.from_user.id
    instructions = f"""💳 <b>Add Balance Instructions</b>

<b>Your User ID:</b> <code>{user_id}</code>
<b>Copy this ID when sending payment</b>

<b>Payment Methods:</b>
1. <b>Binance ID:</b> <code>{BINANCE_ID}</code>
2. <b>USDT (BSC):</b> <code>{USDT_ADDRESS}</code>

<b>Steps:</b>
1. Send payment to above address
2. Take screenshot
3. Send screenshot here with your User ID
4. Admin will add balance

<b>Support:</b> {SUPPORT_USERNAME}"""
    
    bot.send_message(msg.chat.id, instructions, parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "📞 Support")
def support_button(msg):
    bot.send_message(msg.chat.id,
                    f"📞 <b>Support</b>\n\nContact: {SUPPORT_USERNAME}\nYour ID: <code>{msg.from_user.id}</code>",
                    parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text == "👑 Admin Panel")
def admin_panel_button(msg):
    if msg.from_user.id == ADMIN_ID:
        bot.send_message(msg.chat.id, "👑 <b>Admin Panel</b>", 
                        reply_markup=admin_keyboard(), parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, "❌ Access denied!")

@bot.message_handler(func=lambda msg: msg.text == "⬅️ Main Menu")
def main_menu_button(msg):
    start_command(msg)

# ======================= BULK BUY PROCESS =======================
@bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def handle_account_type(call):
    if call.data == "type_two_step":
        bot.edit_message_text(
            "🔐 <b>LinkedIn Two-Step Authentication</b>\n\n"
            "Select connection count:",
            call.message.chat.id, call.message.message_id,
            reply_markup=connection_keyboard("two_step"),
            parse_mode="HTML"
        )
    elif call.data == "type_hotmail":
        bot.edit_message_text(
            "📧 <b>LinkedIn Hotmail/Outlook Login</b>\n\n"
            "Select connection count:",
            call.message.chat.id, call.message.message_id,
            reply_markup=connection_keyboard("hotmail"),
            parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_types")
def back_to_account_types(call):
    bot.edit_message_text(
        "📋 <b>Select Account Type:</b>\n\n"
        "🔐 <b>Two-Step Authentication:</b>\n"
        "• More secure accounts\n\n"
        "📧 <b>Hotmail/Outlook:</b>\n"
        "• Hotmail/Outlook email based",
        call.message.chat.id, call.message.message_id,
        reply_markup=account_type_keyboard(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy(call):
    parts = call.data.split("_")
    account_type = "_".join(parts[1:-1])   # two_step / hotmail
    connection_type = parts[-1]            # 0+ / 10+ / 50+ etc
    
    # Store purchase info for next step
    purchase_data = {
        'account_type': account_type,
        'connection_type': connection_type,
        'price': PRICES[account_type][connection_type],
        'user_id': call.from_user.id
    }
    
    msg = bot.edit_message_text(
        f"🛒 <b>Bulk Purchase</b>\n\n"
        f"🔐 <b>Type:</b> {'Two-Step' if account_type == 'two_step' else 'Hotmail'}\n"
        f"🔗 <b>Connection:</b> {connection_type}\n"
        f"💰 <b>Price per account:</b> ${PRICES[account_type][connection_type]:.2f}\n\n"
        f"📦 <b>Enter quantity (1-100):</b>",
        call.message.chat.id, call.message.message_id,
        parse_mode="HTML"
    )
    
    bot.register_next_step_handler(msg, lambda m: process_quantity(m, purchase_data))

def process_quantity(message, purchase_data):
    try:
        quantity = int(message.text.strip())
        
        if quantity < 1 or quantity > 100:
            bot.send_message(message.chat.id, "❌ Quantity must be between 1-100!")
            return
        
        user_balance = db.get_balance(purchase_data['user_id'])
        total_price = purchase_data['price'] * quantity
        
        if user_balance < total_price:
            bot.send_message(
                message.chat.id,
                f"❌ <b>Insufficient balance!</b>\n"
                f"💰 <b>Needed:</b> ${total_price:.2f}\n"
                f"💳 <b>Available:</b> ${user_balance:.2f}\n"
                f"Please add balance first!",
                parse_mode="HTML"
            )
            return
        
        # Check stock
        stock_count = db.get_stock(purchase_data['account_type'], purchase_data['connection_type'])
        
        if stock_count < quantity:
            bot.send_message(
                message.chat.id,
                f"❌ <b>Insufficient stock!</b>\n"
                f"📦 <b>Available:</b> {stock_count} accounts\n"
                f"📦 <b>Requested:</b> {quantity} accounts",
                parse_mode="HTML"
            )
            return
        
        # Process bulk purchase
        accounts_list = []
        
        for i in range(quantity):
            account_details, new_count = get_account_from_file(
                purchase_data['account_type'], 
                purchase_data['connection_type']
            )
            
            if account_details:
                accounts_list.append(account_details)
                # Update stock after each extraction
                db.update_stock(purchase_data['account_type'], purchase_data['connection_type'], new_count)
            else:
                bot.send_message(
                    message.chat.id,
                    f"❌ Not enough stock! Only {i} accounts available.",
                    parse_mode="HTML"
                )
                return
        
        # Deduct balance
        db.update_balance(purchase_data['user_id'], -total_price)
        
        # Add order to database
        for account_details in accounts_list:
            db.add_order(
                purchase_data['user_id'],
                purchase_data['account_type'],
                purchase_data['connection_type'],
                purchase_data['price'],
                account_details
            )
        
        # Create delivery folder if not exists
        delivery_folder = "user_deliveries"
        if not os.path.exists(delivery_folder):
            os.makedirs(delivery_folder)
        
        # Create .txt file for delivery
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        account_type_name = "two_step" if purchase_data['account_type'] == 'two_step' else 'hotmail'
        filename = f"linkedin_{account_type_name}_{purchase_data['connection_type']}_{quantity}_accounts_{timestamp}.txt"
        filepath = os.path.join(delivery_folder, filename)
        
        # Prepare account type name for display
        acc_name = "Two-Step Authentication" if purchase_data['account_type'] == 'two_step' else 'Hotmail/Outlook'
        
        # Write accounts to file with ONE-LINE format
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"✅ LinkedIn Accounts Purchase Receipt\n")
            f.write(f"══════════════════════════════════════════════════\n")
            f.write(f"Order Details:\n")
            f.write(f"• Order Quantity: {quantity}\n")
            f.write(f"• Account Type: {acc_name}\n")
            f.write(f"• Connection: {purchase_data['connection_type']}\n")
            f.write(f"• Price per account: ${purchase_data['price']:.2f}\n")
            f.write(f"• Total Price: ${total_price:.2f}\n")
            f.write(f"• Order Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"══════════════════════════════════════════════════\n\n")
            
            # Format Header based on account type
            if purchase_data['account_type'] == "two_step":
                f.write(f"📋 Two-Step Authentication Accounts ({quantity}):\n")
                f.write(f"Format: email:mail_password:linkedin_password:two_step_code:url\n")
                f.write(f"══════════════════════════════════════════════════\n\n")
            else:
                f.write(f"📋 Hotmail/Outlook Accounts ({quantity}):\n")
                f.write(f"Format: email:mail_password:linkedin_password:recovery_email:url\n")
                f.write(f"══════════════════════════════════════════════════\n\n")
            
            # Write each account in ONE LINE format
            for i, account_details in enumerate(accounts_list, 1):
                # Clean the account details
                account_details = account_details.strip()
                
                # Fix common formatting issues
                # If account has "https" in the middle, fix it
                if " https" in account_details:
                    account_details = account_details.replace(" https", "https")
                if " http" in account_details:
                    account_details = account_details.replace(" http", "http")
                
                # Add account number
                f.write(f"Account #{i}:\n")
                f.write(f"{account_details}\n")
                f.write(f"{'─' * 40}\n")
        
        # Send file to user
        with open(filepath, 'rb') as file:
            caption = f"""✅ <b>Bulk Purchase Completed!</b>

📦 <b>Quantity:</b> {quantity} accounts
🔐 <b>Type:</b> {acc_name}
🔗 <b>Connection:</b> {purchase_data['connection_type']}
💰 <b>Price per account:</b> ${purchase_data['price']:.2f}
💵 <b>Total:</b> ${total_price:.2f}
📊 <b>Remaining Balance:</b> ${db.get_balance(purchase_data['user_id']):.2f}
📅 <b>Order Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📄 <b>File:</b> {filename}

⚠️ <b>Important:</b> 
1. Change passwords immediately
2. Enable 2FA if available
3. Report issues within 24 hours

<b>Support:</b> {SUPPORT_USERNAME}"""
            
            bot.send_document(message.chat.id, file, caption=caption, parse_mode="HTML")
        
        # Clean up file after sending
        os.remove(filepath)
        
        # Send confirmation
        bot.send_message(
            message.chat.id,
            f"✅ <b>Successfully purchased {quantity} {acc_name} accounts!</b>\n"
            f"💰 <b>Total:</b> ${total_price:.2f} deducted from your balance.\n"
            f"💳 <b>New Balance:</b> ${db.get_balance(purchase_data['user_id']):.2f}",
            reply_markup=main_menu_keyboard(message.from_user.id == ADMIN_ID),
            parse_mode="HTML"
        )
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid quantity! Please enter a number between 1-100.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# ======================= MAIN =======================
if __name__ == "__main__":
    try:
        print("=" * 50)
        print("🤖 LinkedIn Accounts Bot - Starting...")
        print("=" * 50)
        
        # Check if folders exist
        ensure_folders()
        print("✅ Folders checked/created")
        
        # Test database connection
        print("✅ Database initialized")
        
        # Test token
        print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
        print(f"👑 Admin ID: {ADMIN_ID}")
        print(f"📞 Support: {SUPPORT_USERNAME}")
        
        # Start bot
        print("🔄 Starting bot polling...")
        print("=" * 50)
        print("Bot is now running. Press Ctrl+C to stop.")
        print("=" * 50)
        
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
