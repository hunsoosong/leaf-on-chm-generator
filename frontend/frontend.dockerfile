FROM node:22-alpine

WORKDIR /app/

COPY ./package.json ./yarn.lock ./

RUN apk add --no-cache git

RUN yarn install

COPY . .

CMD ["yarn", "run", "dev", "--host", "0.0.0.0", "--port", "8000"]
