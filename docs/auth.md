# Authentication Handoff

## Проблема

Нельзя просто передавать пользовательский ID в URL или параметрах:

```
https://postbox.example.com/?telegram_user_id=123
```

Это небезопасно — любой может подделать ID или перехватить значение.

## Решение: Signed Handoff

Hub Bot создаёт **короткоживущий подписанный payload**, который:

1. **Подписан** — приложение может проверить, что он пришёл от Hub
2. **Содержит telegram_user_id** — авторизованное значение
3. **Содержит target app** — предназначен конкретному приложению (например, `postbox`)
4. **Имеет TTL** — истекает через несколько минут
5. **Не может быть изменён** — signature защищает от модификации

## Концептуальный payload

```json
{
  "telegram_user_id": 123456789,
  "app": "postbox",
  "iat": "2026-01-15T10:30:00Z",
  "exp": "2026-01-15T10:35:00Z"
}
```

Это концептуальный пример. Конкретный формат (JWT, Fernet, HMAC и т.д.) выбирается позже.

## Security Requirements

- ✅ Payload подписан (приложение проверяет signature)
- ✅ Короткий TTL (5-10 минут максимум)
- ✅ Предназначен конкретному приложению (`"app"` field)
- ✅ Telegram user ID защищен от изменения
- ✅ Секреты не находятся в URL открытым текстом дольше необходимого
- ✅ Приложение после проверки создаёт собственную session (не полагается на Hub payload)

## Flow

```
User clicks /postbox in Telegram
      ↓
Hub Bot obtains request (telegram_user_id available from Telegram API)
      ↓
Hub Bot generates signed payload with:
  - telegram_user_id
  - app = "postbox"
  - iat, exp
      ↓
Hub Bot presents link or opens Postbox with payload
      ↓
Postbox receives payload
      ↓
Postbox verifies:
  - Signature (knows Hub's secret)
  - TTL not expired
  - app == "postbox"
      ↓
Postbox creates/finds user by telegram_user_id
      ↓
Postbox creates its own session (token/cookie)
      ↓
Postbox serves application
```

## Реализация

На текущем этапе конкретная реализация (JWT, Fernet, простой HMAC) не выбрана.

Она будет определена в следующем коммите, когда начнётся реальная разработка Telegram-бота.
