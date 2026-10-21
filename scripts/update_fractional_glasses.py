import os

# Update static/scanner.js
with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

old_fn_js = '''    function renderGlassesStripHtml(score) {
        const s = Math.max(0, Math.min(5, parseFloat(score) || 0));
        let html = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= Math.floor(s)) {
                html += '<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);">';
            } else if (i === Math.ceil(s) && (s % 1 >= 0.25)) {
                html += '<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%); opacity: 0.8;">';
            } else {
                html += '<img src="img/glass_empty_straight.png" class="strip-glass-icon empty" alt="" style="width: 17px; height: 23px; object-fit: contain; opacity: 0.45; filter: grayscale(100%);">';
            }
        }
        return html;
    }'''

new_fn_js = '''    function renderGlassesStripHtml(score) {
        const s = Math.max(0, Math.min(5, parseFloat(score) || 0));
        let html = '';
        for (let i = 1; i <= 5; i++) {
            let fillPct = 0;
            if (s >= i) {
                fillPct = 100;
            } else if (s > i - 1) {
                fillPct = Math.round((s - (i - 1)) * 100);
            } else {
                fillPct = 0;
            }
            html += '<span class="fractional-glass-box" title="' + s + ' / 5">' +
                    '<img src="img/glass_empty_straight.png" class="glass-bg" alt="">' +
                    (fillPct > 0 ? '<span class="glass-fill-wrap" style="width: ' + fillPct + '%;"><img src="img/glass_filled_straight.png" class="glass-fg" alt=""></span>' : '') +
                    '</span>';
        }
        return html;
    }'''

if '\r\n' in js:
    js = js.replace(old_fn_js.replace('\n', '\r\n'), new_fn_js.replace('\n', '\r\n'), 1)
else:
    js = js.replace(old_fn_js, new_fn_js, 1)

with open('static/scanner.js', 'w', encoding='utf-8', newline='') as f:
    f.write(js)
print('scanner.js updated')

# Update static/scanner.html
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_fn_html = '''        function renderGlassesStripHtml(score) {
            const s = Math.max(0, Math.min(5, parseFloat(score) || 0));
            let html = '';
            for (let i = 1; i <= 5; i++) {
                if (i <= Math.floor(s)) {
                    html += `<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);">`;
                } else if (i === Math.ceil(s) && (s % 1 >= 0.25)) {
                    html += `<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%); opacity: 0.8;">`;
                } else {
                    html += `<img src="img/glass_empty_straight.png" class="strip-glass-icon empty" alt="" style="width: 17px; height: 23px; object-fit: contain; opacity: 0.45; filter: grayscale(100%);">`;
                }
            }
            return html;
        }'''

new_fn_html = '''        function renderGlassesStripHtml(score) {
            const s = Math.max(0, Math.min(5, parseFloat(score) || 0));
            let html = '';
            for (let i = 1; i <= 5; i++) {
                let fillPct = 0;
                if (s >= i) {
                    fillPct = 100;
                } else if (s > i - 1) {
                    fillPct = Math.round((s - (i - 1)) * 100);
                } else {
                    fillPct = 0;
                }
                html += '<span class="fractional-glass-box" title="' + s + ' / 5">' +
                        '<img src="img/glass_empty_straight.png" class="glass-bg" alt="">' +
                        (fillPct > 0 ? '<span class="glass-fill-wrap" style="width: ' + fillPct + '%;"><img src="img/glass_filled_straight.png" class="glass-fg" alt=""></span>' : '') +
                        '</span>';
            }
            return html;
        }'''

if '\r\n' in html:
    html = html.replace(old_fn_html.replace('\n', '\r\n'), new_fn_html.replace('\n', '\r\n'), 1)
else:
    html = html.replace(old_fn_html, new_fn_html, 1)

with open('static/scanner.html', 'w', encoding='utf-8', newline='') as f:
    f.write(html)
print('scanner.html updated')
