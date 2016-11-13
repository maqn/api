FROM python:2.7-onbuild

RUN rm /usr/src/app/config.py ; \
  mkdir /data && \
  ln -s /data/config.py /usr/src/app/config.py

VOLUME /data
EXPOSE 8080
ENV FLASK_APP main.py
CMD [ "flask", "run", "--host=0.0.0.0", "--port=8080" ]
