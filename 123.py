import requests
from Bot.config.config import load_config

config = load_config()
TOKEN = config.tg_bot.token
WEB_APP_URL = "https://miniapp.calc.press/stubacme-calc"

# Установка Menu Button
url = f"https://api.telegram.org/bot{TOKEN}/setChatMenuButton"
params = {
    "menu_button": {
        "type": "web_app",
        "text": "🔺 Калькулятор резьбы",
        "web_app": {
            "url": WEB_APP_URL
        }
    }
}

response = requests.post(url, json=params)
print(response.json())
