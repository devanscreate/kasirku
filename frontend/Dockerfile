# Tahap 1: Build PWA statis menggunakan pnpm
FROM node:22-alpine AS builder

WORKDIR /app

# Aktifkan pnpm via corepack
RUN corepack enable pnpm

# Salin konfigurasi dependensi
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Pasang dependensi
RUN pnpm install --frozen-lockfile

# Salin source code
COPY . .

# Build aset produksi PWA
RUN pnpm build

# Tahap 2: Image minimal untuk mengekspor aset dist
FROM alpine:latest
WORKDIR /dist
COPY --from=builder /app/dist .
CMD ["tar", "-cf", "-", "."]
