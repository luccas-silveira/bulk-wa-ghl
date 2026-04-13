# Frontend Dockerfile - Multi-stage build
FROM node:20-alpine as builder

# Set working directory
WORKDIR /app

# Fix ownership so node user can write to /app (WORKDIR is created as root)
RUN chown node:node /app

# Run as non-root user (node user exists in node:20-alpine with UID 1000)
USER node

# Copy package files
COPY --chown=node:node package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY --chown=node:node . .

# Build argument for API URL
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

# Build application
RUN npm run build

# Production stage - Nginx
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
