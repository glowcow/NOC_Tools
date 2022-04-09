#!/bin/python3

from main.config import tg_api, bc
import telebot, re

class tg_msg:
    def send(chat_id, title, msg):
        bot = telebot.TeleBot(tg_api.bot_token)
        try:
            bot.send_message(chat_id=chat_id , text=f'{title}\n{msg}', parse_mode='HTML')
            print(f'{bc.GREEN}[+]{bc.ENDC} Telegram message sent successfully!')
            return True
        except telebot.apihelper.ApiTelegramException as err:
            if re.findall('Error code: 400', str(err)):
                lc = len(msg.split("\n"))
                chc = len(msg)
                print(f'{bc.RED}[!]{bc.ENDC} Telegram API Error: {err}!\n{bc.RED}[!]{bc.ENDC} Message lines/character count: {lc}/{chc}')
                bot.send_message(chat_id=chat_id , text=f'{title}\n<b>Telegram API Error: {err}!</b> \nMessage lines/character count: {lc}/{chc}', parse_mode='HTML')
            elif re.findall('Error code: 401', str(err)):
                print(f'{bc.RED}[!]{bc.ENDC} Telegram API Error: {err}!')
            return False
        except:
            print(f'{bc.RED}[!]{bc.ENDC} Telegram API Error: Unknown!')
            return False

class tg_file:
    def send(chat_id, title, path):
        bot = telebot.TeleBot(tg_api.bot_token)
        try:
            file = open(path, 'rb')
            bot.send_document(chat_id=chat_id , data=file)
            print(f'{bc.GREEN}[+]{bc.ENDC} Telegram file from {bc.CYAN}{path}{bc.ENDC} sent successfully!')
            return True
        except telebot.apihelper.ApiTelegramException as err:
            if re.findall('Error code: 413', str(err)):
                print(f'{bc.RED}[!]{bc.ENDC} Telegram API Error: {err}!')
        except:
            print(f'{bc.RED}[!]{bc.ENDC} Telegram API Error: Unknown!')
            return False