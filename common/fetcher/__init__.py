#!../../manage/exec-in-virtualenv.sh
# -*- coding: UTF-8 -*-
# File: __init__.py
# Date: Sat May 10 19:20:13 2014 +0800
# Author: Yuxin Wu <ppwwyyxxc@gmail.com>

from lib.textutil import parse_file_size
from lib.downloader import direct_download
from ukutil import check_filetype, import_all_modules
from uklogger import *
from job import JobContext, SearchResult

from functools import wraps
import ukconfig
import sys
import requests
import os
import traceback
import re


def check_pdf(fname):
    return check_filetype(fname, 'PDF document')

class register_parser(object):
    parser_list = []

    parser_dict = {}
    """ save the original parser func"""

    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop('name')
        self.url_match = re.compile(kwargs.pop('urlmatch'))

        self.type_match = kwargs.pop('typematch', None)
        self.legal = kwargs.pop('legal', True)

        assert self.name not in self.parser_dict

    def __call__(self, func):
        """ func: callable to be invoked, took a 'SearchResult'
            func return a dict, with
            'url', 'headers' to pass to downloader,
            'ctx_update': {} to update the context
        """
        self.parser_dict[self.name] = func

        @wraps(func)
        def wrapper(res):
            assert isinstance(res, SearchResult)
            try:
                params = func(res)
                if params is None:
                    return None
                if 'ctx_update' not in params:
                    params['ctx_update'] = {}
                params['ctx_update'].update({'source': self.name})
                return params
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log_exc("Error in parser '{0}' with url '{1}'".
                        format(self.name, res.url))
                return None
        self.parser_list.append(self)
        self.cb = wrapper
        return wrapper

    def run(self, ctx, sr, progress_updater=None):
        """ run this parser against the SearchResult given
            return True/False indicate success,
            will update ctx metadata and ctx.success
        """
        url = sr.url
        if (self.type_match is None
            or self.type_match != sr.type) and \
           len(self.url_match.findall(url)) == 0:
            return False

        log_info("Parsing url {0} with parser {1}".
                 format(url, self.name))
        res = self.cb(sr)
        if res is None:
            return False

        try:
            data = direct_download(res['url'], res.get('headers'),
                                   progress_updater)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log_exc("Error while downloading in parser '{0}' with" \
                    "url '{1}'".format(self.name, url))
            return False

        ft = check_filetype(data, 'PDF document')
        if ft == True:
            ctx.success = True
            ctx.data = data
            log_info("Update metadata: {0}".format(str(res['ctx_update'])))
            # TODO update metadata

            # write file
            if ukconfig.SAVE_TO_FILE:
                filename = ctx.title + ".pdf"
                log_info("Writing data to {0}".format(filename))
                with open(filename, 'wb') as f:
                    f.write(data)
            return True
        else:
            log_err("Wrong Format: {0}".format(ft))
            return False


@register_parser(name='direct link', urlmatch='.*\.pdf', typematch='directpdf')
def direct_link(search_result):
    return { 'url': search_result.url}

if __name__ != '__main__':
    import_all_modules(__file__, __name__)
