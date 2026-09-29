FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S dalildz && adduser -S dalildz -G dalildz
COPY --from=build /app/public ./public
COPY --from=build --chown=dalildz:dalildz /app/.next/standalone ./
COPY --from=build --chown=dalildz:dalildz /app/.next/static ./.next/static
USER dalildz
EXPOSE 3000
CMD ["node", "server.js"]
