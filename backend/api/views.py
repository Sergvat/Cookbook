from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics, mixins, permissions, status
from rest_framework.response import Response


from users.models import Subscription, CustomUser
from recipes.models import Tag, Recipe, Ingredient
from api.serializers import (SubscriptionsSerializer, TagSerializer,
                             IngredientSerializer, RecipeSerializer,
                             RecipeCreateSerializer)


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


class TagViewSet(generics.ListCreateAPIView,
                 viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(generics.ListCreateAPIView,
                        viewsets.GenericViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
