# Setup

0. create `bot_token.py` with tg bot token in it; e.g.
    ```python
    TOKEN = 'tg_bot_token'
    ```
1. `virtualenv --python=python3 py3`
2. `source py3/bin/activate`
3. `pip install -r requirements.txt`

# Run bot and api server

0. You need a redis server running on `localhost:6379`
1. `python api.py`
2. `python bot.py`, or `python bot.py dev` if you have a socks proxy server working on `socks5://127.0.0.1:1080`

