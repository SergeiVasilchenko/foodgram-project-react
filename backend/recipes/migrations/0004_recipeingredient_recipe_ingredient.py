# Generated by Django 4.2.2 on 2023-06-29 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_remove_recipeingredient_recipe_ingredient_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='recipeingredient',
            constraint=models.UniqueConstraint(fields=('recipe', 'ingredient'), name='recipe_ingredient', violation_error_message='Ингредиенты должны быть уникальными'),
        ),
    ]