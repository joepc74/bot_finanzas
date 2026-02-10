import yfinance as yf
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os, asyncio, logging, sqlite3, io
from telebot import asyncio_filters
from telebot.types import *
from telebot.async_telebot import AsyncTeleBot

# Replace with your actual Telegram Bot Token
load_dotenv()
TOKEN = os.getenv('KEY_TELEGRAM')
bot = AsyncTeleBot(token=TOKEN)
con=None

def is_valid_user(id):
    """Check if the user ID is valid."""
    # Implement your logic to check if the user ID is valid
    # For example, you can maintain a list of allowed user IDs
    allowed_users = [201580722, 201580722]  # Replace with actual user IDs
    return id in allowed_users

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    """Send a message when the command /start is issued."""
    await bot.reply_to(message, 'Welcome! Use /price <ticker> to get the current price of a stock.\nUse /help for more commands.')

@bot.message_handler(commands=['help'])
async def send_help(message):
    """Send a message when the command /help is issued."""
    await bot.reply_to(message,'''Available commands:
                              /price <ticker> - Get current price of a stock.
                              /sma <ticker> <*short_period> <*long_period> - Get SMA crossover graph, periods are 9 and 20 by default.
                              /graph <ticker> <*period> - Get price graph of a stock, period is 1d, 5d, 1mo, 3mo, 6mo, 1y (defaul value), 2y, 5y, 10y, ytd, max.
                              /track <ticker> - Track a stock for price updates every 12 hours.
                              /untrack <ticker> - Stop tracking a stock.
                              /tracks - Show tracked stocks.''')
def is_tracking(user_id, ticker):
    global con
    cursor= con.cursor()
    cursor.execute("SELECT * FROM tracks WHERE user_id=? AND ticker=?;", (user_id, ticker))
    return cursor.fetchone()

@bot.message_handler(commands=['price'])
async def send_price(message):
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    """Get the current price of a stock."""
    ticker = message.text.split()[1] if len(message.text.split()) > 1 else None
    logging.info(f"User {message.from_user.id} requested price for {ticker}.")
    try:
        stock = yf.Ticker(ticker)
        current_price = stock.info['regularMarketPrice']
        await bot.reply_to(message,f"Current price of {stock.info['longName']} ({ticker}): {current_price}")
    except Exception as e:
        print(e)
        logging.error(f"Error fetching price for {ticker}: {e}")
        await bot.reply_to(message,"Invalid ticker symbol.")

@bot.message_handler(commands=['sma'])
async def send_sma(message) -> None:
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    """Generate and send SMA crossover graph."""
    ticker = message.text.split()[1] if len(message.text.split()) > 1 else None
    short_period = int(message.text.split()[2]) if len(message.text.split()) > 2 else 9
    long_period = int(message.text.split()[3]) if len(message.text.split()) > 3 else 20
    logging.info(f"User {message.from_user.id} requested SMA crossover graph for {ticker} with short period {short_period} and long period {long_period}.")

    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1y")
        data['SMA_short'] = data['Close'].rolling(short_period).mean()
        data['SMA_long'] = data['Close'].rolling(long_period).mean()

        plt.figure(figsize=(12, 6))
        plt.plot(data['Close'], label='Close')
        plt.plot(data['SMA_short'], label=f'SMA {short_period}')
        plt.plot(data['SMA_long'], label=f'SMA {long_period}')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.title(f'SMA Crossover for {ticker}')
        plt.legend()
        plt.grid(True)


        # Save the graph to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        image_bytes = buf.getvalue()
        # Send the graph to the user
        await bot.send_photo(chat_id=message.chat.id, photo=image_bytes, caption=f"SMA Crossover graph for {ticker} with short period {short_period} and long period {long_period}:")
        buf.close()
        plt.close()

    except Exception as e:
        print(e)
        logging.error(f"Error generating SMA graph for {ticker}: {e}")
        await bot.reply_to(message,"Error generating SMA graph.")

def graph(ticket,period="1y",buy_price=None):
    stock = yf.Ticker(ticket)
    data = stock.history(period=period)

    plt.figure(figsize=(12, 6))
    plt.plot(data['Close'], label='Close')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.title(f'Price Graph for {stock.info["longName"]} ({ticket})')
    if buy_price:
        plt.axhline(y=buy_price, color='r', linestyle='--', label=f'Buy Price: {buy_price}')
    plt.legend()
    plt.grid(True)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    image_bytes = buf.getvalue()
    buf.close()
    plt.close()
    return image_bytes

@bot.message_handler(commands=['graph'])
async def send_graph(message):
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    """Generate and send price graph."""
    ticker = message.text.split()[1] if len(message.text.split()) > 1 else None
    periodo=message.text.split()[2] if len(message.text.split()) > 2 else '1y' # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    logging.info(f"User {message.from_user.id} requested price graph for {ticker} with period {periodo}.")
    try:
        track=is_tracking(message.from_user.id, ticker)
        await bot.send_photo(chat_id=message.chat.id, photo=graph(ticker,periodo,buy_price=track['buy_price'] if track else None), caption=f"Price graph for {ticker} with period {periodo}:")
    except Exception as e:
        print(e)
        logging.error(f"Error generating price graph for {ticker}: {e}")
        await bot.reply_to(message,"Error generating price graph.")

@bot.message_handler(commands=['track'])
async def track_ticket(message):
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    """Track a ticket."""
    ticker = message.text.split()[1] if len(message.text.split()) > 1 else None
    buy_price = float(message.text.split()[2]) if len(message.text.split()) > 2 else 0
    try:
        stock = yf.Ticker(ticker)
        global con
        cursor= con.cursor()
        cursor.execute("INSERT INTO tracks (user_id, ticker, buy_price) VALUES (?, ?, ?);", (message.from_user.id, ticker, buy_price))
        con.commit()
        await bot.reply_to(message,f"Tracking {ticker} for price updates.")
    except Exception as e:
        print(e)
        logging.error(f"Error tracking {ticker}: {e}")
        await bot.reply_to(message,"Error tracking the ticket.")

@bot.message_handler(commands=['tracks'])
async def tracks(message):
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    """Show tracked tickets."""
    global con
    cursor= con.cursor()
    cursor.execute("SELECT ticker, buy_price FROM tracks WHERE user_id=?;", (message.from_user.id,))
    tracks = cursor.fetchall()
    if tracks:
        response = "Tracked tickets:\n"
        for ticker, buy_price in tracks:
            response += f"- {ticker} (Buy Price: {buy_price})\n"
        await bot.reply_to(message, response)
    else:
        await bot.reply_to(message, "No tracked tickets.")

@bot.message_handler(commands=['untrack'])
async def untrack_ticket(message):
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    """Untrack a ticket."""
    ticker = message.text.split()[1] if len(message.text.split()) > 1 else None
    try:
        global con
        cursor= con.cursor()
        cursor.execute("DELETE FROM tracks WHERE user_id=? AND ticker=?;", (message.from_user.id, ticker))
        con.commit()
        await bot.reply_to(message,f"Untracked {ticker}.")
    except Exception as e:
        print(e)
        logging.error(f"Error untracking {ticker}: {e}")
        await bot.reply_to(message,"Error untracking the ticket.")

@bot.message_handler(commands=['bd'])
async def envia_bd(message):
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    await bot.send_document(message.chat.id,open('bot.db','rb'))
    return
@bot.message_handler(commands=['sql'])
async def comando_sql(message):
    if not is_valid_user(message.from_user.id):
        await bot.reply_to(message, "Unauthorized access.")
        return
    sql=" ".join(message.text.split()[1:])
    try:
        con.execute(sql)
        con.commit()
        await bot.reply_to(message, "Ejecutado", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error executing SQL command: {e}")

async def actualiza_tickets():
    global con
    cursor= con.cursor()
    while True:
        logging.info("Checking for tickets ...")
        seguimentos= cursor.execute("SELECT * FROM tracks WHERE last_check < datetime('now', '-11 hours');").fetchall()
        if seguimentos:
            for seguimiento in seguimentos:
                id, user_id, ticker, last_check, buy_price = seguimiento
                try:
                    stock = yf.Ticker(ticker)
                    current_price = stock.info['regularMarketPrice']
                    min_price=stock.info['dayLow']
                    max_price=stock.info['dayHigh']
                    open_price=stock.info['open']
                    change=round((current_price-open_price)/current_price*100,2) if current_price else 0
                    buy_change=round((current_price-buy_price)/current_price*100,2) if current_price and buy_price else 0
                    await bot.send_photo(chat_id=user_id, photo=graph(ticker,'1mo', buy_price=buy_price if buy_price!=0 else None),caption=f"Current price of {stock.info['longName']} ({ticker}): {current_price}\nMin: {min_price}\nMax: {max_price}\nChange: {change}%\nBuy Change: {buy_change}%")
                    cursor.execute(f"UPDATE tracks SET last_check=current_timestamp WHERE id={id};")
                    con.commit()
                except Exception as e:
                    print(e)
                    logging.error(f"Error sending message to {user_id}: {e}")
        logging.info("Price updates checked. Next check in 12 hours.")
        await asyncio.sleep(12*60*60) # se ejecuta cada 12 horas


async def main():
    """Start the bot."""

    await bot.set_my_commands([
        BotCommand("start","Start the bot"),
        BotCommand("help","Show help message"),
        BotCommand("price","Show current price of a stock"),
        BotCommand("sma","Show SMA of a stock"),
        BotCommand("graph","Show price graph of a stock"),
        BotCommand("track","Track a stock"),
        BotCommand("untrack","Untrack a stock"),
        BotCommand("tracks","Show tracked stocks")
    ])

    try:
        bot.add_custom_filter(asyncio_filters.StateFilter(bot))
        L = await asyncio.gather(
            # update_cambios(),
            actualiza_tickets(),
            bot.polling(non_stop=True)
            )
    finally:
        bot.close()

def init_db():
    logging.info("Initializing database connection...")
    global con
    con = sqlite3.connect("bot.db")
    con.row_factory = sqlite3.Row
    # Create the tracks table if it doesn't exist
    con.execute("CREATE TABLE IF NOT EXISTS tracks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ticker TEXT, last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP, buy_price REAL NOT NULL DEFAULT 0);")

def text():
    dat = yf.Ticker("AUCO.L")
    # print(dat.__dict__)
    print('\n'.join(f'{k}: {v}' for k, v in dat.info.items()))
    # print(dat.calendar)
    # print(dat.analyst_price_targets)
    # print(dat.quarterly_income_stmt)
    # print(dat.history(period='1mo'))
    # print(dat.option_chain(dat.options[0]).calls)

if __name__ == '__main__':
    if '-log' in os.sys.argv:
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', filename='bot.log')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='bot.log')
    init_db()
    asyncio.run(main())
