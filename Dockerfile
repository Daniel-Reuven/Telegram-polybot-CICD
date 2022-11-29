FROM python:3.8-slim-bullseye
WORKDIR /botapp
LABEL app=bot
COPY . .
RUN pip install -r requirements.txt
CMD ["python3", "bot.py"]