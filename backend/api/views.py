from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from rest_framework.generics import ListAPIView
from rest_framework import viewsets, generics, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.db.models import Exists, OuterRef


from .permissions import IsAuthorOrReadOnly
from users.models import Subscription, CustomUser
from recipes.models import Tag, Recipe, Ingredient, ShoppingList, FavoriteRecipe, IngredientToRecipe
from .serializers import (SubscriptionSerializer, SubscriptionListSerializer, TagSerializer,
                          IngredientSerializer, RecipeSerializer,
                          RecipeCreateSerializer, ShoppingListSerializer)


class SubscriptionViewSet(viewsets.GenericViewSet,
                          mixins.CreateModelMixin,
                          mixins.DestroyModelMixin):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        author = get_object_or_404(CustomUser, id=kwargs.get('id'))
        if author == request.user:
            return Response(
                {'error': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription, created = Subscription.objects.get_or_create(
            author=author, user=request.user)
        if created:
            serializer = self.get_serializer_class()(
                instance=subscription, context=self.get_serializer_context())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        author = get_object_or_404(CustomUser, id=kwargs.get('id'))
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


class ShoppingListViewSet(generics.ListAPIView):
    serializer_class = ShoppingListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)


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
            if not FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists():
                FavoriteRecipe.objects.create(user=user, recipe=recipe)
                return Response(status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Рецепт уже в избранном.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'DELETE':
            favorites = FavoriteRecipe.objects.filter(user=user, recipe=recipe)
            if favorites.exists():
                favorites.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'error': 'Рецепт не находится в избранном.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        user = self.request.user
        recipe = self.get_object()
        if request.method == 'POST':
            if not ShoppingList.objects.filter(user=user, ingredients__in=recipe.ingredients.all()).exists():
                ShoppingList.objects.create(
                    user=user, ingredients=recipe.ingredients.all())
                return Response(status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Рецепт уже в корзине.'}, status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'DELETE':
            cart_ingredients = ShoppingList.objects.filter(
                user=user, ingredients__in=recipe.ingredients.all())
            if cart_ingredients.exists():
                cart_ingredients.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'error': 'Рецепт отсутствует в корзине.'}, status=status.HTTP_400_BAD_REQUEST)

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
            queryset = queryset.annotate(
                is_in_shopping_cart=Exists(
                    ShoppingList.objects.filter(
                        user=user, recipe=OuterRef('pk'))
                )
            ).filter(is_in_shopping_cart=True)

        if slug:
            queryset = queryset.filter(tags__slug=slug)

        return queryset


class ShoppingListDownloadAPIView(APIView):
    def get(self, request, *args, **kwargs):
        ingredients = IngredientToRecipe.objects.filter(
            recipe__shoppinglist__user=request.user).values(
            'ingredient__name', 'ingredient__measurement_unit').annotate(
            amount=Sum('amount'))

        shopping_cart = '\n'.join([
            f'{ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]}) – '
            f'{ingredient["amount"]}'
            for ingredient in ingredients
        ])

        response = HttpResponse(shopping_cart, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename=shopping_cart.txt')

        return response
