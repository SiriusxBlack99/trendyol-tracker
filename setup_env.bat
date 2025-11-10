@echo off
if not exist .env (
  copy .env.example .env
  echo Edit .env with your Telegram token and chat id.
) else (
  echo .env already exists.
)
