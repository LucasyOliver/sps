import time
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Aguarda a disponibilidade do banco de dados padrao com limite de tentativas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Tempo maximo de espera em segundos (padrao: 30).',
        )
        parser.add_argument(
            '--interval',
            type=float,
            default=1.0,
            help='Intervalo entre tentativas em segundos (padrao: 1.0).',
        )

    def handle(self, *args, **options):
        timeout = max(1, options['timeout'])
        interval = max(0.1, options['interval'])
        start_time = time.monotonic()

        self.stdout.write('Aguardando conexao com o banco de dados...')

        while True:
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
                self.stdout.write(
                    self.style.SUCCESS('Banco de dados disponivel!')
                )
                return
            except OperationalError as exc:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    raise CommandError(
                        f'Banco de dados indisponivel apos {timeout} segundos: {exc}'
                    ) from exc
                self.stdout.write(
                    'Banco indisponivel, aguardando nova tentativa...'
                )
                time.sleep(interval)
