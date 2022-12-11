FROM python:3.9-slim-bullseye
WORKDIR /app
ENV APP_PATH=services/bot
COPY . .
COPY common /app
RUN pip install -r $APP_PATH/requirements.txt

CMD python3 "$APP_PATH/bot.py"