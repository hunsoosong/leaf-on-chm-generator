FROM nginxinc/nginx-unprivileged:latest

WORKDIR /etc/nginx

COPY ./nginx.dev.conf ./conf.d/default.conf

EXPOSE 80

ENTRYPOINT ["nginx"]

CMD ["-g", "daemon off;"]