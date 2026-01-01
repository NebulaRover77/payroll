FROM nginx:alpine

# Set working directory
WORKDIR /usr/share/nginx/html

# Copy static site content
COPY index.html script.js style.css ./

# Expose default nginx port
EXPOSE 80
