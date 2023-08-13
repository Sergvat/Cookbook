import csv

from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт ингредиентов из CSV-файлов'

    def handle(self, *args, **options):
        with open('./data/ingredients.csv', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                Ingredient.objects.get_or_create(
                    name=row['name'], measurement_unit=row['unit'])

        self.stdout.write(self.style.SUCCESS(
            'Ingredients imported successfully'))
