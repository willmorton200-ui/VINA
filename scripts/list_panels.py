import re

content = open('static/scanner.html', encoding='utf-8').read()
panels = re.findall(r'id=[\'"](hub-panel-[^\'"]+)[\'"]', content)
print('Hub panels:', panels)
