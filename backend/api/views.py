from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from rest_framework import viewsets, generics, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.views import APIView


from .permissions import IsAuthorOrReadOnly
from users.models import Subscription, CustomUser
from recipes.models import Tag, Recipe, Ingredient, ShoppingList, FavoriteRecipe, IngredientToRecipe
from .serializers import (SubscriptionsSerializer, TagSerializer,
                          IngredientSerializer, RecipeSerializer,
                          RecipeCreateSerializer, ShoppingListSerializer)


class SubscriptionCreateDestroyAPIView(mixins.CreateModelMixin,
                                       mixins.DestroyModelMixin,
                                       generics.GenericAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionsSerializer
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
            return Response(
                {'error': 'Подписка уже оформлена'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer_class()(
            instance=subscription, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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


class TagViewSet(mixins.ListModelMixin,
                 viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(mixins.ListModelMixin,
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
        if request.metod == 'POST':
            if not FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists():
                FavoriteRecipe.objects.create(user=user, recipe=recipe)
                return Response(status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Рецепт уже в избранном.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.metod == 'DELETE':
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
        if request.metod == 'post':
            if not ShoppingList.objects.filter(user=user, recipe=recipe).exists():
                ShoppingList.objects.create(user=user, recipe=recipe)
                return Response(status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Рецепт уже в корзине.'}, status=status.HTTP_400_BAD_REQUEST)
        if request.metod == 'delete':
            cart_ingredients = ShoppingList.objects.filter(
                user=user, recipe=recipe)
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
            queryset = queryset.filter(is_favorited=True)

        if is_in_shopping_cart == 'true':
            queryset = queryset.filter(is_in_shopping_cart=True)

        if slug:
            queryset = queryset.filter(tags__slug=slug)

        return queryset


class ShoppingListDownloadAPIView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user

        ingredients = IngredientToRecipe.objects.filter(
            recipe__shoppinglist__user=user).values(
            'ingredients__name', 'ingredients__measurement_unit').annotate(
            amount=Sum('amount'))

        unique_ingredients = {}
        for ingredient in ingredients:
            name = ingredient['ingredients__name']
            unit = ingredient['ingredients__measurement_unit']
            amount = ingredient['amount']

            key = (name, unit)
            if key in unique_ingredients:
                unique_ingredients[key] += amount
            else:
                unique_ingredients[key] = amount

        shopping_cart = '\n'.join([
            f'{name} ({unit}) – {amount}'
            for (name, unit), amount in unique_ingredients.items()
        ])

        response = HttpResponse(shopping_cart, content_type='text/plain')
        file_name = f'{user.username}.txt'
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'

        return response
