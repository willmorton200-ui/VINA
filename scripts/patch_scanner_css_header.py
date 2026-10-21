with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

old_panels = """#hub-panel-home,
#hub-panel-toasts,
#hub-panel-favorites,
#hub-panel-cart,
#hub-panel-profile {
    padding: 0 !important;
}"""

new_panels = """#hub-panel-home,
#hub-panel-toasts,
#hub-panel-favorites,
#hub-panel-cart,
#hub-panel-profile,
#hub-panel-catalog {
    padding: 0 !important;
}"""

assert old_panels in css, "old_panels not found"
css = css.replace(old_panels, new_panels, 1)

old_search_css = """.home-search-bar {
    display: flex;
    align-items: center;
    background: #ededf0;
    border-radius: 12px;
    padding: 0 10px 0 14px;
    height: 46px;
    margin-bottom: 20px;
    gap: 8px;
}"""

new_search_css = """.home-search-bar {
    display: flex;
    align-items: center;
    background: #ededf0;
    border-radius: 12px;
    padding: 0 10px 0 14px;
    height: 46px;
    margin-bottom: 10px;
    gap: 8px;
}"""

assert old_search_css in css, "old_search_css not found"
css = css.replace(old_search_css, new_search_css, 1)

with open('static/scanner.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Updated scanner.css successfully!")
