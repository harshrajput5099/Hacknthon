from rest_framework import serializers
from .models import Product, Category, FarmerProfile, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['full_name', 'email']

class FarmerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = FarmerProfile
        fields = ['user', 'city', 'state']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['category_id', 'category_name', 'description']

class ProductSerializer(serializers.ModelSerializer):
    farmer = FarmerProfileSerializer(read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'product_id', 'product_name', 'description', 'price',
            'stock', 'image', 'created_at', 'farmer', 'category',
            'category_name'
        ]
        read_only_fields = ['product_id', 'created_at', 'farmer'] 