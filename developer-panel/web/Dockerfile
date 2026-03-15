FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Bake NEXT_PUBLIC_ env vars at build time (Next.js inlines these into the bundle)
ARG NEXT_PUBLIC_HSPANEL_API_TOKEN=change-me
ENV NEXT_PUBLIC_HSPANEL_API_TOKEN=$NEXT_PUBLIC_HSPANEL_API_TOKEN

RUN npm run build

FROM node:20-alpine
WORKDIR /app

# Copy standalone output and static assets
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
