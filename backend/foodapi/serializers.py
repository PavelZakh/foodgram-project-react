from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Ingredient, Tag, Recipe, Follow, IngredientsAmount

User = get_user_model()


class FixedUserSerializer(UserSerializer):
    """Сериализатор для модели User."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name', 'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
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
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name', 'password'
        )


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = '__all__'

    def to_internal_value(self, data):
        return Tag.objects.get(id=data)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = '__all__'

    def to_internal_value(self, data):
        return Ingredient.objects.get(id=data)


class IngredientsAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для модели IngredientsAmount."""
    id = IngredientSerializer()
    name = serializers.CharField(
        required=False
    )
    measurement_unit = serializers.CharField(
        required=False
    )
    amount = serializers.IntegerField()

    def to_representation(self, instance):
        data = IngredientSerializer(instance.ingredient).data
        data["amount"] = instance.amount
        return data

    class Meta:
        model = IngredientsAmount
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""
    tags = TagSerializer(
        many=True,
    )
    author = FixedUserSerializer(
        read_only=True,
    )
    ingredients = IngredientsAmountSerializer(
        source='ingredientsamount_set',
        many=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Recipe.objects.filter(favorites__user=user, id=obj.id).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Recipe.objects.filter(carts__user=user, id=obj.id).exists()

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': 'Нужен минимум один ингредиент для рецепта!'})
        ingredients_ids = list(map(lambda ingr: ingr['id'], ingredients))
        if len(set(ingredients_ids)) < len(ingredients_ids):
            raise serializers.ValidationError('Ингредиенты должны '
                                              'быть уникальными!')
        for ingredient in ingredients:
            if int(ingredient['amount']) < 0:
                raise serializers.ValidationError({
                    'ingredients': ('Убедитесь, что значение количества '
                                    'ингредиента больше 0!')
                })
        return ingredients

    def ingredients_create(self, ingredients, recipe):
        objects = [
            IngredientsAmount(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount'],
            )
            for ingredient in ingredients
        ]
        IngredientsAmount.objects.bulk_create(objects)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredientsamount_set')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        self.ingredients_create(ingredients, recipe)
        recipe.tags.set(tags_data)

        return recipe

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags_data)

        IngredientsAmount.objects.filter(recipe=instance).delete()
        ingredients = validated_data.pop('ingredientsamount_set')
        self.ingredients_create(ingredients, instance)

        return super().update(instance, validated_data)


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
    is_subscribed = serializers.SerializerMethodField()
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
