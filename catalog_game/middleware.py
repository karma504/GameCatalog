import logging
import time

from django.conf import settings

logger = logging.getLogger('catalog_game.slow')


class RequestTimingMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed = time.perf_counter() - started
        response['X-Response-Time'] = f'{elapsed * 1000:.0f}ms'
        if elapsed > getattr(settings, 'SLOW_REQUEST_SECONDS', 1.0):
            logger.warning('Повільний запит: %s %s — %.2f с (статус %s)',
                           request.method, request.get_full_path(), elapsed, response.status_code)
        return response
