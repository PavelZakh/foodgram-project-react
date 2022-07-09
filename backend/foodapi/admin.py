from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from .models import (Ingredient, Tag, Recipe, Cart, Favorite,
                     Follow, IngredientsAmount)

User = get_user_model()


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorite_count')
    list_filter = ('author', 'name', 'tags')

    def favorite_count(self, obj):
        return obj.favorites.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_filter = ('name',)


class MyUserAdmin(UserAdmin):
    list_filter = UserAdmin.list_filter + ('username', 'email')


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Cart)
admin.site.register(Favorite)
admin.site.register(Follow)
admin.site.register(IngredientsAmount)
admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)
