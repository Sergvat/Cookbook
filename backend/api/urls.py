from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views import TagViewSet, RecipeViewSet

router = DefaultRouter()
# router.register('Subscription', SubscriptionViewSet)
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('tags', TagViewSet)
# router.register('ingredients', IngredientViewSet)

urlpatterns = [
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
]
