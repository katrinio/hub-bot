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

## Реализация: JWT с HS256

**Формат:** JWT (JSON Web Token)  
**Algorithm:** HS256 (HMAC with SHA-256)  
**Signing:** Симметричный ключ (`HUB_AUTH_SECRET` из `.env`)

### Claims

```json
{
  "sub": "123456789",
  "aud": "postbox",
  "iss": "the-hub-bot",
  "iat": 1705329000,
  "exp": 1705329300
}
```

- **`sub`** (subject) — Telegram user ID как string
- **`aud`** (audience) — целевое приложение (`postbox`)
- **`iss`** (issuer) — издатель (`the-hub-bot`)
- **`iat`** (issued-at) — время создания (UNIX timestamp)
- **`exp`** (expiration) — время истечения (UNIX timestamp, TTL = 5 минут)

### Важно: JWT подписывается, но НЕ шифруется

Payload можно декодировать без secret — это нормально. Signature обеспечивает:
- **authenticity** — приложение проверяет что Hub создал token
- **integrity** — payload не может быть изменён

Нельзя хранить секретные данные в payload. Hub передаёт только `telegram_user_id`, который уже известен Telegram.

## Security Requirements

- ✅ Payload подписан (приложение проверяет signature)
- ✅ Короткий TTL (5-10 минут максимум)
- ✅ Предназначен конкретному приложению (`"app"` field)
- ✅ Telegram user ID защищен от изменения
- ✅ Секреты не находятся в URL открытым текстом дольше необходимого
- ✅ Приложение после проверки создаёт собственную session (не полагается на Hub payload)

## Flow: Hub → Postbox

```
/start
   ↓
The Hub (menu)
   ↓
[📦 Postbox]  ← user clicks
   ↓
hub_bot processes callback.from_user.id
   ↓
create_auth_token(telegram_user_id, audience="postbox")
   ↓
JWT generated (fresh, 5 min TTL)
   ↓
build_postbox_auth_url(POSTBOX_URL, token)
   ↓
show URL button: [Открыть Postbox ↗]
   ↓
user clicks URL
   ↓
GET /auth/hub?token=<JWT>
   ↓
Postbox verifies JWT:
  - signature (knows HUB_AUTH_SECRET)
  - aud == "postbox"
  - iss == "the-hub-bot"
  - not expired
   ↓
Postbox extracts telegram_user_id from sub
   ↓
Postbox creates/finds user by telegram_user_id
   ↓
Postbox creates session cookie
   ↓
Postbox redirects to /
   ↓
Postbox app loaded
```

**Key points:**
- JWT created **only after callback** (not in callback_data)
- Uses real `callback.from_user.id` from Telegram (not client state)
- Fresh token for each auth attempt
- `POSTBOX_URL` configured via environment variable (not hardcoded)

## UX: Link Refresh

Так как JWT имеет TTL 5 минут, пользователь может открыть старое сообщение из истории чата, где ссылка уже истекла.

Для решения этой проблемы **Postbox экран содержит кнопку обновления**:

```
🔄 Обновить ссылку
```

При клике на кнопку:
1. Bot генерирует **новый** JWT (свежий, 5 минут TTL)
2. Bot обновляет сообщение с новой ссылкой и кнопкой

Это позволяет пользователю обновить ссылку на месте, не возвращаясь в /start меню.

### Реализация

- `PostboxRefreshCallback` — callback data для refresh кнопки (action: `postbox_refresh`)
- `postbox_refresh_handler()` — обработчик, который создаёт новый JWT и обновляет сообщение
- `build_postbox_auth_keyboard()` — включает refresh кнопку в клавиатуру

## Configuration

### Hub Bot

Требует `HUB_AUTH_SECRET` в `.env`:

```bash
HUB_AUTH_SECRET=your_secret_key_min_32_chars_recommended
```

Функция генерации:

```python
from hub_bot.auth import create_auth_token

token = create_auth_token(
    telegram_user_id=123456789,
    audience="postbox"
)
```

### Postbox (и другие приложения)

Для проверки token:

```python
import jwt

payload = jwt.decode(
    token,
    secret,  # тот же HUB_AUTH_SECRET
    algorithms=["HS256"],
    audience="postbox"
)

user_id = int(payload["sub"])
```

## Масштабирование

На первом этапе Hub и приложения разделяют один signing secret.

При росте числа приложений можно:
- Использовать асимметричную подпись (RSA / EdDSA)
- Hub подписывает приватным ключом, приложения проверяют через публичный ключ
- Каждое приложение хранит только публичный ключ

Это будет рассмотрено позже.

## Будущее: Beta-канал и подписки

**Идея:** The Hub может стать beta-каналом для обновлений приложений.

Пользователь подписывается на новости конкретного приложения через Hub, а Hub уведомляет его о новых релизах и фичах.

**Не реализовано пока:**
- кнопка подписки на витрине приложения
- база данных для хранения subscriptions
- background jobs для отправки уведомлений
- рассылка пользователям

Сейчас витрина содержит только metadata (описание, roadmap) без механики подписок.
