# Containerfile for in container development

FROM node:lts-alpine

ENV NODE_ENV=development

WORKDIR /app

COPY /generator_web_app/package.json /generator_web_app/package-lock.json ./

RUN --mount=type=cache,target=/root/.npm npm install

COPY /generator_web_app/. .

RUN chown -R node:node /app

USER node

EXPOSE 5173

CMD [ "npm", "run", "dev", "--", "--host" ]