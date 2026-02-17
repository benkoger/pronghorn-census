# Containerfile for production deployment 

# build stage
ARG VITE_API_URL_ARG
ENV VITE_API_URL=${VITE_API_URL_ARG}

FROM node:lts-alpine as build-stage
WORKDIR /app
COPY /generator_web_app/package*.json ./
RUN npm install
COPY /generator_web_app/. .
RUN npm run build

# production stage
FROM nginx:stable-alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY /generator_web_app/nginx.conf /etc/nginx/nginx.conf
EXPOSE 6900
CMD ["nginx", "-g", "daemon off;"]
