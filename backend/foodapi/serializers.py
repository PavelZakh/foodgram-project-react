from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserCreateSerializer, UserSerializer

from .models import (Ingredient, Tag, Recipe,
                     Follow, IngredientsAmount)

User = get_user_model()


class FixedUserSerializer(UserSerializer):
    """Сериализатор для модели User."""
    is_subscribed = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = get_object_or_404(User, id=self.context.get('request').user.id)
        if not user.is_anonymous:
            return Follow.objects.filter(user=user, author=obj.id).exists()
        return False


class FixedCreateUserSerializer(UserCreateSerializer):
    """Сериализатор на создание модели User."""
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())],
    )

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'password')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientsAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для модели IngredientsAmount."""
    id = serializers.IntegerField(
        source='ingredient.id',
        read_only=True,
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True,
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True,
    )

    class Meta:
        model = IngredientsAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')
        validators = [
            UniqueTogetherValidator(
                queryset=IngredientsAmount.objects.all(),
                fields=['ingredient', 'recipe'],
                message='Данный ингридиент уже содержится в этом рецепте!'
            )
        ]


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""
    tags = TagSerializer(
        many=True,
        read_only=True,
    )
    author = FixedUserSerializer(
        read_only=True,
    )
    ingredients = IngredientsAmountSerializer(
        source='ingredientsamount_set',
        many=True,
        read_only=True,
    )
    is_favorited = serializers.BooleanField(
        read_only=True,
    )
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True,
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, obj):
        user = get_object_or_404(User, id=self.context.get('request').user.id)
        if not user.is_anonymous:
            return Recipe.objects.filter(favorites__user=user, author=obj.id).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = get_object_or_404(User, id=self.context.get('request').user.id)
        if not user.is_anonymous:
            return Recipe.objects.filter(carts__user=user, author=obj.id).exists()
        return False

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': 'Нужен хоть один ингридиент для рецепта'})
        ingredient_list = []
        for ingredient_item in ingredients:
            ingredient = get_object_or_404(Ingredient,
                                           id=ingredient_item['id'])
            if ingredient in ingredient_list:
                raise serializers.ValidationError('Ингридиенты должны '
                                                  'быть уникальными')
            ingredient_list.append(ingredient)
            if int(ingredient_item['amount']) < 0:
                raise serializers.ValidationError({
                    'ingredients': ('Убедитесь, что значение количества '
                                    'ингредиента больше 0')
                })
        data['ingredients'] = ingredients
        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)

        for ingredient in ingredients:
            IngredientsAmount.objects.create(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'),
            )

        tags_data = self.initial_data.get('tags')
        recipe.tags.set(tags_data)

        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        instance.text = validated_data.get('text', instance.text)

        instance.tags.clear()
        tags_data = self.initial_data.get('tags')
        instance.tags.set(tags_data)

        IngredientsAmount.objects.filter(recipe=instance).all().delete()
        ingredients = validated_data.get('ingredients')
        for ingredient in ingredients:
            IngredientsAmount.objects.create(
                recipe=instance,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'),
            )

        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )

        instance.save()
        return instance


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для ShoppingList."""
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Follow."""
    email = serializers.EmailField(
        source='author.email',
        read_only=True,
    )
    id = serializers.IntegerField(
        source='author.id',
        read_only=True,
    )
    username = serializers.CharField(
        source='author.username',
        read_only=True,
    )
    first_name = serializers.CharField(
        source='author.first_name',
        read_only=True,
    )
    last_name = serializers.CharField(
        source='author.last_name',
        read_only=True,
    )
    is_subscribed = serializers.BooleanField(
        read_only=True,
    )
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = Follow
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count',
        )

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(user=obj.user, author=obj.author).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_queryset = Recipe.objects.filter(author=obj.author)
        recipes_limit = request.GET.get('recipes_limit')
        if recipes_limit:
            recipes_queryset = recipes_queryset[:int(recipes_limit)]
        return ShoppingCartSerializer(recipes_queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()
