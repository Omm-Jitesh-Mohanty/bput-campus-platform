from django.core.management.base import BaseCommand
from apps.chatbot.indexer import rebuild_all


class Command(BaseCommand):
    help = 'Rebuild the chatbot RAG index.'

    def handle(self, *args, **options):
        self.stdout.write('Building chatbot index...')
        counts = rebuild_all()
        for k, v in counts.items():
            self.stdout.write(f'  ✓ {k}: {v} chunks')
        self.stdout.write(self.style.SUCCESS('Done.'))