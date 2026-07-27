# MVP Checklist

## Foundation

- [x] Создать репозиторий
- [x] Зафиксировать архитектуру в docs/architecture.md
- [x] Описать authentication handoff в docs/auth.md
- [ ] Настроить configuration через environment variables

## Telegram Shell

- [x] Подключить aiogram и создать Telegram bot instance
- [x] Реализовать `/start` команду
- [ ] Добавить меню приложений (InlineKeyboard)
- [ ] Добавить Postbox в меню
- [ ] Добавить обработчик callback `hub:postbox`

## Authentication

- [ ] Выбрать формат подписи (JWT / Fernet / HMAC)
- [ ] Реализовать генерацию auth payload
- [ ] Добавить TTL (5-10 минут)
- [ ] Добавить audience field (`postbox`)
- [ ] Реализовать signing и verification функции
- [ ] Документировать shared secret между Hub и Postbox

## Postbox Integration

- [ ] Определить URL/endpoint для открытия Postbox из Hub
- [ ] Передавать подтверждённую Telegram identity через signed payload
- [ ] Создавать/находить пользователя в Postbox по telegram_user_id
- [ ] Создавать локальную Postbox session
- [ ] Проверить полный flow: Telegram → Hub → Postbox

## Deployment & Migration

- [ ] Запустить The Hub Bot на реальном Telegram account
- [ ] Перейти с отдельного Postbox bot на Hub menu
- [ ] Решить судьбу старого Postbox bot (sundown, migrate users и т.д.)

## Future Integrations

Laterbox, Traect, Registry — в следующих MVP:

- [ ] Laterbox (в следующем MVP)
- [ ] Traect (в следующем MVP)
- [ ] Registry (в следующем MVP)
