import telegram as libr
import pika
import json
import copy
import fastf1
from datetime import datetime

# Telegram credentials
my_token = "7528122259:AAHen1bT65reaaTN0d8SoAZl7u_hNZt7EWc"
my_telegram_ID = "7518813395"

# RabbitMQ setup
params = pika.ConnectionParameters(host="172.17.0.3")
connection = pika.BlockingConnection(params)
channel = connection.channel()

channel.queue_declare(queue='f1_timetable_queue')
channel.exchange_declare(exchange='f1_timetable', exchange_type='direct')
channel.queue_bind(exchange='f1_timetable', queue="f1_timetable_queue")

def send(msg, chat_id, context, token=my_token):
    context.logger.info('Sending msg:' + msg)
    bot = libr.Bot(token=token)
    bot.sendMessage(chat_id=chat_id, text=msg)

def get_f1_session_info():
    now = datetime.utcnow()
    schedule = fastf1.get_event_schedule(now.year)
    next_race = schedule[schedule['Session5Date'] > now].iloc[0]
    
    msg = f"Upcoming F1 Event: {next_race['EventName']}\n"
    msg += f"Race Date: {next_race['Session5Date']} UTC\n"
    msg += f"Circuit: {next_race['Location']}"
    return msg

def handler(context, event):
    context.logger.info('Processing F1 event update')
    res = json.loads(event.body.decode())
    
    if not res:
        send("No live F1 sessions currently.", my_telegram_ID)
        return
    
    session_update = f"Session: {res.get('session', 'Unknown')}\n"
    session_update += f"Driver: {res.get('driver', 'Unknown')}\n"
    session_update += f"Lap Time: {res.get('lap_time', 'N/A')}\n"
    session_update += f"Position: {res.get('position', 'N/A')}"
    
    send(session_update, my_telegram_ID, context)


if __name__ == "__main__":
    send()