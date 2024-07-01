FROM python:3.10

LABEL author="pat@backblaze.com"

WORKDIR /app

ARG UID=1000
ARG GID=1000

RUN apt-get update \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean \
  && groupadd -g "${GID}" python \
  && useradd --create-home --no-log-init -u "${UID}" -g "${GID}" python \
  && chown python:python -R /app

USER python

COPY --chown=python:python ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

ARG FLASK_DEBUG="false"
ARG LOGLEVEL="DEBUG"
ARG GUNICORN_LOGLEVEL="debug"
ENV FLASK_DEBUG="${FLASK_DEBUG}" \
    FLASK_APP="app" \
    FLASK_SKIP_DOTENV="true" \
    GUNICORN_LOGLEVEL="${GUNICORN_LOGLEVEL}" \
    PYTHONUNBUFFERED="true" \
    PYTHONPATH="." \
    PATH="${PATH}:/home/python/.local/bin" \
    USER="python"
COPY --chown=python:python . .
CMD ["gunicorn", "--config", "python:config.gunicorn", "app:app"]
