from django.http import HttpResponse
from rest_framework.generics import ListAPIView
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Exists, OuterRef


from .permissions import IsAuthorOrReadOnly
from users.models import Subscription, CustomUser
from recipes.models import (Tag, Recipe,
                            Ingredient, FavoriteRecipe,
                            IngredientToRecipe, RecipeInShoppingList)
from .serializers import (SubscriptionSerializer, SubscriptionListSerializer,
                          TagSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeSerializer,
                          RecipeCreateSerializer, RecipeInShoppingListSerializer)


class SubscriptionViewSet(viewsets.GenericViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @action(detail=True, methods=["POST", "DELETE"], url_path="subscribe")
    def subscribe(self, request, *args, **kwargs):
        author = self.get_object()
        if request.method == 'POST':
            if author == request.user:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription, created = Subscription.objects.get_or_create(
                author=author, user=request.user)
            if created:
                serializer = self.get_serializer_class()(
                    instance=author, context=self.get_serializer_context())
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Подписка уже оформлена'}, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                author=author, user=request.user)
            if subscription:
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'error': 'Вы не являетесь подписчиком данного пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )


class SubscriptionListView(ListAPIView):
    serializer_class = SubscriptionListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)


class TagViewSet(mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__startswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        user = self.request.user
        recipe = self.get_object()
        if request.method == 'POST':
            if not FavoriteRecipe.objects.filter(
                    user=user, recipe=recipe).exists():
                favorite = FavoriteRecipe.objects.create(user=user, recipe=recipe)
                serializer = FavoriteSerializer(favorite)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': 'Рецепт уже в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'DELETE':
            favorites = FavoriteRecipe.objects.filter(user=user, recipe=recipe)
            if favorites.exists():
                favorites.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {'error': 'Рецепт не находится в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        user = self.request.user
        recipe = self.get_object()
        if request.method == 'POST':
            recipe_in_shopping_list, created = RecipeInShoppingList.objects.get_or_create(
                recipe=recipe, user=user)
            if created:
                serializer = RecipeInShoppingListSerializer(
                    recipe_in_shopping_list)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': 'Рецепт уже в корзине.'},
                    status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'DELETE':
            items = RecipeInShoppingList.objects.filter(
                recipe=recipe, user=user)
            if items.exists():
                items.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {'error': 'Рецепт отсутствует в корзине.'},
                    status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'])
    def download_shopping_cart(self, request):
        items = RecipeInShoppingList.objects.filter(user=request.user)
        ingredients = {}
        for item in items:
            recipe = item.recipe
            for ingredient in recipe.ingredients.all():
                if ingredient.id in ingredients.keys():
                    ingredients[ingredient.id] += IngredientToRecipe.objects.get(
                        recipe=recipe, ingredient=ingredient).amount
                else:
                    ingredients[ingredient.id] = IngredientToRecipe.objects.get(
                        recipe=recipe, ingredient=ingredient).amount
        result = []
        for id, amount in ingredients.items():
            ingredient = Ingredient.objects.get(id=id)
            result.append(
                f'{ingredient.name} ({ingredient.measurement_unit}) - {amount}')

        file_data = '\n'.join(result).encode('utf-8')
        response = HttpResponse(file_data, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=shopping_cart.txt'

        return response

    def get_queryset(self):
        queryset = super().get_queryset()
        author = self.request.query_params.get('author')
        tags = self.request.query_params.getlist('tags')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        slug = self.request.query_params.get('tag_slug')
        if author:
            queryset = queryset.filter(author_id=int(author))

        if tags is not None and len(tags):
            queryset = queryset.filter(tags__slug__in=tags)

        if is_favorited == 'true':
            user = self.request.user
            queryset = queryset.annotate(
                is_favorited=Exists(
                    FavoriteRecipe.objects.filter(
                        user=user, recipe=OuterRef('pk'))
                )
            ).filter(is_favorited=True)

        if is_in_shopping_cart == 'true':
            user = self.request.user
            queryset = queryset.filter()

        if slug:
            queryset = queryset.filter(tags__slug=slug)

        return queryset
