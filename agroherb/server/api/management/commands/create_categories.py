from django.core.management.base import BaseCommand
from api.models import Category

class Command(BaseCommand):
    help = 'Creates default product categories'

    def handle(self, *args, **kwargs):
        categories = [
            {'name': 'Vegetables', 'description': 'Fresh vegetables'},
            {'name': 'Fruits', 'description': 'Fresh fruits'},
            {'name': 'Grains', 'description': 'Grains and pulses'},
            {'name': 'Dairy', 'description': 'Dairy products'},
            {'name': 'Organic', 'description': 'Organic products'},
        ]

        for cat in categories:
            Category.objects.get_or_create(
                category_name=cat['name'],
                description=cat['description']
            )
            self.stdout.write(f"Created category: {cat['name']}") 