import logging
import traceback

log = logging.getLogger('manage')


class ExceptionMiddleware(object):
    def process_exception(self, request, exception):
        log.error(request.path + ', exc=' + traceback.format_exc())