# -*- coding: utf-8 -*-
with open("static/scanner.js", "r", encoding="utf-8") as f:
    content = f.read()

target = """    function formatSommMarkdown(rawText) {
        if (!rawText) return '';
        let escaped = escapeSommHtml(rawText);
        escaped = escaped.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
        const lines = escaped.split('\\n');
        let inList = false;
        let outHtml = '';
        for (let line of lines) {
            const trim = line.trim();
            if (trim.startsWith('•') || trim.startsWith('-') || trim.startsWith('*')) {
                if (!inList) {
                    outHtml += '<ul style="margin: 6px 0; padding-left: 18px;">';
                    inList = true;
                }
                const content = trim.replace(/^[•\\-\\*]\\s*/, '');
                outHtml += `<li style="margin-bottom: 3px;">${content}</li>`;
            } else {
                if (inList) {
                    outHtml += '</ul>';
                    inList = false;
                }
                if (trim.length > 0) {
                    outHtml += `<p style="margin: 0 0 6px 0;">${trim}</p>`;
                }
            }
        }
        if (inList) outHtml += '</ul>';
        return outHtml || escaped;
    }"""

replacement = """    function formatSommMarkdown(rawText) {
        if (!rawText) return '';
        let escaped = escapeSommHtml(rawText);
        escaped = escaped.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
        const lines = escaped.split('\\n');
        let inList = false;
        let outHtml = '';
        for (let line of lines) {
            const trim = line.trim();
            if (trim.startsWith('### ')) {
                if (inList) { outHtml += '</ul>'; inList = false; }
                outHtml += `<h4 style="margin: 6px 0 8px 0; font-size: 14px; font-weight: 700; color: #722F37; line-height: 1.4;">${trim.substring(4)}</h4>`;
            } else if (trim.startsWith('## ')) {
                if (inList) { outHtml += '</ul>'; inList = false; }
                outHtml += `<h3 style="margin: 8px 0 10px 0; font-size: 15px; font-weight: 700; color: #722F37; line-height: 1.4;">${trim.substring(3)}</h3>`;
            } else if (trim.startsWith('•') || trim.startsWith('-') || trim.startsWith('*')) {
                if (!inList) {
                    outHtml += '<ul style="margin: 6px 0; padding-left: 18px;">';
                    inList = true;
                }
                const content = trim.replace(/^[•\\-\\*]\\s*/, '');
                outHtml += `<li style="margin-bottom: 4px; line-height: 1.45;">${content}</li>`;
            } else {
                if (inList) {
                    outHtml += '</ul>';
                    inList = false;
                }
                if (trim.length > 0) {
                    outHtml += `<p style="margin: 0 0 6px 0; line-height: 1.45;">${trim}</p>`;
                }
            }
        }
        if (inList) outHtml += '</ul>';
        return outHtml || escaped;
    }"""

assert target in content, "Target not found"
new_content = content.replace(target, replacement, 1)
with open("static/scanner.js", "w", encoding="utf-8") as f:
    f.write(new_content)
print("SUCCESS: formatSommMarkdown updated to support headings!")
