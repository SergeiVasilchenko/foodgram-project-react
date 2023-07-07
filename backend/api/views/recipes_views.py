import django.contrib.auth
import django.db.models
# import django.http
# import django_filters.rest_framework
import recipes.models
import rest_framework
# import serializers.recipes_serializers
from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomPagination
from api.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import recipes_serializers

User = django.contrib.auth.get_user_model()


class IngredientViewSet(rest_framework.ReadOnlyModelViewSet):
    queryset = recipes.Ingredient.objects.all()
    serializer_class = recipes_serializers.IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (
        DjangoFilterBackend,
    )
    filterset_class = IngredientFilter


class TagViewSet(rest_framework.ReadOnlyModelViewSet):
    queryset = recipes.Tag.objects.all()
    serializer_class = recipes_serializers.TagSerializer
    permission_classes = (IsAdminOrReadOnly,)


class RecipeViewSet(rest_framework.ModelViewSet):
    queryset = recipes.Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly | IsAdminOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (
        DjangoFilterBackend,
    )
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in rest_framework.SAFE_METHODS:
            return recipes_serializers.RecipeReadSerializer
        return recipes_serializers.RecipeWriteSerializer

    def perform_create(self, serializer):
        author = self.request.user
        serializer.save(author=author)

    def add_item(self, model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return rest_framework.Response(
                status=rest_framework.status.HTTP_400_BAD_REQUEST
            )
        recipe = get_object_or_404(recipes.Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = recipes_serializers.RecipePreviewSerializer(recipe)
        return rest_framework.Response(
            serializer.data,
            status=rest_framework.status.HTTP_201_CREATED
        )

    def delete_item(self, model, user, pk):
        item = model.objects.filter(user=user, recipe__id=pk)
        if item.exists():
            item.delete()
            return rest_framework.Response(
                status=rest_framework.status.HTTP_204_NO_CONTENT
            )
        raise rest_framework.PermissionDenied(
            'У вас недостаточно прав редактировать данный рецепт'
        )

    @rest_framework.action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[rest_framework.IsAuthenticated]
    )
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.write_item(recipes.Favorites, request.user, pk)
        return self.delete_item(recipes.Favorites, request.user, pk)

    @rest_framework.action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[rest_framework.IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.write_item(recipes.UsersRecipes, request.user, pk)
        return self.delete_item(recipes.UsersRecipes, request.user, pk)

    @rest_framework.action(
        detail=False,
        permission_classes=[rest_framework.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        if not user.shopping_cart.exists():
            return rest_framework.Response(
                status=rest_framework.status.HTTP_400_BAD_REQUEST
            )
        ingredients = recipes.RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=django.db.models.Sum('amount'))

        shopping_list = ('Список покупок:\n')
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(
            shopping_list,
            content_type='text/plain'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response
