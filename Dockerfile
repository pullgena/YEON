FROM node:22-alpine
WORKDIR /app
COPY package.json server.js index.html ./
ENV NODE_ENV=production PORT=3000 YEON_DATA_FILE=/data/yeon-data.json
RUN mkdir -p /data && chown -R node:node /data /app
USER node
EXPOSE 3000
CMD ["node", "server.js"]
