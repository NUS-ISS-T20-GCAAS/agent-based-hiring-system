# ---------- Build stage ----------
FROM node:20-alpine AS builder

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG NPM_REGISTRY=https://registry.npmjs.org/

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

COPY package.json package-lock.json ./
RUN npm config set registry "${NPM_REGISTRY}" \
 && npm ci --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000

COPY . .
ARG VITE_WS_URL
ENV VITE_WS_URL=${VITE_WS_URL}
RUN npm run build


# ---------- Runtime stage ----------
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Defaults for localhost / docker-compose
ENV DNS_RESOLVER="127.0.0.11"
ENV API_URL="http://coordinator-agent:8000"

# Copy nginx config template (uses __PLACEHOLDER__ syntax to avoid conflicts with nginx $ variables)
COPY nginx.conf /etc/nginx/nginx.conf.template

# Copy build output
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# Custom entrypoint: replace only our placeholders, then start nginx
CMD sh -c "sed -e 's|__DNS_RESOLVER__|'\"$DNS_RESOLVER\"'|g' \
               -e 's|__API_URL__|'\"$API_URL\"'|g' \
               /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf \
           && nginx -g 'daemon off;'"
