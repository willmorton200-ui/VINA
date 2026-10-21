with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = '<!-- МОДАЛЬНОЕ ОКНО: ВИНО НЕ НАЙДЕНО В КАТАЛОГЕ'

stub_modal = """    <!-- МОДАЛЬНОЕ ОКНО: ТОЧКА ВХОДА СОМЕЛЬЕ (ЗАГЛУШКА ДЛЯ ИНТЕГРАЦИИ ИЗ ДРУГОГО ПРОЕКТА) -->
    <div class="somm-stub-modal-overlay" id="sommelier-stub-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.65); backdrop-filter: blur(4px); z-index: 10005; align-items: center; justify-content: center; padding: 20px;" onclick="if(event.target.id==='sommelier-stub-modal') closeSommelierStubModal()">
        <div class="somm-stub-modal-card" style="background: #ffffff; border-radius: 20px; max-width: 440px; width: 100%; padding: 26px 22px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); position: relative;">
            <div style="display: inline-block; background: #fff3cd; border: 1px solid #ffeeba; color: #856404; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px; margin-bottom: 14px; letter-spacing: 0.5px;">
                ⚡ ТОЧКА ВХОДА СОМЕЛЬЕ / ENTRY POINT
            </div>
            <div style="width: 60px; height: 60px; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center; background: #fdf2f4; border-radius: 50%;">
                <img src="img/glass_filled_straight.png" style="width: 30px; height: 40px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);" alt="Сомелье">
            </div>
            <h3 style="margin: 0 0 8px 0; font-size: 20px; font-weight: 700; color: #1a1a1a;">Цифровой ИИ-Сомелье</h3>
            <p style="margin: 0 0 16px 0; font-size: 14px; color: #495057; line-height: 1.55;">
                Сервис интеллектуального сомелье подготовлен для подключения из внешнего проекта / микросервиса.
            </p>
            <div style="background: #f8f9fa; border: 1px dashed #ced4da; border-radius: 12px; padding: 12px 14px; text-align: left; margin-bottom: 20px; font-size: 12.5px; color: #495057;">
                <div style="margin-bottom: 6px;"><strong>Точка интеграции (JS Handler):</strong><br><code style="color: var(--primary, #800020); font-size: 11.5px; word-break: break-all;">window.openSommelierEntryPoint(wineSlug, wineData)</code></div>
                <div><strong>Выбранное вино:</strong> <span id="somm-stub-wine-name" style="font-weight: 600; color: #1a1a1a;">—</span></div>
            </div>
            <button type="button" class="btn btn-primary" onclick="closeSommelierStubModal()" style="width: 100%; border-radius: 12px; padding: 12px; font-weight: 700; font-size: 14px;">
                Понятно
            </button>
        </div>
    </div>

    """

if target in html:
    html = html.replace(target, stub_modal + target, 1)
    print("Added sommelier stub modal to scanner.html")
else:
    print("Target comment not found in scanner.html")

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)
