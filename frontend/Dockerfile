FROM node:20-alpine AS builder
WORKDIR /app

# Accept build-time API URL (empty = relative paths, which is what we want)
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Use production nginx config if present, otherwise default
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Install curl for healthcheck
RUN apk add --no-cache curl

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
