"""
Rebuild the RAG vector index from all knowledge sources.

Run after:
  - Adding new PDFs to ai_engine/rag/corpus/generated/
  - Bulk updates to tickets, notices, or config
  - Changing embedding model

Usage:
    python manage.py reindex_rag
    python manage.py reindex_rag --generate-pdfs   # regenerate policy PDFs first
"""
from django.core.management.base import BaseCommand

from ai_engine.rag.indexer import rebuild_all


class Command(BaseCommand):
    help = 'Rebuild the RAG vector index.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--generate-pdfs', action='store_true',
            help='Regenerate policy PDFs before indexing.'
        )

    def handle(self, *args, **options):
        if options['generate_pdfs']:
            self.stdout.write('Generating policy PDFs...')
            from ai_engine.rag.corpus.generator import generate_all
            files = generate_all()
            self.stdout.write(f'  ✓ {len(files)} PDFs generated')

        self.stdout.write('Building FAISS index (this may take 2-5 minutes)...')
        stats = rebuild_all()
        self.stdout.write('')
        for key, count in stats.items():
            if key != 'total':
                self.stdout.write(f'  ✓ {key}: {count} chunks')
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Total: {stats["total"]} chunks indexed.\n'
        ))