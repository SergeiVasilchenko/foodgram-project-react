from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Prefetch


from djoser.serializers import (UserSerializer, UserCreateSerializer,
                                PasswordSerializer)

from rest_framework.fields import (SerializerMethodField, CharField,
                                   ReadOnlyField)
from rest_framework.serializers import ModelSerializer
from rest_framework.relations import PrimaryKeyRelatedField

from drf_extra_fields.fields import Base64ImageField, IntegerField

from recipes.models import Ingredient, Tag, Recipe, RecipeIngredient
from users.models import Subscription

User = get_user_model()


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = Ingredient
        fields = (
            'id', 'name', 'measurement_unit',
        )


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'name', 'color', 'slug',
        )


class CustomUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, author=obj).exists()


class RecipePreviewSerializer(ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'author',
            'name',
            'image',
            'cooking_time'
        )


class SubscriptionSerializer(CustomUserSerializer):
    recipes_count = SerializerMethodField()
    recipes = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes_count', 'recipes'
        )
        read_only_fields = ('email', 'username')

    def validate(self, data):
        author = self.instance
        user = self.context.get('request').user
        if Subscription.objects.filter(author=author, user=user).exists():
            raise ValidationError(
                f'Вы уже подписаны на {author}'
            )
        elif user == author:
            raise ValidationError(
                'Ошибка! Вы не можете подписаться на себя'
            )
        else:
            return data

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipePreviewSerializer(
            recipes, many=True, read_only=True
        )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


# class IngredientReadSerializer(ModelSerializer):
#     id = IntegerField(source='ingredient.id')
#     name = ReadOnlyField(source='ingredient.name')
#     measurement_unit = ReadOnlyField(source='ingredient.measurement_unit')

#     class Meta:
#         model = RecipeIngredient
#         fields = (
#             'id',
#             'name',
#             'measurement_unit',
#             'amount',
#         )


class RecipeIngredientReadSerializer(ModelSerializer):
    id = IntegerField(read_only=True, source='ingredient.id')
    name = ReadOnlyField(
        source='ingredient.name'
    )
    measurement_unit = ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'amount',
            'name',
            'measurement_unit',
        )

    def get_ingredient(self, obj):
        ingredient = obj.ingredient
        serializer = IngredientSerializer(ingredient, many=True)
        return serializer.data


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        many=True,
        source='ingredient_in_recipe'
    )
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_ingredients(self, obj):
        recipe = obj
        ingredients = recipe.ingredients.prefetch_related(
            Prefetch(
                'recipeingredient_set',
                queryset=RecipeIngredient.objects.filter(recipe=recipe),
                to_attr='recipe_ingredients'
            )
        )
        ingredient_data = [
            {
                'id': ingredient.id,
                'name': ingredient.name,
                'measurement_unit': ingredient.measurement_unit,
                'amount': (
                    ingredient.recipe_ingredients[0].amount
                    if ingredient.recipe_ingredients
                    else None
                )
            }
            for ingredient in ingredients
        ]
        return ingredient_data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.shopping_cart.filter(recipe=obj).exists()


class RecipeIngredientWriteSerializer(ModelSerializer):
    id = IntegerField(write_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeWriteSerializer(ModelSerializer):
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        allow_empty=False
    )
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        allow_empty=False
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    @transaction.atomic
    def create_ingredients_amount(self, ingredients, recipe):
        recipe_ingredients = [
            RecipeIngredient(
                ingredient_id=ingredient['id'],
                recipe=recipe,
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        try:
            recipe = Recipe.objects.create(**validated_data)
            recipe.tags.set(tags)
            self.create_ingredients_amount(
                ingredients=ingredients, recipe=recipe
            )
        except IntegrityError as error:
            raise ValidationError(
                'Ингредиенты должны быть уникальными'
            ) from error
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')

        try:
            instance = super().update(instance, validated_data)
            instance.tags.set(tags)
            instance.ingredients.clear()
            self.create_ingredients_amount(
                ingredients=ingredients, recipe=instance
            )
        except IntegrityError as error:
            raise ValidationError(
                'Ингредиенты должны быть уникальными'
            ) from error

        return instance

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {"request": request}
        return RecipeReadSerializer(
            instance, context=context
        ).data


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )


class PasswordChangeSerializer(PasswordSerializer):
    new_password = CharField(required=True)
    current_password = CharField(required=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise ValidationError('Введен некорректный текущий пароль')
        return attrs

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance
