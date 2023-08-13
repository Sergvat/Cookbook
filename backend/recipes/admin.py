from django.contrib import admin

from recipes.models import (Tag, Recipe, Ingredient,
                            IngredientToRecipe, FavoriteRecipe)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')


class IngredientInLine(admin.TabularInline):
    model = IngredientToRecipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'author',
        'name',
        'image',
        'text',
        'cooking_time',
        # 'published',
        # 'is_favorited',
        # 'is_in_shopping_cart'
    )
    list_filter = ('name', 'author',)
    inlines = (IngredientInLine,)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)


@admin.register(IngredientToRecipe)
class IngredientToRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
