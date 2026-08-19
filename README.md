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

Самостоятельная проверка Asahi DEVICES watcher без отправки в Telegram:

```bash
poetry run python -m watcher --dry-run
```

Watcher разбирает полный upstream `DEVICES`, но выводит только отслеживаемое устройство `j516sap`
(MacBook Pro 16-inch, M3 Pro, 2023).

Для ручной отправки watcher использует `TELEGRAM_BOT_TOKEN` и `ADMIN_TELEGRAM_ID`:

```bash
poetry run python -m watcher
```

### Проверка изменений по cron

Режим `--check` сравнивает `j516sap` со snapshot в `data/watcher/j516sap.json`. Каталог `data`
примонтирован в контейнер как `/app/data`. Первый запуск только
сохраняет baseline. Следующие запуски отправляют администратору сообщение исключительно при изменении
`model`, `min_ver` или `expert_only`. Snapshot обновляется только после успешной отправки.

Инициализация baseline на VPS:

```bash
cd /home/katrin/projects/hub-bot
docker compose run --rm hub-bot python -m watcher --check
```

Пример `crontab -e` для ежедневной проверки в 05:00 по Белграду:

```cron
CRON_TZ=Europe/Belgrade
0 5 * * * cd /home/katrin/projects/hub-bot && /usr/bin/flock -n /tmp/hub-bot-watcher.lock /usr/bin/docker compose run --rm hub-bot python -m watcher --check >> data/watcher/cron.log 2>&1
```

При необходимости snapshot можно перенести через `WATCHER_STATE_PATH` или аргумент `--state-path`.

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
