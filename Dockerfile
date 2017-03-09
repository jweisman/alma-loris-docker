FROM ubuntu:16.04

MAINTAINER Ex Libris Group

ENV HOME /root

# Update packages and install tools 
RUN apt-get update -y && apt-get install -y wget git gcc g++ unzip make pkg-config

# Install pip and python libs
RUN apt-get install -y python-dev python-setuptools python-pip build-essential libxml2-dev libxslt1-dev
RUN pip install --upgrade pip		
RUN pip2.7 install Werkzeug
RUN pip2.7 install configobj

# Install cmake 3.2
WORKDIR /tmp/cmake
RUN wget http://www.cmake.org/files/v3.2/cmake-3.2.2.tar.gz && tar xf cmake-3.2.2.tar.gz && cd cmake-3.2.2 && ./configure && make && make install

# Download and compile OpenJPEG v2.1.2
WORKDIR /tmp/openjpeg
RUN git clone https://github.com/uclouvain/openjpeg.git ./
RUN git checkout tags/v2.1.2
RUN cmake . && make && make install

# shortlinks for other libraries
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libfreetype.so /usr/lib/ \
	&& ln -s /usr/lib/`uname -i`-linux-gnu/libjpeg.so /usr/lib/ \
	&& ln -s /usr/lib/`uname -i`-linux-gnu/libz.so /usr/lib/ \
	&& ln -s /usr/lib/`uname -i`-linux-gnu/liblcms2.so /usr/lib/ \
	&& ln -s /usr/lib/`uname -i`-linux-gnu/libtiff.so /usr/lib/ 

RUN echo "/usr/local/lib" >> /etc/ld.so.conf && ldconfig

# install graphic libraries
RUN apt-get install -y libjpeg-turbo8-dev libfreetype6-dev zlib1g-dev liblcms2-dev liblcms2-utils libtiff5-dev python-dev libwebp-dev apache2 libapache2-mod-wsgi
RUN pip2.7 install Pillow

# Install kakadu
# WORKDIR /usr/local/lib
# RUN wget --no-check-certificate https://github.com/loris-imageserver/loris/raw/development/lib/Linux/x86_64/libkdu_v74R.so \
#	&& chmod 755 libkdu_v74R.so
#
# WORKDIR /usr/local/bin
# RUN wget --no-check-certificate https://github.com/loris-imageserver/loris/raw/development/bin/Linux/x86_64/kdu_expand \
#	&& chmod 755 kdu_expand
#

# Install loris
RUN mkdir /opt/loris/
WORKDIR /opt/loris/
RUN git clone https://github.com/loris-imageserver/loris.git ./
RUN git checkout tags/v2.1.0-final

RUN useradd -d /var/www/loris2 -s /sbin/false loris

# Create image directory
RUN mkdir /usr/local/share/images
RUN chown loris:loris /usr/local/share/images

# Load example images
RUN cp -R tests/img/* /usr/local/share/images/

# install loris conf and replace webapp.py (with 'opj' mod), run setup.py 
COPY loris2.conf etc/loris2.conf
COPY keyfile-pub.pem etc/keyfile-pub.pem
COPY webapp.py loris/webapp.py
COPY resolver.py loris/resolver.py
RUN ./setup.py install 

# install Alma resolver dependencies
RUN apt-get install -y libssl-dev libffi-dev
RUN pip install cryptography pyjwt boto3

# get python validator framework
RUN pip2.7 install bottle \
    && pip2.7 install python-magic \
    && pip2.7 install lxml

# get IIIF validator
WORKDIR /tmp
RUN wget --no-check-certificate https://pypi.python.org/packages/source/i/iiif-validator/iiif-validator-1.0.0.tar.gz \
	&& tar zxfv iiif-validator-1.0.0.tar.gz \
	&& rm iiif-validator-1.0.0.tar.gz

# Configure Apache
COPY wsgi-loris.conf /etc/apache2/conf-available/wsgi-loris.conf
RUN a2enmod headers expires 
RUN a2enconf wsgi-loris

# run
WORKDIR /opt/loris/loris

# Run Apache
EXPOSE 80
CMD /usr/sbin/apache2ctl -D FOREGROUND