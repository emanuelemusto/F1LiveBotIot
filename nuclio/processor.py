import telebot
import pika
import json
from datetime import datetime
import os

# Telegram credentials
my_token = os.getenv("TELEGRAM_BOT_TOKEN")
my_telegram_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telebot.TeleBot(my_token)
last_message_id = None

# RabbitMQ setup
params = pika.ConnectionParameters(host = "f1livebot1-rabbitmq-1", port = 5672)
connection = pika.BlockingConnection(params)
channel = connection.channel()

channel.queue_declare(queue='f1_timetable_queue')
channel.exchange_declare(exchange='f1_timetable', exchange_type='direct')
channel.queue_bind(exchange='f1_timetable', queue="f1_timetable_queue")

def send_or_update_timetable(timetable_message):
    global last_message_id
    if last_message_id:
        try:
            bot.edit_message_text(chat_id=my_telegram_ID, message_id=last_message_id, 
                                  text=timetable_message, parse_mode="Markdown")
            return
        except:
            last_message_id = None
    message = bot.send_message(my_telegram_ID, timetable_message, parse_mode="Markdown")
    last_message_id = message.message_id

def handler(context, event):
    context.logger.info('Processing F1 event update')
    
    res = json.loads(event.body.decode())
    
    if not res:
        send_or_update_timetable("No live F1 sessions currently.")
        return
    
    context.logger.info(res)
    
    send_or_update_timetable(res)
