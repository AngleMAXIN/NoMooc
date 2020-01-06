FROM python:3.6.8-alpine3.9

ENV OJ_ENV production

ADD . /app
WORKDIR /app

HEALTHCHECK --interval=10s --retries=3 CMD python2 /app/deploy/health_check.py

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories && apk update

RUN apk add --update --no-cache build-base mariadb-connector-c-dev nginx openssl gcc postgresql-dev curl unzip supervisor jpeg-dev zlib-dev freetype-dev \
&& apk add --no-cache --virtual .build-deps \
		mariadb-dev \
		musl-dev \
    && pip install --no-cache-dir -r /app/deploy/requirements.txt -i https://pypi.douban.com/simple \
    && apk del build-base --purge \
    && apk del .build-deps

# RUN curl -vLJO -H 'Accept: application/octet-stream' 'http://api.github.com/repos/matongzaizhaohuanwo/nomooc/releases/assets/16250108?access_token=0634dd5d7b7dd80ccee78dc4ae34bd3d77dff716' && \
#     unzip dist.zip && \
#     rm dist.zip

ENTRYPOINT /app/deploy/entrypoint.sh


