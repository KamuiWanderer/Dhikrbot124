# Use Node.js as the base image
FROM node:20-slim

# Install Python 3 and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package.json and install Node dependencies
COPY package*.json ./
RUN npm install

# Copy bot requirements and install Python dependencies
COPY bot/requirements.txt ./bot/
RUN pip3 install --no-cache-dir -r bot/requirements.txt --break-system-packages

# Copy the rest of the application
COPY . .

# Build the React frontend
RUN npm run build

# Expose the port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Start the server
CMD ["npm", "start"]
