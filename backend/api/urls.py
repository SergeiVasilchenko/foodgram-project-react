import django.urls
import rest_framework.routers

from .views import recipes_views, users_views

app_name = 'api'

router = rest_framework.routers.DefaultRouter()

router.register(
    'ingredients',
    recipes_views.IngredientViewSet,
    basename='ingredients'
)
router.register('tags', recipes_views.TagViewSet, basename='tags')
router.register(
    'recipes',
    recipes_views.RecipeViewSet,
    basename='recipes'
)
router.register('users', users_views.CustomUserViewSet, basename='users')


urlpatterns = [
    django.urls.path('', django.urls.include(router.urls)),
    django.urls.path('', django.urls.include('djoser.urls')),
    django.urls.path('auth/', django.urls.include('djoser.urls.authtoken')),
]
