from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (TagViewSet, IngredientViewSet,
                    RecipeViewSet, SubscriptionViewSet,
                    SubscriptionListView)

app_name = 'api'

router = DefaultRouter()
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet)
router.register('users', SubscriptionViewSet, basename='subscriptions')

urlpatterns = [
    path('users/subscriptions/',
         SubscriptionListView.as_view(), name='subscription'),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
