# 1) 빌드
FROM node:18-alpine AS build
# 빌드 컨텍스트에는 .git 이 포함되지 않으므로 husky(postinstall) 설치를 건너뛴다.
ENV HUSKY=0
RUN corepack enable
WORKDIR /opt/app
COPY package.json pnpm-lock.yaml ./
RUN npm config set fetch-retry-maxtimeout 600000 -g && pnpm install --frozen-lockfile
COPY . .
ARG VITE_APP_VERSION=alpha
ENV VITE_APP_VERSION=${VITE_APP_VERSION}
RUN pnpm run build

# 2) 서빙: 정적 파일 + 백엔드 프록시
FROM nginx:1.27-alpine
# BACKEND_URL 은 컨테이너 시작 시 nginx 설정 템플릿에 채워진다.
ENV BACKEND_URL=http://backend:1337
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /opt/app/dist /usr/share/nginx/html
EXPOSE 9900
