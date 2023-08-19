from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (IngredientViewSet, RecipeViewSet, SubscriptionListView,
                    SubscriptionViewSet, TagViewSet)

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
