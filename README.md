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

## Граница ответственности

**The Hub Bot** отвечает за:
- Telegram identity
- `/start` команда
- меню приложений
- routing пользователя
- безопасная передача подтверждённой Telegram identity приложению
- минимальная общая Telegram UX

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

## Статус

Проект находится на начальном этапе разработки. В этом коммите:
- архитектурные принципы
- документация

Рабочая реализация Telegram-бота — в следующих коммитах.

Смотрите [docs/mvp.md](docs/mvp.md) для плана первого MVP.

## Development

```bash
poetry install
poetry run pytest
poetry run ruff check .
poetry run mypy src
```

Смотрите [CONTRIBUTING.md](CONTRIBUTING.md) для полной инструкции.

## Документация

- [docs/architecture.md](docs/architecture.md) — архитектурные принципы
- [docs/auth.md](docs/auth.md) — концепция authentication handoff
- [docs/mvp.md](docs/mvp.md) — план первого MVP
