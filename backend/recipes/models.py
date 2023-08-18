from django.db import models
from django.core.validators import MinValueValidator
from users.models import CustomUser


class Tag(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название тега')
    color = models.CharField(max_length=7, blank=True,
                             null=True, verbose_name='Цвет тега')
    slug = models.SlugField(max_length=200, null=True,
                            unique=True, verbose_name='Слаг тега')

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=200, verbose_name='Название ингредиента')
    measurement_unit = models.CharField(
        max_length=200, verbose_name='Единица измерения')

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}.'


class Recipe(models.Model):
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='recipes',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientToRecipe',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег',
    )
    image = models.ImageField(upload_to='images')
    name = models.CharField(
        max_length=200,
        verbose_name='Название рецепта',
    )
    text = models.TextField(
        verbose_name='Описание рецепта'
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления',
        validators=[
            MinValueValidator(1, 'Минимальное время приготовления = 1')
        ]
    )

    class Meta:
        verbose_name = 'Рецепт',
        verbose_name_plural = 'Рецепты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class IngredientToRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        related_name='ingredients_recipe',
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(1, 'Минимальное количество = 1')
        ]
    )

    class Meta:
        verbose_name = 'Список ингридиентов'
        verbose_name_plural = 'Списки ингридиентов'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient_recipe'
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name} - {self.amount}.'


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='favorite',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='favorite',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe'
            )
        ]

    def __str__(self):
        return f'{self.user} - {self.recipe}.'


class RecipeInShoppingList(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='shop_list',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name="Рецепт")

    class Meta:
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_cart_item'
            )
        ]

    def __str__(self):
        return f'{self.user.email} - {self.recipe.name}.'
