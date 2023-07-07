from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from djoser.serializers import (PasswordSerializer, UserCreateSerializer,
                                UserSerializer)
from rest_framework.fields import SerializerMethodField
from users.models import Subscription

User = get_user_model()


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
        if user == author:
            raise ValidationError(
                'Ошибка! Вы не можете подписаться на себя'
            )
        return data

    def get_recipes(self, obj):
        from api.serializers.recipes_serializers import RecipePreviewSerializer
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
    new_password = models.CharField(blank=False)
    current_password = models.CharField(blank=False)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise ValidationError('Введен некорректный текущий пароль')
        return attrs

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance
