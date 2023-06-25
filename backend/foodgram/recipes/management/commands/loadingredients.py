import pandas as pd

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


def loadcsv(file_name: str):
    return pd.read_csv(f'data/{file_name}.csv')


def import_ingredients():
    data = [
        Ingredient(
            name=row[0],
            measurement_unit=row[1],
        )
        for _, row in loadcsv("ingredients").iterrows()
    ]
    Ingredient.objects.bulk_create(data)


class Command(BaseCommand):
    help = 'Loads ingredients from a CSV file'

    def handle(self, *args, **options):
        import_ingredients()
        self.stdout.write(self.style.SUCCESS(
            'Ingredients imported successfully'
        ))
