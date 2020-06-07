# encoding: utf8

import collections
import json
import time
from datetime import datetime

from flask import Flask
from flask import request
import redis

app = Flask(__name__)
_REDIS_POOL = redis.ConnectionPool(host='localhost', port=6379, db=0)

_FALLBACK_URL = 'https://zhw2590582.github.io/assets-cdn/video/one-more-time-one-more-chance-480p.mp4'
FALLBACK = collections.defaultdict(bytes, {
    'csmn_title': b'',
    'csmn_video_url': _FALLBACK_URL.encode('utf8'),
    'csmn_backup_urls': [
        json.dumps({
            'default': True,
            'name': '未设置 (Sample)',
            'url': _FALLBACK_URL,
        }),
    ],
})

def redis_cli():
    global _REDIS_POOL
    return redis.Redis(connection_pool=_REDIS_POOL)

def get_title():
    key = 'csmn_title'
    url = redis_cli().get(key) or FALLBACK.get(key)
    return url.decode('utf8')

def set_title(title):
    key = 'csmn_title'
    return redis_cli().set(key, title)

def get_video_url():
    key = 'csmn_video_url'
    url = redis_cli().get(key) or FALLBACK.get(key)
    return url.decode('utf8')

def set_video_url(url):
    key = 'csmn_video_url'
    return redis_cli().set(key, url)

def get_backup_urls():
    key = 'csmn_backup_urls'
    urls = redis_cli().lrange(key, 0, -1) or FALLBACK.get(key)
    urls = [json.loads(_url) for _url in urls]
    if urls:
        urls[0]['default'] = True
    return urls

def append_backup_url(name, url):
    key = 'csmn_backup_urls'
    _backup = json.dumps({ 'name': name, 'url': url })
    return redis_cli().rpush(key, _backup)

def set_backup_url(idx, name, url):
    key = 'csmn_backup_urls'
    _backup = json.dumps({ 'name': name, 'url': url })
    return redis_cli().lset(key, idx, _backup)

def remove_backup_url(idx):
    key = 'csmn_backup_urls'
    cursor = 0
    _urls = []
    while cursor < idx:
        _url = redis_cli().lpop(key)
        if not _url:
            break
        _urls.append(_url)
        cursor += 1
    redis_cli().lpop(key)
    while _urls:
        redis_cli().lpush(key, _urls.pop())
    return True

def get_subtitle_url():
    key = 'csmn_subs_url'
    url = redis_cli().get(key) or FALLBACK.get(key, b'')
    return url.decode('utf8')

def set_subtitle_url(start):
    key = 'csmn_subs_url'
    return redis_cli().set(key, start)

def get_start():
    key = 'csmn_start'
    start = redis_cli().get(key) or FALLBACK.get(key, 0)
    return int(float(start))

def set_start(start):
    key = 'csmn_start'
    return redis_cli().set(key, start)

def get_config_ts():
    key = 'csmn_config_update_ts'
    start = redis_cli().get(key) or FALLBACK.get(key, 0)
    return int(float(start))

def update_config_ts():
    key = 'csmn_config_update_ts'
    return redis_cli().set(key, time.time())

@app.route('/api/config', methods=['GET'])
def get_config():
    config = {
        'title': get_title(),
        'start': get_start(),
        'url': get_video_url(),
        'quality': get_backup_urls(),
        'subtitle': {
            'url': get_subtitle_url(),
        },
        'update_ts': get_config_ts(),
    }
    return config

@app.route('/api/config', methods=['POST'])
def set_config():
    key = request.values.get('key')
    val = request.values.get('val')
    code, msg = 0, 'OK'
    try:
        if key == 'url':
            rtn = set_video_url(val)
            update_config_ts()
        elif key == 'subs':
            rtn = set_subtitle_url(val)
            update_config_ts()
        elif key == 'title':
            rtn = set_title(val)
            update_config_ts()
        elif key == 'start':
            start = datetime.strptime(val, '%Y%m%d %H%M')
            rtn = set_start(datetime.timestamp(start))
            update_config_ts()
        elif key == 'cdn':
            cmds = val.split()
            sub = cmds[0]
            # if sub == 'set':
            #     idx, name, url = cmds[1:]
            #     idx = int(idx)
            #     rtn = set_backup_url(idx, name, url)
            if sub == 'add':
                name, url = cmds[1:]
                rtn = append_backup_url(name, url)
                update_config_ts()
            elif sub == 'del':
                idx, = cmds[1:]
                rtn = remove_backup_url(int(idx))
                update_config_ts()
            else:
                code = 2
                msg = 'backup_urls: unsupported sub command: %s' % sub
        else:
            code = 1
            msg = 'not supported: key = %s, val = %s' % (
                key, val
            )
    except Exception as e:
        code = -1
        msg = 'failed to set config: %s' % e
    return {
        'code': code,
        'msg': msg,
    }

if __name__ == "__main__":
    app.run()
