import logging
import json
import sys
from datetime import datetime

import requests
import telegram
from telegram.ext import CommandHandler, Updater, filters, MessageHandler
from telegram.ext.dispatcher import run_async
from bot_token import TOKEN

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


api_addr = 'http://127.0.0.1:5000'

CREATOR_ID = 891572805
ENABLED_CHATS = set([-366748532, -1001423166131])

CFG_RESPONSE = '''CSMN config:
- *标题*: {title}
- *开始时间*: {start}
- *默认链接*: {url}
- *字幕链接*: {subs}
- *CDN*:
{cdn}
'''

HELP_SET_CONFIG = '''Usage `/set option value`
Supported:
`/set title <title>`
`/set url <url>`
`/set subs <url>`
`/set start <yyyymmdd HHMM>`
`/set cdn add <name> <url>`
`/set cdn del <index>`
'''

@run_async
def on_enable(update, context):
    logging.info('command [enable] started')
    message = update.message
    uid = message.from_user.id
    chat_id = message.chat_id
    if uid == CREATOR_ID:
        logging.info('bot enabled in %s' % chat_id)
        ENABLED_CHATS.add(chat_id)
        context.bot.send_message(
            reply_to_message_id=update.message.message_id,
            chat_id=chat_id, text='bot enabled in this chat'
        )
    else:
        context.bot.send_message(chat_id=chat_id, text='not allowed')

@run_async
def on_status(update, context):
    logging.info('commamd: [on_status] started')
    bot = context.bot
    message = update.message
    chat_id = message.chat_id
    if chat_id not in ENABLED_CHATS:
        return context.bot.send_message(
            reply_to_message_id=update.message.message_id,
            chat_id=chat_id, text='not allowed in this chat'
        )
    r = requests.get(api_addr + '/api/config')
    try:
        current_config = json.loads(r.content)
    except Exception as e:
        logging.error('get /api/config failed. data=%s', r.content)
        current_config = {}
    cdns = '\n'.join(
        '   - *' + _cdn.get('name') + '* ' + _cdn.get('url')
        for _cdn in current_config.get('quality', [])
    )
    start = current_config.get('start') or 0
    start = datetime.fromtimestamp(start)
    rsp = CFG_RESPONSE.format(
        title=current_config.get('title'),
        start=start.strftime('%Y-%m-%d %H:%M'),
        url=current_config.get('url'),
        subs=current_config.get('subtitle', {}).get('url'),
        cdn=cdns,
    )
    context.bot.send_message(
        reply_to_message_id=update.message.message_id,
        chat_id=chat_id, text=rsp, parse_mode='markdown'
    )

@run_async
def on_set(update, context):
    logging.info('commamd: [on_set] started')
    bot = context.bot
    message = update.message
    chat_id = message.chat_id
    if chat_id not in ENABLED_CHATS:
        return context.bot.send_message(
            reply_to_message_id=update.message.message_id,
            chat_id=chat_id, text='not allowed in this chat',
            parse_mode='markdown',
        )
    args = message.text.split()[1:]
    if len(args) < 2:
        context.bot.send_message(
            reply_to_message_id=update.message.message_id,
            chat_id=chat_id, text=HELP_SET_CONFIG, parse_mode='markdown',
        )
        return
    option = args[0]
    args = args[1:]
    code, result = api_set_config(option, args)
    if code is not 200:
        context.bot.send_message(
            reply_to_message_id=update.message.message_id,
            chat_id=chat_id,
            text='error: upstream responded with code %s' % code
        )
        return
    msg = result.get('msg')
    context.bot.send_message(
        reply_to_message_id=update.message.message_id,
        chat_id=chat_id,
        text=msg,
    )

def api_set_config(key, args):
    if key not in ('title', 'url', 'subs', 'start', 'cdn'):
        return 400, 'Unsupported option ' + key
    data = {
        'key': key,
        'val': ' '.join(args)
    }
    url = api_addr + '/api/config'
    r = requests.post(url, data=data)
    try:
        rsp = r.json()
    except Exception as e:
        logging.error('api_set_config failed. key=%s, args=%s, rsp=%s', key, args, r.content)
        rsp = {}
    return r.status_code, rsp

CMD_CONTROLLER_MAP = {
    'enable': on_enable,
    'status': on_status,
    'set': on_set,
}

def main(token, request_kwargs=None):
    global CMD_CONTROLLER_MAP

    updater = Updater(token=token, request_kwargs=args, use_context=True)

    dispatcher = updater.dispatcher

    for cmd, func in CMD_CONTROLLER_MAP.items():
        dispatcher.add_handler(CommandHandler(cmd, func))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    args = {}
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1 and sys.argv[1] == 'dev':
        logging.info('use proxy')
        args.update(proxy_url='socks5://127.0.0.1:1080')
    main(TOKEN, args)

