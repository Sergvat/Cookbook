from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action


from .permissions import IsAuthorOrReadOnly
from users.models import Subscription, CustomUser
from recipes.models import Tag, Recipe, Ingredient, ShoppingList
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

    # @action(detail=True, methods=['post', 'delete'])
    # def favorite(self, request, pk=None):
    #     recipe = self.get_object()
    #     if request.metod == 'post':

    #     if request.metod == 'delete':

    #     return Response(serializer.data,
    #                         status=status.)

    # @action(detail=True, methods=['post', 'delete'])
    # def shopping_cart(self, request, pk=None):
    #     if request.metod == 'post':

    #     if request.metod == 'delete':

    #     return Response(serializer.data,
    #                         status=status.)

    def get_queryset(self):
        queryset = super().get_queryset()
        author = self.request.query_params.get('author')
        tags = self.request.query_params.get('tags')
        if author:
            queryset = queryset.filter(author_id=int(author))
        if len(tags):
            queryset = queryset.filter(tags__in=tags)
        return queryset
