FROM ubuntu:16.04

RUN apt-get -q update &&\
    DEBIAN_FRONTEND="noninteractive" apt-get -q install -y -o Dpkg::Options::="--force-confnew" --no-install-recommends\
        apache2 libapache2-mod-wsgi-py3 openssl git vim curl \
        python3.5 python3-venv python3-pip python3-dev \
        build-essential autoconf libtool pkg-config libpq-dev libmysqlclient-dev &&\
    apt-get -q autoremove &&\
    apt-get -q clean -y && rm -rf /var/lib/apt/lists/* && rm -f /var/cache/apt/*.bin

RUN openssl req \
    -new \
    -newkey rsa:2048 \
    -days 3650 \
    -nodes \
    -x509 \
    -subj "/CN=localhost" \
    -keyout /etc/ssl/selfsigned.key \
    -out /etc/ssl/selfsigned.crt

RUN a2enmod ssl

WORKDIR /www
ADD requirements.txt /www/requirements.txt

RUN cd /www && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

ADD apache2_wsgi_sample.conf /etc/apache2/sites-enabled/python_wsgi.conf
RUN echo "Port 443" > /etc/apache2/ports.conf
ADD . /www

ENTRYPOINT ["/www/docker_entrypoint.sh"]
CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
