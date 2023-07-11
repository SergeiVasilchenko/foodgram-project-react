from django.contrib import admin

from recipes.models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                            Tag, UsersRecipes)


class IngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_filter = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'id',
        'author',
        'favorites_count',
        'get_ingredients',
    )
    list_filter = ('author', 'name', 'tags',)
    inlines = (IngredientInline,)

    def favorites_count(self, obj):
        return obj.favorites.count()
    favorites_count.short_description = 'Добавлений в избранное'

    def get_ingredients(self, obj):
        return ', '.join([
            ingredients.name for ingredients
            in obj.ingredients.all()])
    get_ingredients.short_description = 'Ингредиенты'


class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount',)


class FavoritesAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')


class UserRecipesAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
admin.site.register(Favorites, FavoritesAdmin)
admin.site.register(UsersRecipes, UserRecipesAdmin)
