# MVP Checklist

## Foundation

- [x] Создать репозиторий
- [x] Зафиксировать архитектуру в docs/architecture.md
- [x] Описать authentication handoff в docs/auth.md
- [x] Настроить configuration через environment variables (.env + python-dotenv)

## Telegram Shell

- [x] Подключить aiogram и создать Telegram bot instance
- [x] Реализовать `/start` команду
- [x] Добавить меню приложений (InlineKeyboard)
- [x] Добавить Postbox в меню
- [x] Добавить обработчик callback `hub:postbox`
- [x] Добавить обработчик возврата в The Hub (`hub:home`)

## Authentication

- [x] Выбрать формат подписи JWT / HS256
- [x] Реализовать генерацию auth payload
- [x] Добавить TTL 5 минут
- [x] Добавить audience field (`postbox`)
- [x] Реализовать signing и verification функции (Hub side)
- [x] Документировать shared secret между Hub и Postbox

## Postbox Integration

- [x] Определить URL/endpoint для открытия Postbox из Hub
  - Использует `POSTBOX_URL` config + `/auth/hub?token=<JWT>`
- [x] Передавать подтверждённую Telegram identity через signed payload
  - JWT with `sub=telegram_user_id`, `aud=postbox`, `iss=the-hub-bot`, 5 min TTL
- [x] Показывать URL button для входа в Postbox
  - Handler `hub:postbox` генерирует JWT и показывает "Открыть Postbox ↗" button
- [x] Авторизация на стороне Postbox
  - Postbox verifies JWT и создаёт session
- [ ] Проверить полный flow ручно (end-to-end smoke test)

## Deployment & Migration

- [ ] Запустить The Hub Bot на реальном Telegram account
- [ ] Перейти с отдельного Postbox bot на Hub menu
- [ ] Решить судьбу старого Postbox bot (sundown, migrate users и т.д.)

## Future Integrations

Laterbox, Traect, Registry — в следующих MVP:

- [ ] Laterbox (в следующем MVP)
- [ ] Traect (в следующем MVP)
- [ ] Registry (в следующем MVP)
