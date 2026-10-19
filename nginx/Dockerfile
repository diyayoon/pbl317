FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/default.conf
COPY default.conf /etc/nginx/conf.d/default.conf
COPY proxy_params.conf /etc/nginx/proxy_params.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
