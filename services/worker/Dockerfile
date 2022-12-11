FROM python:3.9-slim-bullseye
WORKDIR /app
ENV APP_PATH=services/worker
COPY . .
RUN pip install -r $APP_PATH/requirements.txt
RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends ffmpeg
CMD python3 -m services.worker.worker