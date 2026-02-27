class AmplitudeEventTranslations:
    EVENTS_RU = {
        '[Amplitude] Application Opened': 'Приложение открыто',
        '[Amplitude] Application Backgrounded': 'Приложение свернуто',
        '[Amplitude] Application Updated': 'Приложение обновлено',
        '[Amplitude] Application Installed': 'Приложение установлено',
        'session_start': 'Начало сессии',
        'page_opened': 'Открыт экран',
        'push_opened': 'Открыто push-уведомление',
        'notification_opened_app': 'Открытие приложения из уведомления',
        'achievements_page_viewed': 'Открыт экран достижений',
        'achievement_page_viewed': 'Открыта страница достижения',
        'achievement_card_clicked': 'Клик по карточке достижения',
        'achievement_reward_claimed_page': 'Открыта страница получения награды',
        'achievement_completed': 'Достижение выполнено',
        'story_tapped': 'Нажатие на сторис',
        'wheel_of_fortune_closed': 'Колесо фортуны закрыто',
        'wheel_of_fortune_wheel_initialized': 'Колесо фортуны инициализировано',
        'wheel_of_fortune_spin': 'Прокрутка колеса фортуны',
        'crystal_tapped': 'Нажатие на кристалл',
        'refill_with_merchant_success': 'Успешное пополнение через мерчанта',
        'restaurant_waiter_call_success': 'Успешный вызов официанта',
        'qr_code_scanned': 'QR-код отсканирован',
    }

    @classmethod
    def translate(cls, event_name: str) -> str:
        normalized = (event_name or '').strip()
        if not normalized:
            return ''

        return cls.EVENTS_RU.get(normalized, normalized)
