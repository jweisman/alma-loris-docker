# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
import errno
from logging import getLogger
from loris_exception import ResolverException
from os.path import join, exists, dirname
from os import makedirs, rename, remove
from shutil import copy
import tempfile
from urllib import unquote, quote_plus
from contextlib import closing

import constants
import hashlib
import glob
import requests
import re

logger = getLogger(__name__)


class _AbstractResolver(object):

    def __init__(self, config):
        self.config = config

    def is_resolvable(self, ident):
        """
        The idea here is that in some scenarios it may be cheaper to check
        that an id is resolvable than to actually resolve it. For example, for
        an HTTP resolver, this could be a HEAD instead of a GET.

        Args:
            ident (str):
                The identifier for the image.
        Returns:
            bool
        """
        cn = self.__class__.__name__
        raise NotImplementedError('is_resolvable() not implemented for %s' % (cn,))

    def resolve(self, ident):
        """
        Given the identifier of an image, get the path (fp) and format (one of.
        'jpg', 'tif', or 'jp2'). This will likely need to be reimplemented for
        environments and can be as smart or dumb as you want.

        Args:
            ident (str):
                The identifier for the image.
        Returns:
            (str, str): (fp, format)
        Raises:
            ResolverException when something goes wrong...
        """
        cn = self.__class__.__name__
        raise NotImplementedError('resolve() not implemented for %s' % (cn,))

    def format_from_ident(self, ident):
        if ident.rfind('.') != -1:
            extension = ident.split('.')[-1]
            if len(extension) < 5:
                extension = extension.lower()
                #return constants.EXTENSION_MAP.get(extension, extension)
                return extension
        message = 'Format could not be determined for: %s.' % (ident)
        raise ResolverException(404, message)

class AlmaS3Resolver(_AbstractResolver):
    """
    Receives a JWT token with the information needed to retrieve the 
    file from S3. Token is verified, and then file is served from
    cache or downloaded from S3.
    """

    def __init__(self, config):
        super(AlmaS3Resolver, self).__init__(config)
        self.public_key_file = self.config.get('public_key_file')
        self.default_format = self.config.get('default_format', None)
        self.cache_root = self.config.get('cache_root')
        self._file_info = None
        logger.debug('initialize AlmaS3Resolver')

        try:
            assert self.cache_root and self.public_key_file
        except:
            message = 'Server Side Error: Configuration incomplete and cannot resolve. Settings required for cache_root and public_key_file.'
            logger.error(message)
            raise ResolverException(500, message)

    def is_resolvable(self, ident):
        logger.debug('is_resolvable %s' % ident)
        file_info, fp = self._ident_s3_details(ident)
        if exists(fp):
            return True
        else:
            import boto3
            s3 = boto3.client('s3', region_name=self.region)
            try:
                s3.head_object(**file_info)
                return True
            except:
                return False

        return False
 
    def cache_path(self, file_info):
        return join(self.cache_root, file_info['Bucket'], file_info['Key'])

    def get_format(self, ident, potential_format):
        if self.default_format is not None:
            return self.default_format
        elif potential_format is not None:
            return potential_format
        else:
            return self.format_from_ident(ident)

    # Get the file details from the identifier token
    def _ident_s3_details(self, ident):

        logger.debug('_ident_s3_details ident %s' % ident)
        logger.debug('_ident_s3_details self._file_info %s' % str(self._file_info))

        # TODO: Ensure errors are bubbled up (not 500)
        import jwt
        with open(self.public_key_file, "r") as f:
            public_key = f.read()
            try:
                file_info = jwt.decode(ident, public_key, algorithm='RS256')
                assert file_info.get('bucket') and file_info.get('key') and file_info.get('region')
                self.region = file_info['region']
                self._file_info = {
                    'Bucket': file_info['bucket'],
                    'Key': file_info['key']
                }
            except (jwt.exceptions.InvalidTokenError, 
                jwt.exceptions.ExpiredSignatureError, 
                jwt.exceptions.InvalidKeyError):
                message = 'Token could not be validated %s'
                logger.warn(message, ident)
                raise (ResolverException(401, message))
            except AssertionError:
                message = 'Identifier does not contain required attributes %s'
                logger.info(message, ident)
                raise ResolverException(400, message)

        logger.debug('file info %s' % str(self._file_info))
        print str(self._file_info)
        return self._file_info, self.cache_path(self._file_info)

    def _create_cache_dir(self, fp):
        import os
        cache_dir = dirname(fp)
        try:
            makedirs(cache_dir)
        except OSError as ose:
            if ose.errno == errno.EEXIST:
                pass
            else:
                raise

    def download_file(self, ident):
        logger.debug('download_file ident %s' % ident)
        file_info, fp = self._ident_s3_details(ident)
        if not exists(fp):
            import boto3
            self._create_cache_dir(fp)
            s3 = boto3.client('s3', region_name=self.region)
            file_info['Filename'] = fp
            s3.download_file(**file_info)

        return fp

    def resolve(self, ident):
        cached_file_path = self.download_file(ident)
        format_ = self.get_format(cached_file_path, None)
        return (cached_file_path, format_)        



