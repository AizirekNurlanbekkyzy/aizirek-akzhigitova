FROM node:22-alpine AS base
RUN apk add --no-cache libc6-compat
WORKDIR /app
RUN npm install --global pnpm@11.25.0

FROM base AS deps
COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG FIXFLOW_API_ORIGIN=http://backend:8000
ENV FIXFLOW_API_ORIGIN=$FIXFLOW_API_ORIGIN
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm run build

FROM base AS runner
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
EXPOSE 3000
CMD ["pnpm", "run", "start"]
