from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TagViewSet, IngredientViewSet, RecipeViewSet, SubscriptionViewSet, SubscriptionListView, ShoppingListDownloadAPIView

app_name = 'api'

router = DefaultRouter()
router.register('subscriptions', SubscriptionViewSet, basename='subscriptions')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet)

urlpatterns = [
    path('users/subscriptions/',
         SubscriptionListView.as_view(), name='subscription'),
    path('recipes/download_shopping_cart/',
         ShoppingListDownloadAPIView.as_view(), name='download_shopping_cart'),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
