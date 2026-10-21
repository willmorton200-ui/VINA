with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

old_sticky_css = """.btn-sticky-somm {
    flex: 0 0 130px;
    height: 44px;
    background: #ffffff;
    border: 1.5px solid var(--primary, #800020);
    color: var(--primary, #800020);
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
    font-family: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    transition: background 0.15s ease, transform 0.12s ease;
}

.btn-sticky-somm:hover {
    background: #fdf2f4;
    transform: translateY(-1px);
}

.btn-sticky-cart {
    flex: 1;
    height: 44px;
    background: var(--primary, #800020);
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
    font-family: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(128, 0, 32, 0.25);
    transition: background 0.15s ease, transform 0.12s ease;
}

.btn-sticky-cart:hover {
    background: var(--primary-light, #a31c3b);
    transform: translateY(-1px);
}

.btn-sticky-cart.added {
    background: #28a745;
}"""

new_sticky_css = """.btn-sticky-somm {
    flex: 1;
    height: 44px;
    background: #ffffff;
    border: 1.5px solid var(--primary, #722F37);
    color: var(--primary, #722F37);
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
    font-family: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    transition: background 0.15s ease, transform 0.12s ease;
}

.btn-sticky-somm:hover {
    background: #fdf2f4;
    transform: translateY(-1px);
}

.btn-sticky-map {
    flex: 1;
    height: 44px;
    background: var(--primary, #722F37);
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
    font-family: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(114, 47, 55, 0.25);
    transition: background 0.15s ease, transform 0.12s ease;
}

.btn-sticky-map:hover {
    background: #873842;
    transform: translateY(-1px);
}

.btn-sticky-cart {
    display: none !important;
}"""

assert old_sticky_css in css, "old_sticky_css not found"
css = css.replace(old_sticky_css, new_sticky_css, 1)

with open('static/scanner.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Updated scanner.css for btn-sticky-map successfully!")
