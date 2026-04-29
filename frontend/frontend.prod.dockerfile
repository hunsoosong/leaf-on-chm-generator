FROM node:22-alpine as build-stage

WORKDIR /app/

COPY ./package.json ./yarn.lock ./

RUN apk add --no-cache git

RUN yarn install

COPY . .

RUN yarn build

FROM nginxinc/nginx-unprivileged:latest

WORKDIR /etc/nginx

COPY --from=build-stage /app/dist /usr/share/nginx/html

COPY ./frontend.nginx.conf ./conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
