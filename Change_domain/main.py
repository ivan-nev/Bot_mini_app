from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

NEW_URL = "https://vikunja.calc.press"

HTML_PAGE = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Сервис переехал — Vikunja</title>
    <meta name="robots" content="noindex">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #2c3e50;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            padding: 48px 40px;
            max-width: 460px;
            width: 100%;
            text-align: center;
        }}
        .logo {{
            font-size: 28px;
            font-weight: 700;
            color: #1973ff;
            margin-bottom: 24px;
        }}
        h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 12px; }}
        p {{ font-size: 15px; color: #6b7280; margin-bottom: 28px; }}
        .new-url {{
            display: inline-block;
            background: #f0f4ff;
            color: #1973ff;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 14px;
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 28px;
            text-decoration: none;
            word-break: break-all;
        }}
        .btn {{
            display: inline-block;
            background: #1973ff;
            color: #fff;
            font-size: 15px;
            font-weight: 500;
            padding: 12px 32px;
            border-radius: 8px;
            text-decoration: none;
        }}
        .btn:hover {{ background: #1259cc; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">Vikunja</div>
        <h1>Мы переехали</h1>
        <p>Сервис доступен по новому адресу:</p>
        <a class="new-url" href="{NEW_URL}">{NEW_URL}</a>
        <br>
        <a class="btn" href="{NEW_URL}">Перейти на новый сайт</a>
    </div>
</body>
</html>"""


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def moved(full_path: str):
    return HTML_PAGE