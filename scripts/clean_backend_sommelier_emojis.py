import re

def clean_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Specific replacements in stores_and_history.py
    content = content.replace("🎂 Тост на День рождения:", "Тост на День рождения:")
    content = content.replace("❤️ Тост для свидания и особенного вечера:", "Тост для свидания и особенного вечера:")
    content = content.replace("🥂 Тост для встречи друзей:", "Тост для встречи друзей:")
    content = content.replace("🏆 Тост за успех, проект и победу:", "Тост за успех, проект и победу:")
    content = content.replace("💡 **Совет сомелье по подаче", "**Совет сомелье по подаче")
    content = content.replace("🎯 **Ответ на ваш вопрос", "**Ответ на ваш вопрос")
    content = content.replace("👑 Император Николай II", "Император Николай II")
    content = content.replace("🚩 Иосиф Сталин", "Иосиф Сталин")
    content = content.replace("🦅 Франклин Рузвельт", "Франклин Рузвельт")
    content = content.replace("🎩 Уинстон Черчилль", "Уинстон Черчилль")
    content = content.replace("✒️ Антон Чехов", "Антон Чехов")
    content = content.replace("📚 Александр Куприн", "Александр Куприн")

    # Specific replacements in pairing_engine.py
    content = content.replace("🎯 Близнец по вкусу", "Близнец по вкусу")
    content = content.replace("💎 Выгодная альтернатива", "Выгодная альтернатива")
    content = content.replace("💎 Выгоднее по цене", "Выгоднее по цене")
    content = content.replace("👑 На ступень выше", "На ступень выше")
    content = content.replace("🔄 Похожий профиль", "Похожий профиль")
    content = content.replace("🔥 Идеальная синергия", "Идеальная синергия")
    content = content.replace("👍 Хороший выбор", "Хороший выбор")
    content = content.replace("👑 Классическая гармония", "Классическая гармония")
    content = content.replace("💎 Лучшая цена / качество", "Лучшая цена / качество")

    # Strip emojis from sensory tags
    tags_to_clean = [
        "🔥 Дым и угли", "Дым и угли",
        "🥩 Сочная мраморность", "Сочная мраморность",
        "🧈 Тающее травяное масло", "Тающее травяное масло",
        "🍒 Кисло-сладкая вишня", "Кисло-сладкая вишня",
        "🦆 Хрустящая корочка", "Хрустящая корочка",
        "🍷 Глянцевый демигляс", "Глянцевый демигляс",
        "🍋 Звонкий лайм", "Звонкий лайм",
        "🐚 Нежная текстура", "Нежная текстура",
        "🧈 Сливочная эмульсия", "Сливочная эмульсия",
        "🧀 Сливочный желток и сыр", "Сливочный желток и сыр",
        "🥓 Хрустящий гуанчале", "Хрустящий гуанчале",
        "🌶 Черный перец", "Черный перец",
        "🧀 Тягучая сливочность", "Тягучая сливочность",
        "🍯 Горный мед", "Горный мед",
        "🌰 Хрустящий пекан", "Хрустящий пекан",
        "🌶 Огненный чили", "Огненный чили",
        "🥭 Спелое манго", "Спелое манго",
        "🌿 Свежий лемонграсс", "Свежий лемонграсс",
        "🍖 Тающие волокна", "Тающие волокна",
        "🌿 Пряные травы и чеснок", "Пряные травы и чеснок",
        "💎 Рубиновый гранат", "Рубиновый гранат",
        "🐟 Нежный лосось", "Нежный лосось",
        "🥑 Кремовое авокадо", "Кремовое авокадо",
        "🍊 Цитрусовый понзу", "Цитрусовый понзу"
    ]
    for i in range(0, len(tags_to_clean), 2):
        content = content.replace(f'"{tags_to_clean[i]}"', f'"{tags_to_clean[i+1]}"')

    # Remove icons in rules
    content = re.sub(r'icon="[^"]+"', 'icon=""', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Cleaned {path}")

clean_file('sommelier/stores_and_history.py')
clean_file('sommelier/pairing_engine.py')
