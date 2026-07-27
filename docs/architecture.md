# Архитектура The Hub Bot

## Основной принцип

```
Telegram
   ↓
The Hub Bot
   ↓
application boundary
   ↓
independent application
```

**The Hub Bot** отвечает за Telegram-facing слой.
**Приложение** отвечает за собственную бизнес-логику и хранилище.

## Независимость приложений

Каждое приложение (Postbox, Laterbox, Traect, Registry):

- **живёт отдельно** — собственный репозиторий, собственный deployment
- **имеет собственное хранилище** — отдельная БД, отдельный Redis, собственные таблицы
- **самостоятельно авторизует пользователя** после проверки handoff от Hub
- **не импортирует код Hub Bot** — никакие импорты из `hub_bot` пакета
- **не зависит от БД Hub Bot** — Hub не имеет общей БД с приложениями

## Hub не должен становиться монолитом

В Hub Bot НЕ переносится:

- Postbox tracking logic
- Laterbox AI/extraction logic
- Traect domains/reviews logic
- Registry membership logic

Это остаётся в соответствующих приложениях.

Hub — только **Telegram shell** и **authentication bridge**.

## Интеграция приложений

Предполагаемая модель:

```
Telegram user
      ↓
The Hub Bot (знает telegram_user_id)
      ↓
создаёт короткоживущий подписанный payload
      ↓
передаёт его приложению (например, Postbox)
      ↓
Приложение проверяет:
    - signature
    - expiration
    - audience (какому приложению предназначен)
      ↓
Приложение создаёт собственную session
```

Дальнейшее общение между пользователем и приложением идёт через собственную session приложения.

## Пример: Postbox

```
Telegram user запрашивает /postbox из Hub
      ↓
Hub генерирует signed handoff payload
      ↓
Hub открывает Postbox с payload в URL (или другим способом)
      ↓
Postbox проверяет payload
      ↓
Postbox создаёт/находит пользователя
      ↓
Postbox создаёт собственную session cookie/token
      ↓
Дальше Postbox работает как обычное приложение
```

Hub не требует знания внутреннего устройства Postbox.
