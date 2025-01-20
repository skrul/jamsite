FROM alpine:3.21

RUN apk update && apk upgrade
RUN apk add bash
RUN apk add nginx

COPY ./nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./dist/jam /usr/share/nginx/html

EXPOSE 80

ENTRYPOINT ["nginx", "-g", "daemon off;"]
#CMD ["sleep", "infinity"]
