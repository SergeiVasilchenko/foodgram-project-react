from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from rest_framework.fields import SerializerMethodField, ReadOnlyField
from rest_framework.serializers import ModelSerializer, ListSerializer
from rest_framework.relations import PrimaryKeyRelatedField
from drf_extra_fields.fields import Base64ImageField, IntegerField

from recipes.models import Ingredient, Tag, Recipe, RecipeIngredient
from api.serializers.users_serializers import CustomUserSerializer

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


class RecipeIngredientListSerializer(ListSerializer):
    def validate(self, data):
        for item in data:
            if item['amount'] <= 0:
                raise ValidationError('Добавьте необходимое количество')

        ingredient_ids = [item['id'] for item in data]
        if len(set(ingredient_ids)) != len(ingredient_ids):
            raise ValidationError('Ингредиенты должны быть уникальными')
        return data

    def create(self, validated_data):
        recipe_ingredients = []
        for item in validated_data:
            ingredient_id = item['id']
            amount = item['amount']
            recipe_ingredients.append(
                RecipeIngredient(
                    ingredient_id=ingredient_id,
                    amount=amount
                )
            )
        return RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def update(self, instance, validated_data):
        instance_mapping = {item.id: item for item in instance}
        data_mapping = {item['id']: item for item in validated_data}

        for ingredient_id, data in data_mapping.items():
            instance_item = instance_mapping.get(ingredient_id, None)
            if instance_item is not None:
                self.child.update(instance_item, data)
        for ingredient_id, instance_item in instance_mapping.items():
            if ingredient_id not in data_mapping:
                instance_item.delete()
        return instance


class RecipeIngredientWriteSerializer(ModelSerializer):
    id = IntegerField(write_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')
        list_serializer_class = RecipeIngredientListSerializer


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
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amount(
            ingredients=ingredients, recipe=recipe
        )
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amount(
            ingredients=ingredients, recipe=instance
        )
        return instance

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {"request": request}
        return RecipeReadSerializer(
            instance, context=context
        ).data
