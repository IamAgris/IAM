# =============================================================================
# Project AURA - Frontend Dockerfile
# =============================================================================
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Build Next.js — rewrites are baked into the build manifest, so the API URL
# must be available at build time. Compose passes http://backend:8000.
ARG IAM_API_URL=http://localhost:8000
ENV IAM_API_URL=${IAM_API_URL}
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["npm", "start"]
