import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from catalog_game.models import Developers, Games

UA = 'Mozilla/5.0 (compatible; GameCatalogLinkCheck/1.0)'
DEAD = {404, 410}


def probe(url, timeout=12):
    for method in ('HEAD', 'GET'):
        request = urllib.request.Request(url, method=method, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, 'ok', ''
        except urllib.error.HTTPError as error:
            if method == 'HEAD' and error.code in (403, 405, 501):
                continue
            if error.code in DEAD:
                return error.code, 'dead', 'сторінку не знайдено'
            return error.code, 'manual', 'перевірте вручну'
        except urllib.error.URLError as error:
            return None, 'dead', f'недоступно: {error.reason}'
        except Exception as error:
            return None, 'manual', f'{type(error).__name__}: {error}'
    return None, 'manual', 'перевірте вручну'


class Command(BaseCommand):
    help = 'Перевіряє official_url та image_url ігор і website розробників'

    def add_arguments(self, parser):
        parser.add_argument('--clear-broken', action='store_true',
                            help='очистити посилання, які точно не працюють (404/410 або домен недоступний)')

    def handle(self, *args, **opts):
        jobs = []
        for game in Games.objects.all():
            for field in ('official_url', 'image_url'):
                url = getattr(game, field)
                if url:
                    jobs.append((f'{game.title} · {field}', game, field, url))
        for dev in Developers.objects.exclude(website__isnull=True).exclude(website=''):
            link = dev.website_link
            if link:
                jobs.append((f'{dev.name_dev} · website', dev, 'website', link))

        self.stdout.write(f'Перевіряю посилань: {len(jobs)} …')
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda job: probe(job[3]), jobs))

        dead = manual = 0
        for (label, obj, field, url), (status, verdict, note) in zip(jobs, results):
            if verdict == 'ok':
                continue
            if verdict == 'dead':
                dead += 1
                self.stdout.write(self.style.ERROR(f'✗ {label}: {url} [{status or "—"}] {note}'))
                if opts['clear_broken'] and field != 'website':
                    setattr(obj, field, None)
                    obj.save(update_fields=[field])
            else:
                manual += 1
                self.stdout.write(self.style.WARNING(f'? {label}: {url} [{status or "—"}] {note}'))

        ok = len(jobs) - dead - manual
        self.stdout.write(self.style.SUCCESS(f'Працюють: {ok}. Не працюють: {dead}. Потрібна ручна перевірка: {manual}.'))
        if dead and opts['clear_broken']:
            self.stdout.write('Недійсні посилання ігор очищено (на сайті буде заглушка).')
