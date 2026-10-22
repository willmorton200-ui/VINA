with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Update relative fetches to apiUrl
js = js.replace(
    "await fetch('/api/sommelier/reset', {",
    "await fetch(apiUrl('/api/sommelier/reset'), {"
)
js = js.replace(
    "const res = await fetch('/api/sommelier/ask', {",
    "const res = await fetch(apiUrl('/api/sommelier/ask'), {"
)
js = js.replace(
    "const res = await fetch('/api/sommelier/pairing/dish', {",
    "const res = await fetch(apiUrl('/api/sommelier/pairing/dish'), {"
)
js = js.replace(
    "const res = await fetch('/api/v2/sommelier/ask', {",
    "const res = await fetch(apiUrl('/api/v2/sommelier/ask'), {"
)

# 2. Improve Sommelier error handling in catch block
old_err_block = """            const errEl = document.createElement('div');
            errEl.className = 'somm-msg somm-msg-assistant';
            errEl.style.cssText = 'display: flex; gap: 10px; align-items: flex-start;';
            errEl.innerHTML = `
                <div style="width: 32px; height: 32px; border-radius: 50%; background: #fdf2f4; border: 1px solid #f8d7da; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    <img src="svg/public-rating.svg" style="width: 18px; height: 18px; object-fit: contain;">
                </div>
                <div style="background: #fff5f5; border: 1px solid #fed7d7; border-radius: 4px 16px 16px 16px; padding: 12px 16px; font-size: 13px; color: #c53030;">
                    Не удалось получить ответ от сомелье. Проверьте соединение и попробуйте еще раз.
                </div>
            `;
            messagesBox.appendChild(errEl);"""

new_err_block = """            const isRemote = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' && window.location.port !== '8080';
            const hasApi = !!localStorage.getItem('vina_api_url');
            let hint = 'Проверьте соединение и попробуйте еще раз.';
            let actionBtn = '';
            if (isRemote && !hasApi) {
                hint = 'Сайт открыт удаленно, но адрес туннеля не настроен. Запустите start_tunnel.bat на ПК и укажите адрес в настройках.';
                actionBtn = '<div style="margin-top: 8px;"><button type="button" onclick="if(window.openBridgeSettings) window.openBridgeSettings();" style="background: #722F37; color: #fff; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer;">Настроить подключение</button></div>';
            } else if (isRemote) {
                hint = 'Не удалось связаться с домашним сервером через туннель. Проверьте, запущены ли start_app.bat и start_tunnel.bat на вашем ПК.';
                actionBtn = '<div style="margin-top: 8px;"><button type="button" onclick="if(window.openBridgeSettings) window.openBridgeSettings();" style="background: #722F37; color: #fff; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer;">Проверить адрес туннеля</button></div>';
            }
            const errEl = document.createElement('div');
            errEl.className = 'somm-msg somm-msg-assistant';
            errEl.style.cssText = 'display: flex; gap: 10px; align-items: flex-start;';
            errEl.innerHTML = `
                <div style="width: 32px; height: 32px; border-radius: 50%; background: #fdf2f4; border: 1px solid #f8d7da; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    <img src="svg/public-rating.svg" style="width: 18px; height: 18px; object-fit: contain;">
                </div>
                <div style="background: #fff5f5; border: 1px solid #fed7d7; border-radius: 4px 16px 16px 16px; padding: 12px 16px; font-size: 13px; color: #c53030; max-width: 90%;">
                    <div style="font-weight: 700; margin-bottom: 4px;">Не удалось получить ответ от сомелье</div>
                    <div style="line-height: 1.45;">${hint}</div>
                    ${actionBtn}
                </div>
            `;
            messagesBox.appendChild(errEl);"""

if old_err_block in js:
    js = js.replace(old_err_block, new_err_block)
    print("Error block replaced successfully in scanner.js")
else:
    # try replacing with CRLF
    old_crlf = old_err_block.replace('\n', '\r\n')
    new_crlf = new_err_block.replace('\n', '\r\n')
    if old_crlf in js:
        js = js.replace(old_crlf, new_crlf)
        print("Error block replaced (CRLF) in scanner.js")
    else:
        print("Warning: old_err_block not matched in scanner.js")

with open('static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("scanner.js updated with apiUrl for sommelier endpoints.")


# Update static/scanner.html
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_get_base = """        function getHubApiBase() {
            const inp = document.getElementById('input-api-url');
            if (inp && inp.value && inp.value.trim()) {
                return inp.value.trim().replace(/\/+$/, '');
            }
            const saved = localStorage.getItem('vina_api_url') || '';
            return saved.replace(/\/+$/, '');
        }"""

new_get_base = """        function getHubApiBase() {
            try {
                const urlParams = new URLSearchParams(window.location.search);
                const apiParam = urlParams.get('api');
                if (apiParam) {
                    const clean = apiParam.trim().replace(/\/+$/, '');
                    localStorage.setItem('vina_api_url', clean);
                    return clean;
                }
            } catch(e) {}
            const inp = document.getElementById('input-api-url');
            if (inp && inp.value && inp.value.trim()) {
                return inp.value.trim().replace(/\/+$/, '');
            }
            const saved = localStorage.getItem('vina_api_url') || '';
            if (saved) return saved.replace(/\/+$/, '');
            if (window.location.protocol === 'file:') return 'http://127.0.0.1:8080';
            return '';
        }"""

if old_get_base in html:
    html = html.replace(old_get_base, new_get_base)
    print("getHubApiBase replaced in scanner.html")
else:
    old_crlf = old_get_base.replace('\n', '\r\n')
    new_crlf = new_get_base.replace('\n', '\r\n')
    if old_crlf in html:
        html = html.replace(old_crlf, new_crlf)
        print("getHubApiBase replaced (CRLF) in scanner.html")
    else:
        print("Warning: old_get_base not matched in scanner.html")

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("scanner.html updated with auto ?api= parameter support.")
