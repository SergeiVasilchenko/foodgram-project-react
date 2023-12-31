import recipes.models
import rest_framework
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField, IntegerField

from .users_serializers import CustomUserSerializer

User = get_user_model()


class IngredientSerializer(rest_framework.serializers.ModelSerializer):
    class Meta:
        model = recipes.models.Ingredient
        fields = (
            'id', 'name', 'measurement_unit',
        )


class TagSerializer(rest_framework.serializers.ModelSerializer):
    class Meta:
        model = recipes.models.Tag
        fields = (
            'id', 'name', 'color', 'slug',
        )


class RecipePreviewSerializer(rest_framework.serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = recipes.models.Recipe
        fields = (
            'author',
            'name',
            'image',
            'cooking_time'
        )


class RecipeIngredientReadSerializer(
    rest_framework.serializers.ModelSerializer
):
    id = IntegerField(read_only=True, source='ingredient.id')
    name = rest_framework.fields.ReadOnlyField(
        source='ingredient.name'
    )
    measurement_unit = rest_framework.fields.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = recipes.models.RecipeIngredient
        fields = (
            'id',
            'amount',
            'name',
            'measurement_unit',
        )


class RecipeReadSerializer(rest_framework.serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        many=True,
        source='ingredient_in_recipe'
    )
    is_favorited = rest_framework.fields.SerializerMethodField(read_only=True)
    is_in_shopping_cart = rest_framework.fields.SerializerMethodField(
        read_only=True
    )
    image = Base64ImageField()

    class Meta:
        model = recipes.models.Recipe
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


class RecipeIngredientListSerializer(
    rest_framework.serializers.ListSerializer
):
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
                recipes.models.RecipeIngredient(
                    ingredient_id=ingredient_id,
                    amount=amount
                )
            )
        return recipes.models.RecipeIngredient.objects.bulk_create(
            recipe_ingredients
        )

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


class RecipeIngredientWriteSerializer(
    rest_framework.serializers.ModelSerializer
):
    id = IntegerField(write_only=True)

    class Meta:
        model = recipes.models.RecipeIngredient
        fields = ('id', 'amount')
        list_serializer_class = RecipeIngredientListSerializer


class TagListSerializer(rest_framework.serializers.ListSerializer):
    def validate(self, data):
        tags_ids = [item for item in data]
        if len(set(tags_ids)) != len(tags_ids):
            raise ValidationError('Теги должны быть уникальными')
        return data

    def create(self, validated_data):
        tags = [
            recipes.models.Tag.objects.get(id=item)
            for item in validated_data
        ]
        return recipes.models.Tag.objects.bulk_create(tags)


class RecipeWriteSerializer(rest_framework.serializers.ModelSerializer):
    tags = TagListSerializer(
        child=IntegerField(),
        allow_empty=False
    )
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        allow_empty=False
    )
    image = Base64ImageField()

    class Meta:
        model = recipes.models.Recipe
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

    def validate_tags(self, tags):
        if not tags:
            raise ValidationError({
                'tags': 'Нужно выбрать хотя бы оин тэг'
            })
        valid_tags = []
        for tag in tags:
            if not recipes.models.Tag.objects.filter(id__in=tags).exists():
                raise ValidationError('Тега не сущестует')
            if tag in valid_tags:
                raise ValidationError('Теги не должы повторяться')
            valid_tags.append(tag)
        return tags

    @transaction.atomic
    def create_ingredients_amount(self, ingredients, recipe):
        recipe_ingredients = [
            recipes.models.RecipeIngredient(
                ingredient_id=ingredient['id'],
                recipe=recipe,
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ]
        recipes.models.RecipeIngredient.objects.bulk_create(recipe_ingredients)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = recipes.models.Recipe.objects.create(**validated_data)
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
