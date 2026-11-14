FROM oven/bun:1 AS deps
WORKDIR /app
COPY package.json ./
RUN bun install --no-save
FROM oven/bun:1 AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN bun run build
EXPOSE 3000
CMD ["bun", "run", "start", "--", "-H", "0.0.0.0"]
