import django.urls
import rest_framework.routers
import views.recipes_views
import views.users_views

app_name = 'api'

router = rest_framework.routers.DefaultRouter()

router.register(
    'ingredients',
    views.recipes_views.IngredientViewSet,
    basename='ingredients'
)
router.register('tags', views.recipes_views.TagViewSet, basename='tags')
router.register(
    'recipes',
    views.recipes_views.RecipeViewSet,
    basename='recipes'
)
router.register('users', views.users_views.CustomUserViewSet, basename='users')


urlpatterns = [
    django.urls.path('', django.urls.include(router.urls)),
    django.urls.path('', django.urls.include('djoser.urls')),
    django.urls.path('auth/', django.urls.include('djoser.urls.authtoken')),
]
