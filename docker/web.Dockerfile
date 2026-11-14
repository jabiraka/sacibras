# O site em modo de desenvolvimento (Vite), lendo os JSONs que o builder gravou.
FROM node:22-slim

WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web ./
EXPOSE 5173
CMD ["npm", "run", "dev"]
