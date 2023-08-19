from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination

from recipes.models import (FavoriteRecipe, Ingredient, IngredientToRecipe,
                            Recipe, RecipeInShoppingList, Tag)
from users.models import CustomUser, Subscription


class AuthorSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        return obj.subscriptions.filter(user=obj).exists()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientToRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientToRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    tags = TagSerializer(many=True)
    ingredients = IngredientToRecipeSerializer(
        many=True,
        source='ingredients_recipe'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return FavoriteRecipe.objects.filter(
                user=user,
                recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return RecipeInShoppingList.objects.filter(
                user=user,
                recipe=obj).exists()
        return False


class RecipeIngredienCreateSerialier(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )

    class Meta:
        model = IngredientToRecipe
        fields = ('id', 'amount')


class RecipeInShoppingListSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.ImageField(source='recipe.image')
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = RecipeInShoppingList
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.ImageField(source='recipe.image')
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    class Meta:
        model = FavoriteRecipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredienCreateSerialier(many=True)
    image = Base64ImageField()
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time'
        )

    def validate(self, data):
        ingredients = data['ingredients']
        ingredients_id = set()
        for ingredient in ingredients:
            if not ingredients:
                raise serializers.ValidationError('Не указаны ингредиенты')
            if ingredient['id'] in ingredients_id:
                raise serializers.ValidationError(
                    'Ингредиент в рецепте не может дублироваться.'
                )
            ingredients_id.add(ingredient['id'])
        tags = data['tags']
        tags_id = set()
        for tag in tags:
            if not tags:
                raise serializers.ValidationError('Не указаны теги')
            if tag in tags_id:
                raise serializers.ValidationError(
                    'Тег в рецепте не может дублироваться.'
                )
            tags_id.add(tag)
        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        instance = Recipe.objects.create(**validated_data)
        self.create_ingredients_for_recipe(instance, ingredients, tags)
        instance.tags.set(tags)
        return instance

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        if ingredients:
            instance.ingredients.clear()
            instance.tags.clear()
            self.create_ingredients_for_recipe(instance, ingredients, tags)
        return instance

    def create_ingredients_for_recipe(self, instance, ingredients, tags):
        for tag in tags:
            instance.tags.add(tag)
        IngredientToRecipe.objects.bulk_create([
            IngredientToRecipe(
                recipe=instance,
                ingredient=ingredient.get('id'),
                amount=ingredient.get('amount')
            ) for ingredient in ingredients
        ])

    def to_representation(self, instance):
        serializer = RecipeSerializer(instance=instance, context=self.context)
        return serializer.data


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()

    def get_is_subscribed(self, obj):
        return obj.subscriptions.filter(author=obj).exists()

    def get_recipes(self, obj):
        recipes = Recipe.objects.filter(author=obj)
        paginator = PageNumberPagination()
        result_page = paginator.paginate_queryset(
            recipes, self.context['request'])
        serializer = RecipeSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data).data


class SubscriptionListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    recipes = RecipeSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('author', 'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        return obj.user.subscriptions.filter(author=obj.author).exists()

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()
