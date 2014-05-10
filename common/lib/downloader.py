#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
# File: downloader.py
# Date: Sat May 10 19:58:01 2014 +0800
# Author: Yuxin Wu <ppwwyyxxc@gmail.com>

from uklogger import *
from lib.textutil import parse_file_size
import ukconfig

import sys
import requests
from urlparse import urlparse

class ProgressPrinter(object):
    def __init__(self):
        self.total = 0

    def finish(self):
        sys.stdout.write("\n")
        sys.stdout.flush()
        log_info("Download finished")

    def update(self, done):
        assert self.total != 0
        width = 50
        done_len = int(width * done / self.total)
        sys.stdout.write("\r[{0}>{1}]".format('=' * done_len,
                                              ' ' * (width - done_len)))
        sys.stdout.flush()

    def set_total(self, size):
        """size: number of bytes"""
        log_info("File size is {0}".format(parse_file_size(size)))
        self.total = size


def direct_download(url, headers=None, progress_updater=None):
    """ direct download according to ctx
        return the data
    """
    log_info("Directly Download with URL {0} ...".format(url))

    if progress_updater is None:
        progress_updater = ProgressPrinter()        # default updater
    if headers is None:
        headers = {'Host': urlparse(url).netloc,
                   'User-Agent': ukconfig.USER_AGENT
                  }

    # for test only
    if ukconfig.download_method == 'wget':
        headers = ' '.join(['--header="{0}: {1}"'.format(k, v) for k, v
                            in headers.iteritems()])
        os.system('wget "{0}" -O "{1}" {2}'.format(url, filename, headers))
        return

    resp = requests.get(url, stream=True, headers=headers)
    total_length = resp.headers.get('content-length')
    if total_length is None:
        progress_updater.finish()
        return resp.content
    else:
        total_length = int(total_length)
        if total_length < ukconfig.FILE_SIZE_MINIMUM:
            raise Exception("File too small: " + parse_file_size(total_length))
        if total_length > ukconfig.FILE_SIZE_MAXIMUM:
            raise Exception("File too large: " + parse_file_size(total_length))
        progress_updater.set_total(total_length)
        dl = 0
        ret = ""
        for data in resp.iter_content():
            dl += len(data)
            ret += data
            progress_updater.update(dl)
        progress_updater.finish()
        return ret