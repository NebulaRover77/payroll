FROM nginx:alpine
WORKDIR /usr/share/nginx/html
COPY index.html script.js style.css ./
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
