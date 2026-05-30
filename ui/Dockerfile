# Build from the REPO ROOT:  docker build -f ui/Dockerfile -t aegis-ui .
FROM node:20-slim AS build
WORKDIR /app
COPY ui/package.json ui/package-lock.json* ./
RUN npm install
COPY ui ./
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN npm run build

FROM node:20-slim AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["npm", "start"]
