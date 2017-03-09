# Alma Loris Docker

A docker build of the [Loris Image Server](https://github.com/loris-imageserver/loris) with a resolver for digital resources managed in [Ex Libris Alma](http://www.exlibrisgroup.com/category/AlmaOverview).

Docker hub repository available at http://hub.docker.com/r/joshmweisman/alma-loris-docker/.

The docker image was based on the [Loris docker repository](https://github.com/loris-imageserver/loris-docker) and the [fork](https://github.com/bodleian/loris-grok-docker) from the Bodleian Library.

## Docker Image

The docker image is based on the following components:
* Ubuntu 16.04
* Apache WSGI mod_wsgi (based on these [guidelines](https://github.com/loris-imageserver/loris/blob/development/doc/apache.md))
* [OpenJPEG](https://github.com/uclouvain/openjpeg.git) (Version 2.1.2)
* [Loris Image Server](https://github.com/loris-imageserver/loris.git) (Version 2.1.0)

## Alma Resolver

The Alma Resolver (`AlmaS3Resolver`) includes the following logic:
* Receives as the identifier [JWT token](http://jwt.io/) 
  * The token is `RS256` signed with an Alma private key and validated with with the public key in `keyfile-pub.pem`.
  * The payload includes the following properties:
```
    {
        "region": region,
        "bucket": bucket,
        "key": filename
    }
```
* If the file is not in cache it is downloaded from the Alma S3 storage

## AWS Deployment

The docker image is deployed to an AWS Elastic Beanstalk application using the 
configuration in `Dockerrun.aws.json`.

## Usage

### Pull the image from docker

    $ docker pull joshmweisman/alma-loris-docker

### Run the image in development

Because the resolver requires AWS credentials, we mount the current user's home directory as the loris user's home in the container:

    $ docker run -d -p 80:80 -v $HOME/.aws:/var/www/loris2/.aws --name loris joshmweisman/alma-loris-docker 

The credentials file must be readable by the loris user. So the file permissions must be changed on the host:

    $ chmod o+r ~/.aws/*

### Connect to a running container
    $ docker exec -i -t loris  /bin/bash

Use `Cntrl-P`, `Cntrl-Q` to leave running.

### Test

To test the container using the images bundled with Loris (in `/usr/local/share/images/`), point your browser to `http://localhost/01/02/0001.jp2/full/full/0/default.jpg`

### Build the container

    $ docker build -t joshmweisman/alma-loris-docker .

