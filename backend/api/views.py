from django.db.models import Exists, OuterRef, Sum
from django.http import HttpResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (FavoriteRecipe, Ingredient, IngredientToRecipe,
                            Recipe, RecipeInShoppingList, Tag)
from users.models import CustomUser, Subscription
from .paginations import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeCreateSerializer,
                          RecipeInShoppingListSerializer, RecipeSerializer,
                          SubscriptionSerializer, TagSerializer, AuthorSerializer)


class SubscriptionViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = CustomPagination

    @action(detail=True,
            methods=["POST", "DELETE"], url_path="subscribe",
            permission_classes=[permissions.IsAuthenticated])
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
            return Response(
                {'error': 'Подписка уже оформлена'},
                status=status.HTTP_400_BAD_REQUEST)
        subscription = Subscription.objects.filter(
            author=author, user=request.user)
        if subscription.exists():
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Вы не являетесь подписчиком данного пользователя'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False,
            methods=['GET'], url_path="subscriptions",
            permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(subscribers__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @action(detail=False, 
            methods=['GET'], url_path='me', 
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = AuthorSerializer(request.user, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)


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
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateSerializer
        if self.action == 'favorite':
            return FavoriteSerializer
        if self.action == 'shopping_cart':
            return RecipeInShoppingListSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create_or_delete(self, request, model, pk=None):
        user = self.request.user
        recipe = self.get_object()
        queryset = model.objects.filter(user=user, recipe=recipe)
        if request.method == 'POST':
            if queryset.exists():
                return Response(
                    {'error': 'Рецепт уже находится в списке.'},
                    status=status.HTTP_400_BAD_REQUEST)
            obj = model.objects.create(user=user, recipe=recipe)
            serializer = self.get_serializer(obj)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED)
        if queryset.exists():
            queryset.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Рецепт не находится в списке.'},
            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.create_or_delete(request, model=FavoriteRecipe, pk=pk)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.create_or_delete(
            request, model=RecipeInShoppingList, pk=pk
        )

    @action(detail=False,
            methods=['GET'],
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = IngredientToRecipe.objects.filter(
            recipe__recipeinshoppinglist__user=request.user).values(
            'ingredient__name', 'ingredient__measurement_unit').annotate(
            quantity=Sum('amount'))
        result = []
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
            quantity = ingredient['quantity']
            result.append(f'{name} ({unit}) - {quantity}')

        file_data = '\n'.join(result).encode('utf-8')
        response = HttpResponse(file_data, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename=shopping_cart.txt')
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

        if self.request.user.is_authenticated:
            if is_favorited == '1':
                user = self.request.user
                queryset = queryset.annotate(
                    is_favorited=Exists(
                        FavoriteRecipe.objects.filter(
                            user=user, recipe=OuterRef('pk'))
                    )
                ).filter(is_favorited=True)

            if is_in_shopping_cart == '1':
                user = self.request.user
                queryset = queryset.annotate(
                    is_in_shopping_cart=Exists(
                        RecipeInShoppingList.objects.filter(
                            user=user, recipe=OuterRef('pk')
                        )
                    )
                ).filter(is_in_shopping_cart=True)

        if slug:
            queryset = queryset.filter(tags__slug=slug)

        return queryset.distinct()
