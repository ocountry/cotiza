# frontend/Dockerfile
# ==============================
# Vigil Frontend - Multi-stage build
# Stage 1: Build the React app with Node.js
# Stage 2: Serve with nginx
# ==============================

# ---- Stage 1: Build ----
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifest for layer caching
COPY package.json ./

# Install dependencies
# Note: no yarn.lock committed — yarn will generate one during build
RUN yarn install --production=false

# Copy the rest of the application source
COPY . .

# Build the React app for production
# REACT_APP_* environment variables are embedded at build time by CRA.
# Set to empty string so API calls are relative (proxied by nginx).
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL:-""}

RUN yarn build

# ---- Stage 2: Serve with nginx ----
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built React app from the builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Nginx:alpine already runs as a non-root user (nginx uid 101)
# The nginx.conf is configured to not need root privileges

# Expose port 80
EXPOSE 80

# Health check: verify nginx is serving
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

# Default CMD from nginx:alpine is "nginx -g daemon off;"