from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count
from .forms import UserSignupForm, ProductForm, FarmerProfileForm, CustomerProfileForm
from .models import FarmerProfile, CertificationRequest, User, Product, Category, CustomerProfile, Order, OrderItem, Payment, Review
from .serializers import ProductSerializer, CategorySerializer
from django.utils import timezone


def signup_view(request):
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')  
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserSignupForm()
    return render(request, 'signup.html', {'form': form})


@login_required
def dashboard_view(request):
    if request.user.role == 'Customer':
        return redirect('customer_dashboard')
    elif request.user.role == 'Farmer':
        return redirect('farmer_dashboard')
    elif request.user.role == 'Admin':
        return redirect('admin_dashboard')
    elif request.user.role == 'Verifier':
        return redirect('verifier_dashboard')
    else:
        messages.error(request, "Invalid user role.")
        return redirect('home')  # Redirect to home if the role is invalid

@login_required
def customer_dashboard(request):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can access this dashboard.')
        return redirect('home')
    
    try:
        customer_profile = CustomerProfile.objects.get(user=request.user)
    except CustomerProfile.DoesNotExist:
        customer_profile = None
    
    context = {
        'customer_profile': customer_profile,
    }
    return render(request, 'customer/customer_dashboard.html', context)

@login_required
def farmer_dashboard(request):
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can access this dashboard.')
        return redirect('home')
    
    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
        recent_products = Product.objects.filter(farmer=farmer_profile).order_by('-created_at')[:5]
    except FarmerProfile.DoesNotExist:
        farmer_profile = None
        recent_products = []
    
    context = {
        'farmer_profile': farmer_profile,
        'recent_products': recent_products,
    }
    return render(request, 'farmer/farmer_dashboard.html', context)

def admin_dashboard(request):
    return render(request, 'admin/admin_dashboard.html')

@login_required
def verifier_dashboard(request):
    if request.user.role != 'Verifier':
        messages.error(request, 'Only verifiers can access this dashboard.')
        return redirect('home')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', '-submitted_at')
    
    # Query certification requests
    certification_requests = CertificationRequest.objects.all()
    
    # Apply filters
    if status:
        certification_requests = certification_requests.filter(status=status)
    
    # Apply sorting
    certification_requests = certification_requests.order_by(sort)
    
    context = {
        'certification_requests': certification_requests,
    }
    return render(request, 'verifier/certification_requests.html', context)

def index_view(request):
    return render(request, 'index.html')

@login_required
def add_product(request):
    # Check if user is a farmer
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can add products.')
        return redirect('product_list')

    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
    except FarmerProfile.DoesNotExist:
        messages.error(request, 'Please complete your farmer profile before adding products.')
        return redirect('farmer_dashboard')

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                product = form.save(commit=False)
                product.farmer = farmer_profile
                
                # Handle image upload
                if 'image' in request.FILES:
                    product.image = request.FILES['image']
                
                product.save()
                messages.success(request, 'Product added successfully!')
                return redirect('product_list')
            except Exception as e:
                messages.error(request, f'Error saving product: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'farmer': farmer_profile,
        'categories': Category.objects.all(),
    }
    return render(request, 'add_product.html', context)

@login_required
def edit_product(request, product_id):
    # Check if user is a farmer
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can edit products.')
        return redirect('product_list')

    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
        product = get_object_or_404(Product, product_id=product_id, farmer=farmer_profile)
    except FarmerProfile.DoesNotExist:
        messages.error(request, 'Product not found or you do not have permission to edit it.')
        return redirect('product_list')

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            try:
                product = form.save(commit=False)
                product.farmer = farmer_profile
                
                # Handle image upload
                if 'image' in request.FILES:
                    product.image = request.FILES['image']
                
                product.save()
                messages.success(request, 'Product updated successfully!')
                return redirect('product_list')
            except Exception as e:
                messages.error(request, f'Error updating product: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'farmer': farmer_profile,
        'categories': Category.objects.all(),
    }
    return render(request, 'edit_product.html', context)

@login_required
def delete_product(request, product_id):
    # Check if user is a farmer
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can delete products.')
        return redirect('product_list')

    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
        product = get_object_or_404(Product, product_id=product_id, farmer=farmer_profile)
        product.delete()
        messages.success(request, 'Product deleted successfully!')
    except FarmerProfile.DoesNotExist:
        messages.error(request, 'Product not found or you do not have permission to delete it.')
    
    return redirect('product_list')

# Product List View
def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'product_list.html', {
        'products': products,
        'categories': categories
    })

# REST API Views
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'farmer']
    search_fields = ['product_name', 'description']
    ordering_fields = ['price', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        try:
            farmer_profile = FarmerProfile.objects.get(user=self.request.user)
            serializer.save(farmer=farmer_profile)
        except FarmerProfile.DoesNotExist:
            return Response(
                {"error": "Only farmers can create products"},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=False, methods=['get'])
    def my_products(self, request):
        try:
            farmer_profile = FarmerProfile.objects.get(user=request.user)
            products = self.queryset.filter(farmer=farmer_profile)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        except FarmerProfile.DoesNotExist:
            return Response(
                {"error": "Farmer profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

@login_required
def edit_farmer_profile(request):
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can edit their profile.')
        return redirect('home')
    
    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
    except FarmerProfile.DoesNotExist:
        farmer_profile = None
    
    if request.method == 'POST':
        form = FarmerProfileForm(request.POST, instance=farmer_profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('farmer_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FarmerProfileForm(instance=farmer_profile)
    
    context = {
        'form': form,
        'farmer_profile': farmer_profile,
    }
    return render(request, 'farmer/edit_profile.html', context)

@login_required
def edit_customer_profile(request):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can edit their profile.')
        return redirect('home')
    
    try:
        customer_profile = CustomerProfile.objects.get(user=request.user)
    except CustomerProfile.DoesNotExist:
        customer_profile = None
    
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=customer_profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('customer_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerProfileForm(instance=customer_profile)
    
    context = {
        'form': form,
        'customer_profile': customer_profile,
    }
    return render(request, 'customer/edit_profile.html', context)

@login_required
def certification_request(request):
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can request certification.')
        return redirect('home')
    
    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
        certification_requests = CertificationRequest.objects.filter(farmer=farmer_profile).order_by('-submitted_at')
    except FarmerProfile.DoesNotExist:
        messages.error(request, 'Please complete your farmer profile first.')
        return redirect('farmer_dashboard')
    
    if request.method == 'POST':
        if 'submitted_documents' in request.FILES:
            CertificationRequest.objects.create(
                farmer=farmer_profile,
                submitted_documents=request.FILES['submitted_documents']
            )
            messages.success(request, 'Certification request submitted successfully!')
            return redirect('certification_request')
        else:
            messages.error(request, 'Please upload your documents.')
    
    context = {
        'certification_requests': certification_requests,
        'farmer_profile': farmer_profile,
    }
    return render(request, 'farmer/certification_request.html', context)

@login_required
def update_certification_status(request, request_id):
    if request.user.role != 'Verifier':
        messages.error(request, 'Only verifiers can update certification status.')
        return redirect('home')
    
    if request.method != 'POST':
        return redirect('verifier_dashboard')
    
    try:
        cert_request = CertificationRequest.objects.get(id=request_id)
        action = request.POST.get('action')
        inspection_date = request.POST.get('inspection_date')
        
        if action == 'approve':
            cert_request.status = 'approved'
            cert_request.inspection_date = inspection_date
            cert_request.approval_date = timezone.now().date()
            messages.success(request, 'Certification request approved successfully.')
        elif action == 'reject':
            cert_request.status = 'rejected'
            cert_request.inspection_date = inspection_date
            messages.success(request, 'Certification request rejected successfully.')
        
        cert_request.save()
        
    except CertificationRequest.DoesNotExist:
        messages.error(request, 'Certification request not found.')
    
    return redirect('verifier_dashboard')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def shop_products(request):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can access the shop.')
        return redirect('home')

    # Get all products
    products = Product.objects.all().select_related('farmer__user', 'category')

    # Apply filters
    category = request.GET.get('category')
    sort = request.GET.get('sort', 'price')  # Default sort by price
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if category:
        products = products.filter(category_id=category)
    
    if min_price:
        products = products.filter(price__gte=min_price)
    
    if max_price:
        products = products.filter(price__lte=max_price)
    
    products = products.order_by(sort)

    # Get cart items for the current user
    cart_items = []
    cart_total = 0
    if request.user.is_authenticated:
        cart_items = OrderItem.objects.filter(
            order__customer=request.user,
            order__order_status='Cart'
        ).select_related('product')
        cart_total = sum(item.product.price * item.quantity for item in cart_items)

    context = {
        'products': products,
        'categories': Category.objects.all(),
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    return render(request, 'customer/shop_products.html', context)

@login_required
def add_to_cart(request, product_id):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can add items to cart.')
        return redirect('shop_products')

    if request.method != 'POST':
        return redirect('shop_products')

    try:
        product = Product.objects.get(product_id=product_id)
        quantity = int(request.POST.get('quantity', 1))

        if quantity <= 0:
            messages.error(request, 'Quantity must be greater than zero.')
            return redirect('shop_products')

        if quantity > product.stock:
            messages.error(request, 'Not enough stock available.')
            return redirect('shop_products')

        # Get or create cart (order with status 'Cart')
        cart, created = Order.objects.get_or_create(
            customer=request.user,
            order_status='Cart',
            defaults={'total_price': 0}
        )

        # Check if product already in cart
        cart_item, created = OrderItem.objects.get_or_create(
            order=cart,
            product=product,
            defaults={'quantity': quantity, 'price': product.price}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        # Update cart total
        cart.total_price = sum(item.price * item.quantity for item in cart.orderitem_set.all())
        cart.save()

        messages.success(request, f'{product.product_name} added to cart.')
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
    except Exception as e:
        messages.error(request, f'Error adding to cart: {str(e)}')

    return redirect('shop_products')

@login_required
def remove_from_cart(request, item_id):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can modify cart.')
        return redirect('shop_products')

    if request.method != 'POST':
        return redirect('shop_products')

    try:
        cart_item = OrderItem.objects.get(
            id=item_id,
            order__customer=request.user,
            order__order_status='Cart'
        )
        cart = cart_item.order
        cart_item.delete()

        # Update cart total
        cart.total_price = sum(item.price * item.quantity for item in cart.orderitem_set.all())
        cart.save()

        messages.success(request, 'Item removed from cart.')
    except OrderItem.DoesNotExist:
        messages.error(request, 'Item not found in cart.')

    return redirect('shop_products')

@login_required
def checkout(request):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can checkout.')
        return redirect('shop_products')

    try:
        # Get customer profile
        customer_profile = CustomerProfile.objects.get(user=request.user)
        
        # Get cart and items
        cart = Order.objects.get(customer=request.user, order_status='Cart')
        cart_items = cart.orderitem_set.all().select_related('product', 'product__farmer', 'product__farmer__user')

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('shop_products')

        if request.method == 'POST':
            # Validate address
            if not customer_profile.address:
                messages.error(request, 'Please add your delivery address before checkout.')
                return redirect('edit_customer_profile')

            # Check stock availability
            for item in cart_items:
                if item.quantity > item.product.stock:
                    messages.error(request, f'Sorry, {item.product.product_name} is out of stock.')
                    return redirect('checkout')

            # Process the order
            payment_method = request.POST.get('payment_method', 'COD')
            cart.order_status = 'Pending'
            cart.placed_at = timezone.now()
            cart.save()

            # Create a new payment record
            Payment.objects.create(
                order=cart,
                payment_method=payment_method,
                payment_status='Pending'
            )

            # Update product stock
            for item in cart_items:
                product = item.product
                product.stock -= item.quantity
                product.save()

            messages.success(request, 'Order placed successfully! We will contact you for delivery details.')
            return redirect('customer_dashboard')

        context = {
            'cart': cart,
            'cart_items': cart_items,
            'customer_profile': customer_profile,
        }
        return render(request, 'customer/checkout.html', context)

    except CustomerProfile.DoesNotExist:
        messages.error(request, 'Please complete your profile before checkout.')
        return redirect('edit_customer_profile')
    except Order.DoesNotExist:
        messages.error(request, 'No active cart found.')
        return redirect('shop_products')

@login_required
def customer_profile(request):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can view this profile.')
        return redirect('home')
    
    try:
        customer_profile = CustomerProfile.objects.get(user=request.user)
    except CustomerProfile.DoesNotExist:
        customer_profile = CustomerProfile.objects.create(user=request.user)
    
    # Get order statistics
    orders = Order.objects.filter(customer=request.user).exclude(order_status='Cart')
    total_orders = orders.count()
    total_spent = orders.aggregate(total=Sum('total_price'))['total'] or 0
    recent_orders = orders.order_by('-placed_at')[:5]
    
    # Get review statistics
    total_reviews = Review.objects.filter(customer=request.user).count()
    
    context = {
        'customer_profile': customer_profile,
        'total_orders': total_orders,
        'total_reviews': total_reviews,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'customer/profile.html', context)

@login_required
def customer_orders(request):
    if request.user.role != 'Customer':
        messages.error(request, 'Only customers can view their orders.')
        return redirect('home')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', '-placed_at')
    
    # Get all orders except cart
    orders = Order.objects.filter(
        customer=request.user
    ).exclude(
        order_status='Cart'
    )
    
    # Apply status filter
    if status:
        orders = orders.filter(order_status=status)
    
    # Apply sorting
    orders = orders.order_by(sort).select_related(
        'payment'
    ).prefetch_related(
        'orderitem_set__product__farmer__user'
    )

    context = {
        'orders': orders,
        'current_status': status,
        'current_sort': sort,
    }
    return render(request, 'customer/orders.html', context)

@login_required
def farmer_orders(request):
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can view their orders.')
        return redirect('home')
    
    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
        
        # Get filter parameters
        status = request.GET.get('status', '')
        sort = request.GET.get('sort', '-placed_at')
        
        # Get all orders containing farmer's products
        orders = Order.objects.filter(
            orderitem__product__farmer=farmer_profile
        ).exclude(
            order_status='Cart'
        ).distinct()
        
        # Apply status filter
        if status:
            orders = orders.filter(order_status=status)
        
        # Apply sorting
        orders = orders.order_by(sort).select_related(
            'customer', 'payment'
        ).prefetch_related(
            'orderitem_set__product'
        )

        # Calculate total earnings
        total_earnings = sum(
            item.price * item.quantity
            for order in orders
            for item in order.orderitem_set.filter(product__farmer=farmer_profile)
        )

        context = {
            'orders': orders,
            'current_status': status,
            'current_sort': sort,
            'total_earnings': total_earnings,
        }
        return render(request, 'farmer/orders.html', context)
        
    except FarmerProfile.DoesNotExist:
        messages.error(request, 'Please complete your farmer profile first.')
        return redirect('farmer_dashboard')

@login_required
def update_order_status(request, order_id):
    if request.user.role != 'Farmer':
        messages.error(request, 'Only farmers can update order status.')
        return redirect('home')
    
    if request.method != 'POST':
        return redirect('farmer_orders')
    
    try:
        farmer_profile = FarmerProfile.objects.get(user=request.user)
        order = Order.objects.filter(
            order_id=order_id,
            orderitem__product__farmer=farmer_profile
        ).distinct().first()
        
        if not order:
            messages.error(request, 'Order not found or you do not have permission to update it.')
            return redirect('farmer_orders')
        
        new_status = request.POST.get('status')
        if new_status in ['Shipped', 'Delivered']:
            order.order_status = new_status
            order.save()
            
            if new_status == 'Delivered':
                # Update payment status if COD
                if order.payment.payment_method == 'COD':
                    order.payment.payment_status = 'Success'
                    order.payment.save()
            
            messages.success(request, f'Order #{order_id} marked as {new_status}.')
        else:
            messages.error(request, 'Invalid order status.')
            
    except FarmerProfile.DoesNotExist:
        messages.error(request, 'Farmer profile not found.')
    
    return redirect('farmer_orders')


