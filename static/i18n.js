/**
 * VINA Bilingual Localization System (Рус / Eng)
 * Covers all static UI texts, onboarding screens, buttons, filters, modals,
 * wine cards, descriptions, sommelier responses, toasts, and dynamic results.
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'vina_lang';

    function detectInitialLang() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const qLang = urlParams.get('lang');
            if (qLang && (qLang.toLowerCase() === 'en' || qLang.toLowerCase() === 'eng')) {
                localStorage.setItem(STORAGE_KEY, 'en');
                return 'en';
            }
            if (qLang && (qLang.toLowerCase() === 'ru' || qLang.toLowerCase() === 'rus')) {
                localStorage.setItem(STORAGE_KEY, 'ru');
                return 'ru';
            }
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved === 'en' || saved === 'ru') return saved;
        } catch (e) {}
        return 'ru';
    }

    window.appLang = detectInitialLang();
    document.documentElement.lang = window.appLang;

    window.getAppLang = function () {
        return window.appLang || 'ru';
    };

    // =========================================================================
    // 1. AUTOMATIC FETCH INTERCEPTOR (Attaches ?lang=en & X-App-Lang header)
    // =========================================================================
    const _origFetch = window.fetch ? window.fetch.bind(window) : null;
    if (_origFetch) {
        window.fetch = function (input, init) {
            const lang = window.getAppLang();
            try {
                let urlStr = typeof input === 'string' ? input : (input && input.url ? input.url : '');
                if (urlStr && (urlStr.includes('/api/') || urlStr.includes('/v1/'))) {
                    const sep = urlStr.includes('?') ? '&' : '?';
                    if (!urlStr.includes('lang=')) {
                        urlStr = urlStr + sep + 'lang=' + encodeURIComponent(lang);
                    }
                    init = Object.assign({}, init || {});
                    const headers = new Headers(init.headers || {});
                    headers.set('X-App-Lang', lang);
                    init.headers = headers;
                    if (typeof input === 'string') {
                        input = urlStr;
                    }
                }
            } catch (e) {}
            return _origFetch(input, init);
        };
    }

    // =========================================================================
    // 2. EXACT BIDIRECTIONAL DOM TEXT DICTIONARY (RU <-> EN)
    // =========================================================================
    const RU_TO_EN_EXACT = {
        // Brand & Headers
        'Свое вино': 'My Wine',
        'в Свое вино': 'to My Wine',
        'Свое вино | Сканер, Каталог, Карта и Сомелье': 'My Wine | Scanner, Catalog, Map & Sommelier',
        'Онлайн': 'Online',
        'Оффлайн': 'Offline',
        'Локально': 'Local',
        'Туннель': 'Tunnel',
        'Ошибка': 'Error',

        // Onboarding Splash 1..4 & Permissions & Auth
        'Добро пожаловать': 'Welcome',
        'Пожалуйста, подтвердите ваш возраст': 'Please confirm your age to continue',
        'Мне есть 18': 'I am 18 or older',
        'Пропустить': 'Skip',
        'Далее': 'Next',
        'Вино рядом': 'Wine Nearby',
        'Разрешите доступ к геопозиции, чтобы видеть актуальный каталог вашего города и магазины рядом': 'Allow location access to explore the wine catalog in your city and nearby wine boutiques',
        'Разрешить приложению': 'Allow',
        'Свое вино доступ к данным о': 'My Wine to access this device\'s',
        'местоположении устройства?': 'location?',
        'Точно': 'Precise',
        'Приблизительно': 'Approximate',
        'При использовании приложения': 'While using the app',
        'Только в этот раз': 'Only this time',
        'Запретить': 'Don\'t allow',
        'Напомним о важном': 'Stay Updated',
        'Разрешите уведомления, чтобы быть в курсе движения заказа и не пропустить акции и персональные предложения': 'Enable notifications to track your orders and receive exclusive offers and personal wine picks',
        'Свое вино отправлять': 'My Wine to send you',
        'уведомления?': 'notifications?',
        'Разрешить': 'Allow',
        '101 бонус': '101 Bonus Points',
        'за авторизацию': 'for signing in',
        'Получите доступ ко всем возможностям приложения — а мы начислим бонусные баллы на первый заказ': 'Unlock all app features — and get 101 bonus points toward your first order',
        'Авторизоваться': 'Sign In',
        'Введите номер телефона': 'Enter your phone number',
        'Укажите ваш номер для получения кода в СМС': 'Enter your phone number to receive an SMS verification code',
        'Получить код': 'Get Code',
        'Введите код из СМС': 'Enter SMS Code',
        'Отправили код на номер': 'Code sent to',
        'Получить новый код через: 2 минуты 53 секунды': 'Request a new code in: 02:53',
        'Отправить код повторно': 'Resend Code',

        // Navigation & Tabs
        'главная': 'home',
        'Главная': 'Home',
        'каталог': 'catalog',
        'Каталог': 'Catalog',
        'сканер': 'scanner',
        'Сканер': 'Scanner',
        'сомелье': 'sommelier',
        'Сомелье': 'Sommelier',
        'карта': 'map',
        'Карта': 'Map',
        'тосты': 'toasts',
        'Тосты': 'Toasts',
        'Тост': 'Toast',
        'Избранное': 'Favorites',
        'Профиль': 'Profile',
        'Назад на главную': 'Back to Home',
        'Назад в каталог': 'Back to Catalog',
        'Назад к вину': 'Back to Wine',
        'Назад к сканеру': 'Back to Scanner',
        'Вернуться к карточке': 'Back to Wine Card',

        // Home Page
        'Сканер вин — Узнай Свое вино по фото!': 'Wine Scanner — Identify Your Wine by Photo!',
        'Открыть камеру сканера': 'Open Scanner Camera',
        'Винный Сомелье и Мастер тостов': 'AI Wine Sommelier & Toast Master',
        'Вина по цвету': 'Wines by Color',
        'Красное': 'Red',
        'Красное вино': 'Red Wine',
        'Белое': 'White',
        'Белое вино': 'White Wine',
        'Розовое': 'Rosé',
        'Игристое': 'Sparkling',
        'вино': 'wine',
        'вина': 'wines',
        'Популярные вина': 'Popular Wines',
        'Новинки': 'New Arrivals',
        'Тосты по случаям': 'Toasts by Occasion',
        'День': 'Birthday',
        'рождения': 'Celebration',
        'Свадьба': 'Wedding',
        'Встреча': 'Gathering',
        'с друзьями': 'with Friends',
        'Романтический': 'Romantic',
        'вечер': 'Evening',
        'Семья': 'Family',
        'Случайный': 'Random',
        'тост': 'Toast',
        'Московский Хакатон 2026 © "Искры Интеллекта"': 'Moscow Hackathon 2026 © "Sparks of Intelligence"',
        'Связаться с техподдержкой -': 'Contact Support —',

        // Toasts Page
        'Короткие': 'Short',
        'Длинные': 'Long',

        // Favorites & Party Calculator
        '0 вин': '0 wines',
        '1 вино': '1 wine',
        '2 вина': '2 wines',
        '3 вина': '3 wines',
        '4 вина': '4 wines',
        '5 вин': '5 wines',
        '6 вин': '6 wines',
        '7 вин': '7 wines',
        '1 шт.': '1 pc.',
        'Список вин к покупке': 'Wine Shopping List',
        'Скопировать список': 'Copy Shopping List',

        // Profile Page
        'Телефон: не указан': 'Phone: not specified',
        'Бонусный баланс': 'Bonus Balance',
        'Повторить демонстрацию заставок': 'Replay Onboarding Screens',
        'Просмотренные вина': 'Recently Viewed Wines',

        // Scanner View & Result View
        'Наведите камеру на этикетку': 'Point the camera at the wine label',
        'и нажмите кнопку съемки': 'and tap the capture button',
        'Выбрать фото': 'Choose Photo',
        'Анализ этикетки нейросетью...': 'Analyzing wine label with AI...',
        'Уверенность': 'Confidence',
        'Распознано': 'Recognized',
        'Народный рейтинг': 'People\'s Rating',
        '&bull; Средний балл:': '• Average Score:',
        'Всего оценок:': 'Total Ratings:',
        'Ваша оценка: - из 5': 'Your rating: - of 5',
        'Винодельня': 'Winery',
        'Производитель': 'Producer',
        'Описание': 'Description',
        'Исходное фото': 'Original Photo',
        'Сделать новый снимок': 'Take New Photo',
        'Сравнение этикеток': 'Label Comparison',
        'Ваш снимок': 'Your Photo',
        'Эталон базы': 'Catalog Reference',
        'Найденное вино': 'Matched Wine',
        'Это другое вино?': 'Is this a different wine?',
        'Отправить разработчику': 'Send to Developers',
        'Цифровой ИИ-Сомелье VINA': 'VINA Digital AI Sommelier',
        'Загрузка данных сомелье…': 'Loading sommelier insights…',
        'С чем подать?': 'Food Pairing?',
        'Профиль вкуса': 'Taste Profile',
        'Найти аналоги': 'Find Analogs',
        'Спросить': 'Ask',

        // Catalog & Filters
        'Фильтры': 'Filters',
        '⚙ Фильтры вин': '⚙ Wine Filters',
        'Сбросить всё': 'Reset All',
        'Сбросить': 'Reset',
        'Цвет вина': 'Wine Color',
        'Все': 'All',
        'Все вина каталога': 'All Catalog Wines',
        'Сахар / Сухость': 'Sweetness / Dryness',
        'Сухое': 'Dry',
        'Полусухое': 'Off-Dry',
        'Полусладкое': 'Semi-Sweet',
        'Сладкое / Ликерное': 'Sweet / Fortified',
        'Брют': 'Brut',
        'Гастросочетания': 'Food Pairings',
        'Гастропары': 'Food Pairings',
        'BBQ, стейки и гриль': 'BBQ, Steaks & Grill',
        'Рыба и морепродукты': 'Fish & Seafood',
        'Блюда из птицы': 'Poultry Dishes',
        'Брускетты и сыры': 'Bruschetta & Cheeses',
        'Выпечка и десерты': 'Pastries & Desserts',
        'Сорта винограда': 'Grape Varieties',
        'Каберне Совиньон / Фран': 'Cabernet Sauvignon / Franc',
        'Саперави': 'Saperavi',
        'Красностоп': 'Krasnostop',
        'Пино Нуар': 'Pinot Noir',
        'Мерло': 'Merlot',
        'Шардоне': 'Chardonnay',
        'Рислинг': 'Riesling',
        'Совиньон Блан': 'Sauvignon Blanc',
        'Мускат': 'Muscat',
        'Регионы': 'Regions',
        'Крым': 'Crimea',
        'Кубань': 'Kuban',
        'Долина Дона': 'Don Valley',
        'Дагестан': 'Dagestan',
        'Нижняя Волга': 'Lower Volga',
        'Рейтинги и награды': 'Ratings & Awards',
        'Народный рейтинг (от 4.8)': 'People\'s Choice (4.8+)',
        'Высокий рейтинг (от 4.5)': 'High Rating (4.5+)',
        'Подборка ИИ': 'AI Selection',
        'Вина с историей (Ялта 1945)': 'Historical Wines (Yalta 1945)',
        'Вина с': 'Wines with',
        'историей': 'History',
        'Показать вина': 'Show Wines',
        'Загрузка каталога...': 'Loading wine catalog...',
        'Показать ещё': 'Show More',
        'Имение Сикоры': 'Sikory Estate',
        'Абрау-Дюрсо': 'Abrau-Durso',
        'Массандра': 'Massandra',
        'Фанагория': 'Fanagoria',
        'Шато де Талю': 'Chateau de Talu',
        'Ведерниковъ': 'Vedernikov Winery',
        'Мысхако': 'Myskhako',
        'Гай-Кодзор': 'Gai-Kodzor',
        'Новый Свет': 'Novy Svet',
        'Литавщук': 'Litavshchuk',

        // Wine Detail View
        'Фото из каталога': 'Catalog Photo',
        'Нажмите для зума': 'Tap to zoom',
        'Рассмотреть этикетку': 'Inspect Label',
        'Органолептический профиль и баланс вкуса': 'Organoleptic Profile & Taste Balance',
        'С чем подать (совет сомелье)': 'Food Pairing (Sommelier Advice)',
        'Российские аналоги этого вина': 'Russian Analogs of This Wine',
        'История вина': 'Wine History',
        'История вина:': 'Wine History:',
        'Поставь свою оценку': 'Rate This Wine',
        'Спросить сомелье': 'Ask Sommelier',
        'Собрать сет': 'Build a Set',
        'Собрать винный сет': 'Build a Wine Set',

        // Wine Set Modal
        'Выберите количество вин сета от 2 до 7:': 'Choose the number of wines in your set (2 to 7):',
        'Количество вин:': 'Number of wines:',
        'Сет составляется из подобных вин того же стиля, цвета и органолептического баланса на основе искусственного интеллекта.': 'The set is curated by AI from wines of similar style, color, and organoleptic balance.',
        'Готовый винный сет': 'Curated Wine Set',
        'Сет из 4 вин': 'Set of 4 Wines',
        'Изменить число': 'Change Count',
        'Добавить сет в избранное': 'Add Set to Favorites',

        // Map View
        '5 ближайших магазинов пешком': '5 Nearest Stores on Foot',
        'Где я': 'Locate Me',
        'Выбранное вино из каталога:': 'Selected wine from catalog:',
        'Расчет пешего пути...': 'Calculating walking route...',
        'Ведение по маршруту активно': 'Turn-by-turn walking navigation active',
        'Завершить': 'Finish',
        'Выберите магазин и нажмите «Путь» — построится пеший маршрут с GPS-трекингом': 'Select a store and tap "Route" to build a walking path with live GPS tracking',

        // Sommelier Tab & Modal
        'Доказательный сомелье VINA': 'VINA Evidence-Based Sommelier',
        'Гастрономический подбор: Блюдо → Сорт → Бутылка': 'Gastronomic Pairing: Dish → Grape → Bottle',
        'Подбор к блюду': 'Pair with Dish',
        'Нероссийские аналоги': 'World Analogs',
        'Мировые аналоги': 'World Analogs',
        'Мировые аналоги выбранного вина': 'World Analogs of Selected Wine',
        'Знаменитые зарубежные вина с идентичным сортовым и терруарным профилем (до 3-х эталонов):': 'Famous world benchmarks with matching terroir and sensory profiles (up to 3 wines):',
        'Найти российский аналог зарубежному вину': 'Find Russian Twins for Foreign Wines',
        'Любите Шабли, Кьянти или Бордо? Введите название — сомелье подберет до 3-х лучших российских вин из каталога:': 'Love Chablis, Chianti or Bordeaux? Enter the name — sommelier will pick up to 3 best Russian twins from the catalog:',
        'Например: Шабли, Кьянти, Бордо, Риоха...': 'e.g. Chablis, Chianti, Bordeaux, Rioja...',
        'Загрузка мировых аналогов...': 'Loading world analogs...',
        'Подбираем мировые аналоги...': 'Finding world twins...',
        'Подбираем до 3-х лучших российских вин из каталога...': 'Searching up to 3 best Russian twins from the catalog...',
        'сходство': 'match',
        'Российский близнец': 'Russian Twin',
        'Распознанный эталон': 'Recognized Benchmark',
        'Диалог': 'Chat',
        'Подобрать': 'Find Match',
        'Мясо': 'Meat',
        'Стейк Рибай': 'Ribeye Steak',
        'Утка с яблоками': 'Duck with Apples',
        'Рыба': 'Fish',
        'Лосось на гриле': 'Grilled Salmon',
        'Устрицы': 'Oysters',
        'Паста Карбонара': 'Pasta Carbonara',
        'Сыры': 'Cheeses',
        'Тирамису': 'Tiramisu',
        'Аналог Шабли': 'Chablis Analog',
        'Алгоритм сопоставляет жирность, кислотность, танины и вес блюда с закрытым реестром 2108 российских вин.': 'The algorithm matches dish richness, acidity, tannins, and weight against our curated registry of 2,108 Russian wines.',
        'Чат с сомелье': 'Sommelier Chat',
        'Приветствую! Я ваш цифровой ИИ-сомелье.': 'Welcome! I am your Digital AI Sommelier.',
        'Задайте любой вопрос по вину: с чем подать, какой у него вкусовой профиль, или попросите подобрать российские аналоги к вашему ужину.': 'Ask any question about wine: food pairings, flavor profiles, or Russian analogs for your dinner.',
        'Стейк': 'Steak',
        'Блюда': 'Dishes',
        'К чему вы подбираете это вино?': 'What dish are you pairing this wine with?',
        'Экспресс-оценка': 'Quick Check',
        'Вердикт сомелье': 'Sommelier Verdict',
        'Подобрать 3 российских аналога': 'Find 3 Russian Analogs',
        'Авторский тост и историческая справка': 'Signature Toast & Historical Note',
        'Сгенерирует торжественный или душевный тост к текущему вину с исторической отсылкой (Ялта 1945, князь Голицын) и гастрономический совет.': 'Generates a celebratory or heartfelt toast for the selected wine with historical context (Yalta 1945, Prince Golitsyn) and serving advice.',
        'Вино:': 'Wine:',
        'Портвейн Красный Ливадия (Ялта 1945)': 'Livadia Red Port (Yalta 1945)',
        'Мадера Массандра Крымская Выдержанная': 'Massandra Crimean Aged Madeira',
        'Сикоры Рислинг Семейный Резерв': 'Sikory Riesling Family Reserve',
        'Красностоп Золотовский Ведерниковъ': 'Vedernikov Krasnostop Zolotovsky',
        'Голубицкое Эстейт Розе': 'Golubitskoe Estate Rosé',
        'Повод для тоста:': 'Toast Occasion:',
        'Встреча со старыми друзьями': 'Gathering with Old Friends',
        'День рождения / Юбилей': 'Birthday / Anniversary',
        'Романтический вечер / Свидание': 'Romantic Evening / Date',
        'Романтический ужин / Свидание': 'Romantic Dinner / Date',
        'Успешное завершение проекта / Победа': 'Project Launch / Victory',
        'Успешная сделка / Достижение цели': 'Successful Deal / Milestone',
        'Свадебное торжество': 'Wedding Celebration',
        'Ваш вопрос или пожелание:': 'Your question or note:',
        'Сгенерировать тост и совет сомелье': 'Generate Toast & Sommelier Advice',
        'Сгенерировать тост и рекомендацию': 'Generate Toast & Recommendation',

        // Missing Wine, Checkout, Settings, Lightbox & Admin Modals
        'Данного вина нет в базе, отправить разработчику для добавления в базу?': 'This wine is not in our database yet. Send it to the developers to add to the catalog?',
        'Разработчики получат снимок этикетки, распознают сорт и винодельню и внесут карточку в каталог VINA.': 'Our team will receive the label photo, identify the grape and winery, and add the wine card to the VINA catalog.',
        'Отмена': 'Cancel',
        'Спасибо! Снимок передан команде разработки. Мы внесем карточку в каталог.': 'Thank you! The photo has been sent to our development team. We will add this wine to the catalog.',
        '✓ Отправлено разработчикам!': '✓ Sent to Developers!',
        'Закрыть': 'Close',
        'Дашборд сервиса VINA • Запросы вин': 'VINA Service Dashboard • Wine Requests',
        'Анализ запросов пользователей для пополнения каталога новыми позициями': 'Analysis of user requests for adding new wines to the catalog',
        'Обновить': 'Refresh',
        'Закрыть дашборд': 'Close Dashboard',
        'Всего запросов': 'Total Requests',
        'Ожидают добавления': 'Pending Addition',
        'В обработке': 'In Progress',
        'Добавлено в базу': 'Added to Database',
        'Лента нераспознанных бутылок и поисковых запросов': 'Feed of Unrecognized Bottles & Search Queries',
        'Загрузка данных дашборда...': 'Loading dashboard data...',
        'Подключение к инференс-серверу': 'Inference Server Connection',
        'Настройки подключения к серверу': 'Server Connection Settings',
        'Укажите адрес сервера (Cloudflare Tunnel), на котором работает инференс:': 'Enter the server address (Cloudflare Tunnel) running the inference engine:',
        'Проверить связь': 'Test Connection',
        'Сохранить': 'Save',
        'Сбросить на локальный (127.0.0.1:8080)': 'Reset to Local (127.0.0.1:8080)',
        'Просмотр изображения': 'Image Preview',
        'Колесико / щипок для зума • Двойной клик 2.5x': 'Scroll / pinch to zoom • Double-tap 2.5x',
        'Заказ успешно оформлен!': 'Order Successfully Placed!',
        'Спасибо за заказ в «Свое вино»! Мы уже начали собирать ваши выбранные вина.': 'Thank you for ordering with My Wine! We have started preparing your selected wines.',
        'Заказ № VN-84192': 'Order # VN-84192',
        'Количество вин:': 'Number of wines:',
        'Способ получения:': 'Delivery method:',
        'Самовывоз': 'Store Pickup',
        'Сумма заказа:': 'Order Total:',
        'Отлично! Вернуться в каталог': 'Great! Back to Catalog'
    };

    const EN_TO_RU_EXACT = {};
    Object.keys(RU_TO_EN_EXACT).forEach(function (ruKey) {
        const enVal = RU_TO_EN_EXACT[ruKey];
        if (!EN_TO_RU_EXACT[enVal]) {
            EN_TO_RU_EXACT[enVal] = ruKey;
        }
    });

    const PLACEHOLDER_RU_TO_EN = {
        'Поиск вина в каталоге...': 'Search wine in catalog...',
        'Поиск винодельни...': 'Search winery...',
        'Поиск сорта...': 'Search grape variety...',
        'Или укажите любое блюдо (напр.: плов, том ям, пицца)...': 'Or enter any dish (e.g., steak, tom yum, pizza)...',
        'Например: какие закуски подать к столу и что сказать гостям?': 'E.g.: what appetizers to serve and what toast to say to guests?',
        'Напишите вопрос сомелье...': 'Ask the sommelier a question...'
    };
    const PLACEHOLDER_EN_TO_RU = {};
    Object.keys(PLACEHOLDER_RU_TO_EN).forEach(function (k) {
        PLACEHOLDER_EN_TO_RU[PLACEHOLDER_RU_TO_EN[k]] = k;
    });

    const TITLE_RU_TO_EN = {
        'Открыть сканер вин': 'Open Wine Scanner',
        'Открыть Сомелье': 'Open Sommelier',
        'Открыть винного Сомелье': 'Open Wine Sommelier',
        'Поделиться ссылкой': 'Share Link',
        'Карта магазинов рядом': 'Nearby Wine Stores Map',
        'Статус подключения (нажмите для настроек моста)': 'Connection status (tap for bridge settings)',
        'Настройки подключения': 'Connection Settings',
        'Сделать снимок этикетки': 'Capture Label Photo',
        'Открыть фильтры вин на весь экран': 'Open Fullscreen Wine Filters',
        'Нажмите, чтобы рассмотреть бутылку и этикетку': 'Tap to inspect bottle and label',
        'Добавить в Избранное': 'Add to Favorites',
        'Очистить диалог': 'Clear Chat',
        'Закрыть': 'Close',
        'Уменьшить': 'Zoom Out',
        'Увеличить': 'Zoom In',
        'Сбросить': 'Reset'
    };
    const TITLE_EN_TO_RU = {};
    Object.keys(TITLE_RU_TO_EN).forEach(function (k) {
        TITLE_EN_TO_RU[TITLE_RU_TO_EN[k]] = k;
    });

    // =========================================================================
    // 3. UI KEYED TRANSLATION DICTIONARY (window.t)
    // =========================================================================
    const UI_DICT = {
        ru: {
            lang_ru: 'Рус',
            lang_en: 'Eng',
            online: 'Онлайн',
            offline: 'Оффлайн',
            local: 'Локально',
            tunnel: 'Туннель',
            error: 'Ошибка',
            wines_count_0: '0 вин',
            wines_count_1: '1 вино',
            wines_count_2_4: '{n} вина',
            wines_count_5_plus: '{n} вин',
            btls_unit: 'шт.',
            guests_unit: 'чел.',
            art_prefix: 'Арт.',
            alc_suffix: '% об.',
            reviews_word: 'оценок',
            your_rating: 'Ваша оценка: {v} из 5',
            your_rating_empty: 'Ваша оценка: - из 5',
            rate_saved_toast: 'Спасибо! Ваша оценка ({v}/5) учтена в Народном рейтинге',
            Showing_wines: 'Показано {s} из {t} вин',
            loading_catalog: 'Загрузка каталога вин...',
            nothing_found: 'По выбранным фильтрам вин не найдено',
            reset_filters: 'Сбросить фильтры',
            in_favs: 'В избранном',
            add_to_favs: 'В избранное',
            set_of_n_wines: 'Сет из {n} вин',
            set_building: 'Собираем сет из похожих вин...',
            set_added_to_favs: 'Сет №{n} добавлен в Избранное!',
            add_set_to_favs: 'Добавить сет в избранное',
            set_title_num: 'Сет №{n}',
            fav_empty_title: 'В избранном пока нет вин',
            fav_empty_sub: 'Нажимайте на сердечко ♥ на карточках вин в каталоге или на главной, чтобы сохранять любимые позиции и собирать сеты.',
            fav_calc_title: 'Калькулятор вина на компанию',
            fav_calc_sub: 'Мировой стандарт сомелье: <strong>1 бутылка (750 мл) = 5 бокалов по 150 мл</strong>. Норма на вечер — <strong>2–3 бокала</strong> (0.5 бутылки на гостя).',
            fav_calc_guests_lbl: 'Количество гостей:',
            fav_calc_apply_btn: 'Рассчитать количество бутылок на {g} чел. ({b} бут.)',
            fav_select_all: 'Выбрать все',
            fav_deselect_all: 'Снять выбор',
            fav_reset_1: 'Сбросить по 1 шт.',
            fav_banner_calculated: 'На <strong>{g} гостей</strong> рекомендуется <strong>{b} бут.</strong> (по ~2.5 бокала / 375 мл на человека). Количество распределено по выбранным винам!',
            fav_banner_neutral: 'Отметьте галочками вина или сеты ниже и нажмите кнопку расчёта (или настройте количество бутылок вручную).',
            fav_wines_section_title: 'Отдельные вина ({n})',
            fav_qty_label: 'Количество бутылок:',
            fav_set_total_btls: 'Всего: {n} бут.',
            fav_set_plus_one: '+1 к каждой',
            fav_set_for_guests: 'На {g} гостей ({b} бут.)',
            fav_summary_label: 'Итого по выбранным позициям:',
            fav_summary_val: 'Видов вин: <strong>{w}</strong> • Бутылок: <strong>{b} шт.</strong>',
            fav_summary_guests: 'Хватит примерно на ~{g} гостей ({gl} бокалов)',
            fav_shopping_list_btn: 'Список покупок',
            fav_copied_toast: 'Список покупок скопирован в буфер обмена!',
            sms_timer_prefix: 'Получить новый код через: ',
            phone_not_set: 'Телефон: не указан',
            phone_prefix: 'Телефон: ',
            viewed_empty: 'Вы еще не просматривали карточки вин.',
            sensory_acidity: 'Кислотность',
            sensory_tannins: 'Танины',
            sensory_body: 'Тело (Плотность)',
            sensory_sweetness: 'Сладость',
            sensory_oak: 'Дуб и выдержка',
            sensory_acid_high: 'Яркая, хрустящая и освежающая ({v}/5)',
            sensory_acid_mid: 'Гармоничная, свежая ({v}/5)',
            sensory_acid_low: 'Мягкая, деликатная ({v}/5)',
            sensory_tan_high: 'Бархатистые, структурные ({v}/5)',
            sensory_tan_mid: 'Мягкие, округлые ({v}/5)',
            sensory_tan_low: 'Деликатные, без терпкости ({v}/5)',
            sensory_body_high: 'Полнотелое, густое и насыщенное ({v}/5)',
            sensory_body_mid: 'Среднетелое, питкое ({v}/5)',
            sensory_body_low: 'Лёгкое, воздушное ({v}/5)',
            sensory_sweet_high: 'Десертная/полусладкая гармония ({v}/5)',
            sensory_sweet_mid: 'Полусухой мягкий баланс ({v}/5)',
            sensory_sweet_low: 'Благородное сухое ({v}/5)',
            sensory_oak_high: 'Выдержка в дубовых бочках, тона ванили и пряностей ({v}/5)',
            sensory_oak_mid: 'Лёгкий контакт с дубом ({v}/5)',
            sensory_oak_low: 'Свежий фруктовый стиль без дуба ({v}/5)',
            dishes_simple_hdr: 'На каждый день (простые):',
            dishes_unusual_hdr: 'Гастро-эксперимент (необычные):',
            analogs_empty: 'Похожие вина загружаются...',
            history_modern_msg: 'Это вино представляет современную школу российского виноделия — живая классика, создаваемая сегодня.',
            map_route_btn: 'Путь',
            map_in_stock: 'В наличии ({n} бут.)',
            map_walk_min: '{m} мин пешком ({d} м)',
            map_no_stores: 'Поблизости винных магазинов не найдено',
            somm_thinking: 'Сомелье подбирает ответ…',
            somm_error: 'Не удалось связаться с сервером сомелье.'
        },
        en: {
            lang_ru: 'Рус',
            lang_en: 'Eng',
            online: 'Online',
            offline: 'Offline',
            local: 'Local',
            tunnel: 'Tunnel',
            error: 'Error',
            wines_count_0: '0 wines',
            wines_count_1: '1 wine',
            wines_count_2_4: '{n} wines',
            wines_count_5_plus: '{n} wines',
            btls_unit: 'pcs',
            guests_unit: 'guests',
            art_prefix: 'SKU',
            alc_suffix: '% ABV',
            reviews_word: 'ratings',
            your_rating: 'Your rating: {v} of 5',
            your_rating_empty: 'Your rating: - of 5',
            rate_saved_toast: 'Thank you! Your rating ({v}/5) has been added to the People\'s Rating',
            Showing_wines: 'Showing {s} of {t} wines',
            loading_catalog: 'Loading wine catalog...',
            nothing_found: 'No wines found matching your filters',
            reset_filters: 'Reset Filters',
            in_favs: 'In Favorites',
            add_to_favs: 'Add to Favorites',
            set_of_n_wines: 'Set of {n} Wines',
            set_building: 'Curating a set of similar wines...',
            set_added_to_favs: 'Set #{n} added to Favorites!',
            add_set_to_favs: 'Add Set to Favorites',
            set_title_num: 'Set #{n}',
            fav_empty_title: 'No wines in Favorites yet',
            fav_empty_sub: 'Tap the heart ♥ on any wine card in the catalog or home screen to save your favorite bottles and wine sets.',
            fav_calc_title: 'Party Wine Calculator',
            fav_calc_sub: 'World sommelier standard: <strong>1 bottle (750 ml) = 5 glasses (150 ml each)</strong>. Evening norm — <strong>2–3 glasses</strong> (0.5 bottles per guest).',
            fav_calc_guests_lbl: 'Number of guests:',
            fav_calc_apply_btn: 'Calculate bottles for {g} guests ({b} btls)',
            fav_select_all: 'Select All',
            fav_deselect_all: 'Deselect All',
            fav_reset_1: 'Reset to 1 btl each',
            fav_banner_calculated: 'For <strong>{g} guests</strong>, we recommend <strong>{b} btls</strong> (~2.5 glasses / 375 ml per person). Quantities have been distributed across your selected wines!',
            fav_banner_neutral: 'Check the wines or sets below and tap Calculate (or adjust bottle quantities manually).',
            fav_wines_section_title: 'Individual Wines ({n})',
            fav_qty_label: 'Bottle quantity:',
            fav_set_total_btls: 'Total: {n} btls',
            fav_set_plus_one: '+1 to each',
            fav_set_for_guests: 'For {g} guests ({b} btls)',
            fav_summary_label: 'Total for selected items:',
            fav_summary_val: 'Wine types: <strong>{w}</strong> • Bottles: <strong>{b} pcs</strong>',
            fav_summary_guests: 'Enough for ~{g} guests ({gl} glasses)',
            fav_shopping_list_btn: 'Shopping List',
            fav_copied_toast: 'Shopping list copied to clipboard!',
            sms_timer_prefix: 'Request a new code in: ',
            phone_not_set: 'Phone: not specified',
            phone_prefix: 'Phone: ',
            viewed_empty: 'You haven\'t viewed any wine cards yet.',
            sensory_acidity: 'Acidity',
            sensory_tannins: 'Tannins',
            sensory_body: 'Body & Density',
            sensory_sweetness: 'Sweetness',
            sensory_oak: 'Oak & Aging',
            sensory_acid_high: 'Crisp, vibrant, and refreshing ({v}/5)',
            sensory_acid_mid: 'Harmonious and fresh ({v}/5)',
            sensory_acid_low: 'Soft and delicate ({v}/5)',
            sensory_tan_high: 'Velvety and structured ({v}/5)',
            sensory_tan_mid: 'Smooth and rounded ({v}/5)',
            sensory_tan_low: 'Delicate, no astringency ({v}/5)',
            sensory_body_high: 'Full-bodied, rich, and dense ({v}/5)',
            sensory_body_mid: 'Medium-bodied, smooth ({v}/5)',
            sensory_body_low: 'Light and airy ({v}/5)',
            sensory_sweet_high: 'Dessert / semi-sweet harmony ({v}/5)',
            sensory_sweet_mid: 'Off-dry gentle balance ({v}/5)',
            sensory_sweet_low: 'Noble dry style ({v}/5)',
            sensory_oak_high: 'Aged in oak barrels, notes of vanilla and spice ({v}/5)',
            sensory_oak_mid: 'Subtle oak contact ({v}/5)',
            sensory_oak_low: 'Fresh, fruit-forward unoaked style ({v}/5)',
            dishes_simple_hdr: 'Everyday Pairings (Simple):',
            dishes_unusual_hdr: 'Gastronomic Discovery (Unusual):',
            analogs_empty: 'Loading similar wines...',
            history_modern_msg: 'This wine represents the modern school of Russian winemaking — a contemporary classic crafted today.',
            map_route_btn: 'Route',
            map_in_stock: 'In stock ({n} btls)',
            map_walk_min: '{m} min walk ({d} m)',
            map_no_stores: 'No wine stores found nearby',
            somm_thinking: 'Sommelier is preparing an answer…',
            somm_error: 'Could not reach the sommelier server.'
        }
    };

    window.t = function (key, params) {
        const lang = window.getAppLang();
        const table = UI_DICT[lang] || UI_DICT.ru;
        let str = table[key] !== undefined ? table[key] : (UI_DICT.ru[key] || key);
        if (params && typeof params === 'object') {
            Object.keys(params).forEach(function (k) {
                str = str.replace(new RegExp('\\{' + k + '\\}', 'g'), params[k]);
            });
        }
        return str;
    };

    window.formatWineCountI18n = function (n) {
        const num = parseInt(n, 10) || 0;
        if (window.getAppLang() === 'en') {
            return num === 1 ? '1 wine' : (num + ' wines');
        }
        const mod10 = num % 10;
        const mod100 = num % 100;
        if (mod10 === 1 && mod100 !== 11) return num + ' вино';
        if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return num + ' вина';
        return num + ' вин';
    };

    // =========================================================================
    // 4. CLIENT-SIDE WINE CARD & META TRANSLATOR
    // =========================================================================
    const CLIENT_WINERY_MAP = {
        'Массандра': 'Massandra',
        'Фанагория': 'Fanagoria',
        'Абрау-Дюрсо': 'Abrau-Durso',
        'Имение Сикоры': 'Sikory Estate',
        'Винодельня Ведерниковъ': 'Vedernikov Winery',
        'Ведерниковъ': 'Vedernikov Winery',
        'Поместье Голубицкое': 'Golubitskoe Estate',
        'Голубицкое Эстейт': 'Golubitskoe Estate',
        'Золотая Балка': 'Zolotaya Balka',
        'Инкерман': 'Inkerman Winery',
        'Инкерманский ЗМВ': 'Inkerman Winery',
        'Кубань-Вино': 'Kuban-Vino',
        'Шато Тамань': 'Chateau Tamagne',
        'Шато де Талю': 'Chateau de Talu',
        'Мысхако': 'Myskhako Winery',
        'Виноградники Гай-Кодзора': 'Gai-Kodzor Vineyards',
        'Гай-Кодзор': 'Gai-Kodzor Vineyards',
        'Новый Свет': 'Novy Svet Champagne House',
        'Новый Свет. Дом шампанских вин': 'Novy Svet Champagne House',
        'Долина Лефкадия': 'Lefkadia Valley',
        'Скалистый берег': 'Rocky Shore',
        'Солнечная долина': 'Sun Valley',
        'Солнечная Долина': 'Sun Valley',
        'ЗМВ Коктебель': 'Koktebel Winery',
        'Коктебель': 'Koktebel Winery',
        'Дербент Вино': 'Derbent Wine',
        'Усадьба Дивноморское': 'Divnomorskoe Estate',
        'Усадьба Маркотх': 'Markotkh Estate',
        'Усадьба Мезыбь': 'Mezyb Estate',
        'Усадьба Перовских': 'Perovskikh Estate',
        'Криница': 'Krinitsa Winery',
        'Винодельня Бюрнье': 'Burnier Winery',
        'Бюрнье': 'Burnier Winery',
        'Винодельня Узунов': 'Uzunov Winery',
        'Галицкий и Галицкий': 'Galitsky & Galitsky',
        'Николаев и сыновья': 'Nikolaev & Sons',
        'Винодельня России': 'Russian Winery'
    };

    const CLIENT_TITLE_MAP = {
        'Loco Cimbali Blanc de Neige Шардоне': 'Loco Cimbali Blanc de Neige Chardonnay',
        'Усадьба Дивноморское Сира': 'Divnomorskoe Estate Syrah',
        'Имение Сикоры Рислинг Семейный Резерв': 'Sikory Estate Riesling Family Reserve',
        'Сикоры Рислинг Семейный Резерв': 'Sikory Riesling Family Reserve',
        'Ведерниковъ Красностоп Золотовский': 'Vedernikov Krasnostop Zolotovsky',
        'Винодельня Ведерниковъ Красностоп Золотовский': 'Vedernikov Winery Krasnostop Zolotovsky',
        'Поместье Голубицкое Розе Пино Нуар': 'Golubitskoe Estate Rosé Pinot Noir',
        'Голубицкое Эстейт Розе': 'Golubitskoe Estate Rosé',
        'Абрау-Дюрсо Империал Винтаж Брют': 'Abrau-Durso Imperial Vintage Brut',
        'Массандра Портвейн Красный Ливадия': 'Massandra Livadia Red Port',
        'Портвейн Красный Ливадия Массандра': 'Massandra Livadia Red Port',
        'Шато де Талю Каберне Совиньон Резерв': 'Chateau de Talu Cabernet Sauvignon Reserve',
        'Криница Рислинг': 'Krinitsa Riesling',
        'Гай-Кодзор Вионье': 'Gai-Kodzor Viognier',
        'Фанагория 100 Оттенков Красного Саперави': 'Fanagoria 100 Shades of Red Saperavi',
        'Фанагория Автохтон Саперави': 'Fanagoria Autochthon Saperavi',
        'Золотая Балка Брют Розе': 'Zolotaya Balka Brut Rosé',
        'Бюрнье Красностоп': 'Burnier Krasnostop',
        'Альма Вэлли Пино Нуар': 'Alma Valley Pinot Noir',
        'Новый Свет Кюве де Престиж': 'Novy Svet Cuvée de Prestige',
        'Мадера Массандра Крымская Выдержанная': 'Massandra Crimean Aged Madeira'
    };

    window.trWineName = function (title) {
        if (!title) return '';
        if (window.getAppLang() === 'ru') return title;
        if (CLIENT_TITLE_MAP[title]) return CLIENT_TITLE_MAP[title];
        let s = String(title);
        Object.keys(CLIENT_TITLE_MAP).forEach(function (k) {
            if (s.includes(k)) s = s.replace(k, CLIENT_TITLE_MAP[k]);
        });
        const wordReplacements = [
            ['Каберне Совиньон', 'Cabernet Sauvignon'],
            ['Каберне Фран', 'Cabernet Franc'],
            ['Каберне', 'Cabernet'],
            ['Пино Нуар', 'Pinot Noir'],
            ['Пино Гри', 'Pinot Gris'],
            ['Пино Блан', 'Pinot Blanc'],
            ['Совиньон Блан', 'Sauvignon Blanc'],
            ['Шардоне', 'Chardonnay'],
            ['Рислинг', 'Riesling'],
            ['Саперави', 'Saperavi'],
            ['Красностоп Золотовский', 'Krasnostop Zolotovsky'],
            ['Красностоп', 'Krasnostop'],
            ['Мерло', 'Merlot'],
            ['Сира', 'Syrah'],
            ['Шираз', 'Shiraz'],
            ['Вионье', 'Viognier'],
            ['Алиготе', 'Aligoté'],
            ['Мускат', 'Muscat'],
            ['Ркацители', 'Rkatsiteli'],
            ['Кокур', 'Kokur'],
            ['Цимлянский Черный', 'Tsimlyansky Cherny'],
            ['Сибирьковый', 'Sibirkovy'],
            ['Гевюрцтраминер', 'Gewürztraminer'],
            ['Мальбек', 'Malbec'],
            ['Красное', 'Red'],
            ['красное', 'Red'],
            ['Белое', 'White'],
            ['белое', 'White'],
            ['Розовое', 'Rosé'],
            ['розовое', 'Rosé'],
            ['Розе', 'Rosé'],
            ['Игристое', 'Sparkling'],
            ['Сухое', 'Dry'],
            ['сухое', 'Dry'],
            ['Полусухое', 'Off-Dry'],
            ['полусухое', 'Off-Dry'],
            ['Полусладкое', 'Semi-Sweet'],
            ['полусладкое', 'Semi-Sweet'],
            ['Сладкое', 'Sweet'],
            ['сладкое', 'Sweet'],
            ['Брют', 'Brut'],
            ['брют', 'Brut'],
            ['Резерв', 'Reserve'],
            ['Отборное', 'Selected'],
            ['Выдержанное', 'Aged'],
            ['Авторское', 'Winemaker\'s Selection']
        ];
        wordReplacements.forEach(function (pair) {
            s = s.split(pair[0]).join(pair[1]);
        });
        return s;
    };

    window.trWinery = function (winery) {
        if (!winery) return '';
        if (window.getAppLang() === 'ru') return winery;
        return CLIENT_WINERY_MAP[winery] || winery;
    };

    window.trMeta = function (meta) {
        if (!meta) return '';
        if (window.getAppLang() === 'ru') return meta;
        let s = String(meta);
        const pairs = [
            ['Крым, Южный берег', 'Crimea, South Coast'],
            ['Кубань, Таманский п-ов', 'Kuban, Taman Peninsula'],
            ['Кубань, Семигорье', 'Kuban, Semigorye'],
            ['Кубань, Тамань', 'Kuban, Taman'],
            ['Крым', 'Crimea'],
            ['Севастополь', 'Sevastopol'],
            ['Кубань', 'Kuban'],
            ['Геленджик', 'Gelendzhik'],
            ['Долина Дона', 'Don Valley'],
            ['Дагестан', 'Dagestan'],
            ['Нижняя Волга', 'Lower Volga'],
            ['Ставрополье', 'Stavropol'],
            ['Россия', 'Russia'],
            ['Красное', 'Red'],
            ['красное', 'red'],
            ['Белое', 'White'],
            ['белое', 'white'],
            ['Розовое', 'Rosé'],
            ['розовое', 'rosé'],
            ['Игристое', 'Sparkling'],
            ['игристое', 'sparkling'],
            ['Оранжевое', 'Orange'],
            ['Вино', 'Wine'],
            ['экстра-брют', 'extra brut'],
            ['Экстра-брют', 'Extra Brut'],
            ['брют', 'brut'],
            ['Брют', 'Brut'],
            ['полусухое', 'off-dry'],
            ['Полусухое', 'Off-Dry'],
            ['полусладкое', 'semi-sweet'],
            ['Полусладкое', 'Semi-Sweet'],
            ['сладкое', 'sweet'],
            ['Сладкое', 'Sweet'],
            ['десертное', 'dessert'],
            ['ликерное', 'fortified sweet'],
            ['сухое', 'dry'],
            ['Сухое', 'Dry'],
            ['0.75 л', '0.75 L']
        ];
        pairs.forEach(function (p) {
            s = s.split(p[0]).join(p[1]);
        });
        return s;
    };

    window.trWineCardItem = function (w) {
        if (!w || window.getAppLang() === 'ru') return w;
        return Object.assign({}, w, {
            title: window.trWineName(w.title || w.name || ''),
            name: window.trWineName(w.name || w.title || ''),
            winery: window.trWinery(w.winery || ''),
            meta: window.trMeta(w.meta || ''),
            region: window.trMeta(w.region || ''),
            color: window.trMeta(w.color || ''),
            sugar: window.trMeta(w.sugar || ''),
            grape: window.trWineName(w.grape || '')
        });
    };

    // =========================================================================
    // 5. ENGLISH TOASTS BY OCCASION (All 8 Categories matching TOASTS_BY_OCCASION)
    // =========================================================================
    window.TOAST_TITLES_EN = {
        friends: 'Gathering with Friends',
        family: 'Family & Home',
        birthday: 'Birthday Toasts',
        wedding: 'Wedding Toasts',
        romance: 'Romantic Evening',
        long: 'Long Toasts',
        short: 'Short Toasts',
        random: 'Random Toast',
        'Встреча с друзьями': 'Gathering with Friends',
        'Семья': 'Family & Home',
        'День рождения': 'Birthday Toasts',
        'Свадьба': 'Wedding Toasts',
        'Романтический вечер': 'Romantic Evening',
        'Длинные тосты': 'Long Toasts',
        'Короткие тосты': 'Short Toasts',
        'Случайный тост': 'Random Toast'
    };

    window.TOASTS_BY_OCCASION_EN_MAP = {
        friends: [
            "They say fine wine only grows nobler with the years, gaining depth, softness, and an unmistakable bouquet. True friendship is the very same: tested by time, roads, and shared joys, it is priceless. Let's drink to friends who turn any evening into a celebration!",
            "A true friend is someone who knows the melody of your heart and can sing it back to you when you forget the words. May the sunlight of southern vineyards always sparkle in our glasses, and may sincere laughter always ring around this table!",
            "In old Crimean cellars, the finest wines are kept in cool silence, waiting to be uncorked for the dearest guests. Here's to meeting more often, with or without an occasion, and may no distance ever cool our warmth!"
        ],
        family: [
            "Family is the root system of a mighty grapevine. Whatever the winds and seasons, it is the deep roots that nourish the clusters with strength, warmth, and life. Let's raise our glasses to our home, to the health of our elders, and to the bright future of the young!",
            "Where love, respect, and mutual understanding reign, even a simple dinner becomes a royal feast. May comfort, prosperity, and peace always live under the roof of our home, and may every evening together warm the soul!",
            "A person is truly happy when they leave in the morning with joy for the work they love and return home in the evening with even greater joy. To our family — our greatest pillar and inspiration!"
        ],
        birthday: [
            "Every bottle of noble wine holds the sunshine of the summer when the grapes ripened. May every new year of your life be just as sunny and generous with bright victories, warm encounters, and great achievements! Happy Birthday!",
            "May your life sparkle with golden light like the finest aged cuvée, may your health be as strong as a century-old vine, and may your dreams come true effortlessly and beautifully. To the birthday star!",
            "May the most inspiring chapter open in the book of your destiny — full of bold projects, loyal companions, family warmth, and high prosperity. To your health and new heights!"
        ],
        wedding: [
            "Two streams merging into a single river become a mighty current that fears no obstacles. Two grape varieties in the hands of a master winemaker give birth to a grand blend. May your union be harmonious, long, and happy! Cheers to the newlyweds!",
            "Love is the art of hearing each other without words and supporting one another at every moment. May your family hearth burn brightly, may your home be filled with children's laughter, and may your feelings grow deeper and more precious with every passing year, like collector's wine!",
            "Today you lay the foundation of your family fortress. May its walls be strong with mutual trust, its windows bright with joy, and may loved ones always gather around your table! To the bride and groom!"
        ],
        romance: [
            "In the glow of candlelight and the ruby color of wine there is a special magic, when all the noise of the vast world fades into the background and only the two of us remain. To this wonderful evening, to tender glances, and to the music of our hearts!",
            "They say truth is in wine, but in your eyes is an entire universe. Let's drink to moments we wish could last forever, and to feelings that give us wings!",
            "May tonight be remembered for the delicate aroma of the southern breeze, the warmth of your touch, and the feeling of absolute happiness here and now!"
        ],
        long: [
            "Once, a wise winemaker was asked the secret of his wine, which was famous throughout the region. He replied: «The secret is simple — I never rush the vine. In spring I let it drink pure water, in summer I let it warm under the generous southern sun, in autumn I carefully harvest the clusters by hand, and in winter I let the wine rest quietly in an oak barrel.» Life is the same: every great endeavor needs patience, dedication, love, and faith in your dream. Let's drink to all our efforts bearing rich and noble fruit!",
            "High in the mountains grew an ancient grapevine. Travelers passing by marveled at how such sweet and fragrant berries could be born on rocky soil. And the old vineyard master said: «The deeper the roots break through stone toward living water, the stronger the character of the wine.» May any trials in life only make us wiser, stronger, and nobler, and may we always be surrounded by those for whom we want to build, create, and triumph!"
        ],
        short: [
            "May our desires always match our possibilities — and open up new horizons!",
            "May there be only the finest wine in our glasses, and only sincere people in our hearts!",
            "To good health, good fortune, and good news in every new day!",
            "May our home be warm, our endeavors bright, and our hearts at peace!"
        ],
        random: []
    };

    // Additional dynamic UI strings for RU_TO_EN_EXACT
    const EXTRA_RU_TO_EN = {
        'Белое вино': 'White Wine',
        'Красное вино': 'Red Wine',
        'Розовое вино': 'Rosé Wine',
        'Игристое вино': 'Sparkling Wine',
        'Вино': 'Wine',
        'Длинные тосты': 'Long Toasts',
        'Короткие тосты': 'Short Toasts',
        'Кислотность': 'Acidity',
        'Танинность': 'Tannins',
        'Тело / Плотность': 'Body / Density',
        'Сладость': 'Sweetness',
        'Выдержка в дубе': 'Oak Aging',
        'Яркая, освежающая': 'Bright, refreshing',
        'Мягкая, сглаженная': 'Soft, smooth',
        'Бархатные, структурные': 'Velvety, structured',
        'Шелковистые': 'Silky',
        'Полнотелое, глубокое': 'Full-bodied, deep',
        'Средняя плотность': 'Medium body',
        'Десертное / Ликерное': 'Dessert / Fortified',
        'Сухое вино': 'Dry wine',
        'Благородный дуб': 'Noble oak',
        'Благородный кавказский/французский дуб': 'Noble Caucasian/French oak',
        'Легкая выдержка': 'Light oak aging',
        'Легкая бочка': 'Subtle oak',
        'История вина': 'Wine History',
        'Секрет подачи:': 'Serving Secret:',
        'Закрыть историческое досье': 'Close Historical Dossier',
        'Авторский тост сомелье': 'Signature Sommelier Toast',
        'Совет сомелье:': 'Sommelier Advice:',
        'Совет сомелье по подаче': 'Sommelier Serving Advice',
        'Похожие вина из каталога (если захотите альтернативу):': 'Similar Wines from the Catalog (Alternatives):',
        'Близнецы по вкусовому профилю в каталоге:': 'Flavor Profile Twins in the Catalog:',
        'Сомелье готовит авторский тост и подбирает рекомендации...': 'Sommelier is crafting a signature toast and recommendations...',
        'Составление тоста и рекомендаций...': 'Crafting toast and recommendations...',
        'Скопировать': 'Copy',
        '✓ Скопировано!': '✓ Copied!',
        'Открыть в каталоге →': 'Open in Catalog →',
        'Перейти к вину →': 'View Wine →',
        'Логика употребления от сомелье VINA': 'VINA Sommelier Pairing Logic',
        'Рекомендованные блюда с фото и рецептом': 'Recommended Dishes with Photos & Recipes',
        'Простые и необычные': 'Simple & Unusual',
        'Простое': 'Simple',
        'Необычное': 'Gourmet',
        'Вкусовой баланс:': 'Flavor Balance:',
        'Краткий рецепт приготовления:': 'Quick Recipe:',
        'Логика сомелье:': 'Sommelier Logic:',
        'Анализ гастрономической совместимости...': 'Analyzing gastronomic compatibility...',
        'Сопоставление жирности, кислотности и танинов блюда с 2108 винами': 'Matching dish richness, acidity, and tannins across 2,108 wines',
        'Запрашиваем оценку цифрового сомелье...': 'Requesting Digital Sommelier assessment...',
        'Подбираем 3 лучших российских аналога в каталоге...': 'Selecting top 3 Russian analogs in the catalog...',
        'Сомелье анализирует реестр 2108 вин...': 'Sommelier is analyzing the registry of 2,108 wines...',
        'Диалог очищен. Чем могу помочь?': 'Chat cleared. How can I help you?',
        'С чем подать?': 'What to pair with?',
        'Профиль вкуса': 'Flavor Profile',
        'Найти аналоги': 'Find Analogs',
        'Стейк': 'Steak',
        'Калькулятор вина на компанию': 'Party Wine Calculator',
        'Количество гостей:': 'Number of guests:',
        'чел.': 'guests',
        'Рассчитать количество шт. для выбранных': 'Calculate bottles for selected wines',
        'Выбрать все': 'Select all',
        'Снять выбор': 'Deselect all',
        'Количество:': 'Quantity:',
        'шт.': 'pcs',
        'Удалить сет': 'Delete Set',
        'Увеличить сет до 9 шт.': 'Scale set to 9 bottles',
        '➕ +1 к каждой': '➕ +1 to each',
        'Итого к покупке:': 'Total to buy:',
        'Список для покупки': 'Shopping List',
        'У вас пока нет сохраненных вин и сетов в Избранном': 'You have no saved wines or sets in Favorites yet',
        'Выбрать вина': 'Browse Wines',
        'Собираем сет из похожих вин...': 'Building a set of similar wines...',
        'Добавить сет в избранное': 'Add Set to Favorites',
        'Назад к сканеру': 'Back to Scanner',
        'Назад на главную': 'Back to Home',
        'Назад в каталог': 'Back to Catalog',
        'Загрузка карточки вина...': 'Loading wine card...',
        'Загрузка вин...': 'Loading wines...',
        'Вы здесь': 'You are here',
        'Путь': 'Route',
        'Винные магазины поблизости не найдены': 'No nearby wine stores found',
        'Ваша оценка: - из 5': 'Your rating: - of 5',
        'Телефон: не указан': 'Phone: not set',
        'В корзине!': 'In Cart!',
        '✓ Добавлено в корзину': '✓ Added to Cart',
        'Добавить в корзину': 'Add to Cart',
        'В вашей корзине пока пусто': 'Your cart is empty',
        'Выберите понравившиеся российские вина в каталоге или сканере и добавьте их в корзину.': 'Choose your favorite Russian wines in the catalog or scanner and add them to the cart.',
        'Перейти в каталог': 'Go to Catalog',
        'Бесплатно (Самовывоз)': 'Free (In-Store Pickup)',
        'Выберите вина для покупки': 'Select wines to buy',
        'Камера ВКЛ': 'Camera ON',
        'Камера ВЫКЛ': 'Camera OFF',
        'Проверка...': 'Checking...',
        'Офлайн': 'Offline',
        'Онлайн': 'Online'
    };
    Object.keys(EXTRA_RU_TO_EN).forEach(function (k) {
        RU_TO_EN_EXACT[k] = EXTRA_RU_TO_EN[k];
        EN_TO_RU_EXACT[EXTRA_RU_TO_EN[k]] = k;
    });

    // =========================================================================
    // 6. DOM TRANSLATION ENGINE (Walks text nodes, placeholders, titles & blocks)
    // =========================================================================
    function translateCompoundBlocks(lang) {
        // 1. Splash 1 Title
        const sp1Title = document.querySelector('#splash-step-1 .age-gate-title');
        if (sp1Title) {
            sp1Title.innerHTML = lang === 'en'
                ? 'Welcome<br>to My Wine'
                : 'Добро пожаловать<br>в Свое вино';
        }
        // 2. Splash 2 Notif Permission Title
        const notifSheetTitle = document.querySelector('#perm-bottom-sheet .perm-sheet-title');
        if (notifSheetTitle) {
            notifSheetTitle.innerHTML = lang === 'en'
                ? 'Allow <b>My Wine</b> to send<br>you notifications?'
                : 'Разрешить приложению<br>Свое вино отправлять<br>уведомления?';
        }
        // 3. Splash 3 Geo Permission Title
        const geoSheetTitle = document.querySelector('#geo-bottom-sheet .perm-sheet-title');
        if (geoSheetTitle) {
            geoSheetTitle.innerHTML = lang === 'en'
                ? 'Allow <b>My Wine</b> to access<br>this device\'s location?'
                : 'Разрешить приложению<br>Свое вино доступ к данным о<br>местоположении устройства?';
        }
        // 4. Splash 4 Bonus Title
        const sp4Title = document.querySelector('#splash-step-4 .age-gate-title');
        if (sp4Title) {
            sp4Title.innerHTML = lang === 'en'
                ? '101 Bonus Points<br>for signing in'
                : '101 бонус<br>за авторизацию';
        }
        // 5. Home Category Cards (4 wine colors: Белое, Красное, Розовое, Игристое)
        const homeCatCards = document.querySelectorAll('#home-color-scroll .home-cat-card .home-cat-label');
        const catEn = ['White<br>Wine', 'Red<br>Wine', 'Rosé<br>Wine', 'Sparkling<br>Wine'];
        const catRu = ['Белое вино', 'Красное вино', 'Розовое<br>вино', 'Игристое<br>вино'];
        homeCatCards.forEach(function (el, idx) {
            if (idx < 4) el.innerHTML = lang === 'en' ? catEn[idx] : catRu[idx];
        });
        // 6. Catalog Category Plates (6 plates: Все вина, Белое, Красное, Розовое, Игристое, Вина с историей)
        const catScrollCards = document.querySelectorAll('#catalog-category-scroll .home-cat-card .home-cat-label');
        const catPlatesEn = ['All<br>Wines', 'White', 'Red', 'Rosé', 'Sparkling', 'Wines with<br>History'];
        const catPlatesRu = ['Все<br>вина', 'Белое', 'Красное', 'Розовое', 'Игристое', 'Вина с<br>историей'];
        catScrollCards.forEach(function (el, idx) {
            if (idx < 6) el.innerHTML = lang === 'en' ? catPlatesEn[idx] : catPlatesRu[idx];
        });
        // 7. Home Toast Occasion Chips (#home-toasts-chips .home-toast-chip)
        const toastChips = document.querySelectorAll('#home-toasts-chips .home-toast-chip');
        const occChipEn = {
            friends: 'Gathering<br>with Friends',
            family: 'Family',
            birthday: 'Birthday',
            wedding: 'Wedding',
            romance: 'Romantic<br>Evening',
            long: 'Long<br>Toasts',
            short: 'Short<br>Toasts',
            random: 'Random<br>Toast'
        };
        const occChipRu = {
            friends: 'Встреча<br>с друзьями',
            family: 'Семья',
            birthday: 'День<br>рождения',
            wedding: 'Свадьба',
            romance: 'Романтический<br>вечер',
            long: 'Длинные<br>тосты',
            short: 'Короткие<br>тосты',
            random: 'Случайный<br>тост'
        };
        toastChips.forEach(function (btn) {
            const onclickAttr = btn.getAttribute('onclick') || '';
            const span = btn.querySelector('span');
            if (!span) return;
            Object.keys(occChipEn).forEach(function (k) {
                if (onclickAttr.includes("'" + k + "'")) {
                    span.innerHTML = lang === 'en' ? occChipEn[k] : occChipRu[k];
                }
            });
        });
        // 7.1. Sommelier quick query chips
        const sommChips = document.querySelectorAll('.somm-chip-btn');
        sommChips.forEach(function (btn) {
            const txt = (btn.textContent || '').trim();
            if (lang === 'en') {
                if (txt === 'С чем подать?' || txt === 'What to pair with?') {
                    btn.textContent = 'What to pair with?';
                    btn.setAttribute('onclick', "sendSommQuickQuery('What to pair with this wine?')");
                } else if (txt === 'Профиль вкуса' || txt === 'Flavor Profile') {
                    btn.textContent = 'Flavor Profile';
                    btn.setAttribute('onclick', "sendSommQuickQuery('Describe taste, acidity and tannins')");
                } else if (txt === 'Найти аналоги' || txt === 'Find Analogs') {
                    btn.textContent = 'Find Analogs';
                    btn.setAttribute('onclick', "sendSommQuickQuery('Find 3 similar Russian wines')");
                } else if (txt === 'Стейк' || txt === 'Steak') {
                    btn.textContent = 'Steak';
                    btn.setAttribute('onclick', "sendSommQuickQuery('Steak')");
                }
            } else {
                if (txt === 'What to pair with?' || txt === 'С чем подать?') {
                    btn.textContent = 'С чем подать?';
                    btn.setAttribute('onclick', "sendSommQuickQuery('С чем подать это вино?')");
                } else if (txt === 'Flavor Profile' || txt === 'Профиль вкуса') {
                    btn.textContent = 'Профиль вкуса';
                    btn.setAttribute('onclick', "sendSommQuickQuery('Опиши вкус, кислотность и танины')");
                } else if (txt === 'Find Analogs' || txt === 'Найти аналоги') {
                    btn.textContent = 'Найти аналоги';
                    btn.setAttribute('onclick', "sendSommQuickQuery('Подбери 3 похожих российских вина')");
                } else if (txt === 'Steak' || txt === 'Стейк') {
                    btn.textContent = 'Стейк';
                    btn.setAttribute('onclick', "sendSommQuickQuery('Стейк')");
                }
            }
        });

        // 8. Scanner instruction
        const scanInstr = document.querySelector('#scanner-view .scan-instruction');
        if (scanInstr) {
            scanInstr.innerHTML = lang === 'en'
                ? 'Point the camera at the wine label<br>and tap the capture button'
                : 'Наведите камеру на этикетку<br>и нажмите кнопку съемки';
        }
        // 9. Update language switcher pills state
        document.querySelectorAll('.vina-lang-btn').forEach(function (btn) {
            const bLang = btn.getAttribute('data-lang');
            if (bLang === lang) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    window.applyI18nToDOM = function (root) {
        const lang = window.getAppLang();
        const container = root || document.body;
        if (!container) return;

        const textMap = lang === 'en' ? RU_TO_EN_EXACT : EN_TO_RU_EXACT;
        const phMap = lang === 'en' ? PLACEHOLDER_RU_TO_EN : PLACEHOLDER_EN_TO_RU;
        const titleMap = lang === 'en' ? TITLE_RU_TO_EN : TITLE_EN_TO_RU;

        // 1. Walk text nodes
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while ((node = walker.nextNode())) {
            const parentTag = node.parentNode && node.parentNode.tagName;
            if (parentTag === 'SCRIPT' || parentTag === 'STYLE') continue;
            const raw = node.nodeValue;
            if (!raw) continue;
            const trimmed = raw.replace(/\s+/g, ' ').trim();
            if (!trimmed) continue;

            if (textMap[trimmed]) {
                const leading = raw.match(/^\s*/)[0];
                const trailing = raw.match(/\s*$/)[0];
                node.nodeValue = leading + textMap[trimmed] + trailing;
            } else if (lang === 'en') {
                // Dynamic pattern replacements
                let updated = raw;
                updated = updated.replace(/Арт\.\s*(\d+)/g, 'SKU $1');
                updated = updated.replace(/(\d+(?:[.,]\d+)?)\s*%?\s*об\./g, '$1% ABV');
                updated = updated.replace(/\((\d+)\s*оценок\)/g, '($1 ratings)');
                updated = updated.replace(/Сорт:\s*/g, 'Grape: ');
                updated = updated.replace(/Сет из (\d+) вин[а]?/g, 'Set of $1 Wines');
                updated = updated.replace(/Сет №\s*(\d+)/g, 'Set #$1');
                updated = updated.replace(/Показано (\d+) из (\d+) вин/g, 'Showing $1 of $2 wines');
                updated = updated.replace(/(\d+)\s*вин[а]?/g, '$1 wines');
                updated = updated.replace(/(\d+)\s*шт\.?/g, '$1 pcs');
                updated = updated.replace(/(\d+)\s*чел\.?/g, '$1 guests');
                updated = updated.replace(/Ваша оценка:\s*(\S+)\s*из\s*5/g, 'Your rating: $1 of 5');
                updated = updated.replace(/Год создания:\s*(\d+)/g, 'Created in: $1');
                updated = updated.replace(/Историческое досье • Год создания:\s*(\d+)/g, 'Historical Dossier • Created in: $1');
                updated = updated.replace(/⏱\s*(\d+)\s*мин/g, '⏱ $1 min');
                updated = updated.replace(/(\d+)%\s*сходство/g, '$1% match');
                updated = updated.replace(/Другие вина к\s+(.+)/g, 'More wines for $1');
                updated = updated.replace(/Идем пешком в:\s*(.+)/g, 'Walking to: $1');
                updated = updated.replace(/Телефон:\s*\+(\d+)/g, 'Phone: +$1');
                updated = updated.replace(/Заказ №\s*(.+)/g, 'Order #$1');
                updated = updated.replace(/Удалить выбранные \((\d+)\)/g, 'Delete selected ($1)');
                updated = updated.replace(/Остальные избранные вина \((\d+)\)/g, 'Other Favorite Wines ($1)');
                updated = updated.replace(/Хватит на компанию из ~(\d+) чел\. \(по ~3 бокала\)/g, 'Enough for ~ $1 guests (~3 glasses per guest)');
                updated = updated.replace(/\((\d+) сортов\)/g, '($1 varieties)');
                updated = updated.replace(/Итого в сете:\s*/g, 'Total in set: ');
                updated = updated.replace(/(\d+)\s*бонус(?:а|ов)?/g, '$1 Bonus Points');
                if (updated !== raw) {
                    node.nodeValue = updated;
                }
            } else if (lang === 'ru') {
                let updated = raw;
                updated = updated.replace(/SKU\s*(\d+)/g, 'Арт. $1');
                updated = updated.replace(/(\d+(?:[.,]\d+)?)\s*%\s*ABV/g, '$1% об.');
                updated = updated.replace(/\((\d+)\s*ratings\)/g, '($1 оценок)');
                updated = updated.replace(/Grape:\s*/g, 'Сорт: ');
                updated = updated.replace(/Set of (\d+) Wines/g, 'Сет из $1 вин');
                updated = updated.replace(/Set #(\d+)/g, 'Сет №$1');
                updated = updated.replace(/Showing (\d+) of (\d+) wines/g, 'Показано $1 из $2 вин');
                updated = updated.replace(/(\d+)\s*wines/g, '$1 вин');
                updated = updated.replace(/(\d+)\s*pcs/g, '$1 шт.');
                updated = updated.replace(/(\d+)\s*guests/g, '$1 чел.');
                updated = updated.replace(/Your rating:\s*(\S+)\s*of\s*5/g, 'Ваша оценка: $1 из 5');
                updated = updated.replace(/Created in:\s*(\d+)/g, 'Год создания: $1');
                updated = updated.replace(/Historical Dossier • Created in:\s*(\d+)/g, 'Историческое досье • Год создания: $1');
                updated = updated.replace(/⏱\s*(\d+)\s*min/g, '⏱ $1 мин');
                updated = updated.replace(/(\d+)%\s*match/g, '$1% сходство');
                updated = updated.replace(/More wines for\s+(.+)/g, 'Другие вина к $1');
                updated = updated.replace(/Walking to:\s*(.+)/g, 'Идем пешком в: $1');
                updated = updated.replace(/Phone:\s*\+(\d+)/g, 'Телефон: +$1');
                updated = updated.replace(/Order #\s*(.+)/g, 'Заказ № $1');
                updated = updated.replace(/Delete selected \((\d+)\)/g, 'Удалить выбранные ($1)');
                updated = updated.replace(/Other Favorite Wines \((\d+)\)/g, 'Остальные избранные вина ($1)');
                updated = updated.replace(/Enough for ~\s*(\d+) guests \(~3 glasses per guest\)/g, 'Хватит на компанию из ~$1 чел. (по ~3 бокала)');
                updated = updated.replace(/\((\d+) varieties\)/g, '($1 сортов)');
                updated = updated.replace(/Total in set:\s*/g, 'Итого в сете: ');
                updated = updated.replace(/(\d+)\s*Bonus Points/g, '$1 бонус');
                if (updated !== raw) {
                    node.nodeValue = updated;
                }
            }
        }

        // 2. Placeholders & Titles
        const els = container.querySelectorAll ? container.querySelectorAll('[placeholder], [title]') : [];
        els.forEach(function (el) {
            const ph = el.getAttribute('placeholder');
            if (ph && phMap[ph]) el.setAttribute('placeholder', phMap[ph]);
            const ti = el.getAttribute('title');
            if (ti && titleMap[ti]) el.setAttribute('title', titleMap[ti]);
        });

        // 3. Compound HTML blocks
        if (!root || root === document.body) {
            translateCompoundBlocks(lang);
        }
    };

    // =========================================================================
    // 7. LANGUAGE SWITCHER ACTION (Re-renders all active views & persists)
    // =========================================================================
    window.setAppLang = function (lang) {
        const normalized = (lang && String(lang).toLowerCase().startsWith('en')) ? 'en' : 'ru';
        window.appLang = normalized;
        document.documentElement.lang = normalized;
        try {
            localStorage.setItem(STORAGE_KEY, normalized);
        } catch (e) {}

        // 1. Translate static DOM
        window.applyI18nToDOM(document.body);

        // 2. Re-render Home rows (Popular & New Arrivals)
        if (typeof window.initHomePopularRows === 'function') {
            window.initHomePopularRows();
        }

        // 3. Re-render Toasts if Toasts panel is open
        const toastsPanel = document.getElementById('hub-panel-toasts');
        if (toastsPanel && toastsPanel.classList.contains('active') && typeof window.openToastCategoryPage === 'function' && window.currentToastCategoryKey) {
            window.openToastCategoryPage(window.currentToastCategoryKey, window.currentToastCategoryTitle || '');
        }

        // 4. Re-render Favorites & Party Calculator
        if (typeof window.renderFavoritesPanel === 'function') {
            const favPanel = document.getElementById('hub-panel-favorites');
            if (favPanel && favPanel.classList.contains('active')) {
                window.renderFavoritesPanel();
            }
        }
        if (typeof window.updateFavBadge === 'function') {
            window.updateFavBadge();
        }

        // 5. Re-render Profile if open
        if (typeof window.renderProfileWines === 'function') {
            const profPanel = document.getElementById('hub-panel-profile');
            if (profPanel && profPanel.classList.contains('active')) {
                window.renderProfileWines();
            }
        }

        // 6. Reload Catalog & Facets if Catalog was loaded or is active
        if (typeof window.loadCatalogFacetsIntoSidebar === 'function') {
            window.loadCatalogFacetsIntoSidebar();
        }
        if (typeof window.fetchCatalogWines === 'function') {
            const catPanel = document.getElementById('hub-panel-catalog');
            if (catPanel && catPanel.classList.contains('active')) {
                window.CURRENT_CATALOG_ITEMS = [];
                window.fetchCatalogWines(false);
            }
        }

        // 7. Reload Wine Detail view if open
        const detailView = document.getElementById('catalog-detail-view');
        if (detailView && detailView.style.display !== 'none' && window.currentDetailWineSlug && typeof window.openWineDetail === 'function') {
            window.openWineDetail(window.currentDetailWineSlug, window.wineDetailSource || 'catalog');
        }

        // 8. Reload Scanner Result view if open
        const resultView = document.getElementById('result-view');
        if (resultView && resultView.classList.contains('active') && window.currentScannedSlug && typeof window.showScannerResultView === 'function') {
            window.showScannerResultView(window.currentScannedSlug);
        }

        // 9. Reload Map stores if Map is active
        const mapPanel = document.getElementById('hub-panel-map');
        if (mapPanel && mapPanel.classList.contains('active') && typeof window.load5NearbyWalkingStores === 'function') {
            window.load5NearbyWalkingStores();
        }

        // 10. Re-render Sommelier World Analogs if active
        const worldView = document.getElementById('somm-modal-view-world-analogs');
        if (worldView && worldView.style.display !== 'none' && typeof window.loadWorldAnalogsView === 'function') {
            window.loadWorldAnalogsView();
        }

        // 10. Dispatch custom event
        try {
            window.dispatchEvent(new CustomEvent('vina-lang-change', { detail: { lang: normalized } }));
        } catch (e) {}
    };

    // Run on DOMContentLoaded and observe dynamic mutations
    document.addEventListener('DOMContentLoaded', function () {
        window.applyI18nToDOM(document.body);

        let debounceTimer = null;
        const observer = new MutationObserver(function () {
            if (debounceTimer) clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                window.applyI18nToDOM(document.body);
            }, 60);
        });
        observer.observe(document.body, { childList: true, subtree: true });
    });
})();
