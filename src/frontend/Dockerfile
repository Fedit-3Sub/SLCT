FROM node:18-alpine
RUN apk update && apk add --no-cache build-base gcc autoconf automake zlib-dev libpng-dev nasm bash vips-dev git
ARG NODE_ENV=development
ENV NODE_ENV=${NODE_ENV}
# 빌드 컨텍스트에는 .git 이 포함되지 않으므로 husky(postinstall) 설치를 건너뛴다.
ENV HUSKY=0
RUN corepack enable

WORKDIR /opt/
COPY package.json pnpm-lock.yaml ./
RUN npm install -g node-gyp
RUN npm config set fetch-retry-maxtimeout 600000 -g && pnpm install
ENV PATH /opt/node_modules/.bin:$PATH

WORKDIR /opt/app
COPY . .
COPY .env .env
RUN chown -R node:node /opt/app
USER node
EXPOSE 9900
CMD ["pnpm", "run", "dev"]
