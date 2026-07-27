# The Hub Bot

Единая Telegram-точка входа для моих независимых приложений.

```
The Hub
├── 📦 Postbox
├── 📥 Laterbox
├── 📊 Traect
└── ...
```

На текущем этапе подключается только **Postbox**.

## Функции Hub Bot

**The Hub Bot** выполняет три функции:

1. **Launcher приложений** — `/start` команда, меню, routing пользователя
2. **Authentication handoff** — безопасная передача подтверждённой Telegram identity приложению через подписанный JWT
3. **Beta-витрина** — краткое описание приложений и публичный roadmap фич

На текущем этапе витрина содержит только metadata без подписок на обновления (см. будущие фичи в [docs/auth.md](docs/auth.md)).

**Приложения** (Postbox, Laterbox, Traect и т.д.) отвечают за:
- собственную бизнес-логику
- собственное хранилище
- собственные API и frontend

```
Postbox = почтовый трекер
Laterbox = сохранение рекомендаций
Traect = weekly tracker
...
```

Hub не импортирует и не знает бизнес-логику приложений.

## Запуск

Установите зависимости:

```bash
poetry install
```

Убедитесь что `.env` файл содержит `TELEGRAM_BOT_TOKEN`:

```bash
# .env должен содержать:
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

Запустите бота:

```bash
poetry run python -m hub_bot
```

Бот читает токен из `.env` файла или переменной окружения.

## Development

Проверки качества перед коммитом:

```bash
poetry run pytest
poetry run ruff check .
poetry run mypy src
```

Смотрите [CONTRIBUTING.md](CONTRIBUTING.md) для полной инструкции.

## Документация

- [docs/architecture.md](docs/architecture.md) — архитектурные принципы
- [docs/auth.md](docs/auth.md) — концепция authentication handoff
- [docs/mvp.md](docs/mvp.md) — план первого MVP
