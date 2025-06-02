FROM python:3.11

RUN apt-get update && apt-get install -y libzbar0 libgl1

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV BOT_TOKEN=${BOT_TOKEN}

CMD ["python", "bot.py"]
