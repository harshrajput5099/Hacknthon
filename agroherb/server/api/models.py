from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import qrcode
from io import BytesIO
from django.core.files import File
from django.utils import timezone

# User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, full_name, phone_number, password=None, role='Customer'):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, phone_number=phone_number, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, phone_number, password):
        user = self.create_user(email, full_name, phone_number, password, role='Admin')
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

# User Model
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('Farmer', 'Farmer'),
        ('Customer', 'Customer'),
        ('Admin', 'Admin'),
        ('Verifier', 'Verifier'),
    ]
    
    user_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Customer')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number']

    def __str__(self):
        return self.email

# Farmer Profile
class FarmerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    def __str__(self):
        return self.user.full_name

# Certification Request
class CertificationRequest(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    submitted_documents = models.FileField(upload_to='certification_documents/')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending')
    submitted_at = models.DateTimeField(default=timezone.now)
    inspection_date = models.DateField(null=True, blank=True)
    approval_date = models.DateField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Certification Request by {self.farmer.user.full_name}"

# Category Model
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.category_name

# Product Model
class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='products/')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Create detailed QR code content
        qr_content = (
            f"Product Details:\n"
            f"Name: {self.product_name}\n"
            f"Category: {self.category.category_name}\n"
            f"Price: ₹{self.price}\n"
            f"Stock Available: {self.stock} units\n\n"
            f"Farmer Details:\n"
            f"Name: {self.farmer.user.full_name}\n"
            f"Location: {self.farmer.city}, {self.farmer.state}\n"
            f"Contact: {self.farmer.user.phone_number}\n"
            f"Certification Status: {'Certified' if hasattr(self.farmer, 'certification_request') and self.farmer.certification_request.status == 'approved' else 'Pending'}"
        )
        
        # Create QR code instance with styling
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        # Add data
        qr.add_data(qr_content)
        qr.make(fit=True)

        # Create image with custom coloring
        qr_image = qr.make_image(fill_color="darkgreen", back_color="white")
        
        # Save to buffer
        buffer = BytesIO()
        qr_image.save(buffer)
        self.qr_code.save(f'qr_{self.product_id}.png', File(buffer), save=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.product_name

# Order Model
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)
    order_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    placed_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Order {self.order_id} - {self.order_status}"

# Order Items Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.order.order_id} - {self.product.product_name}"

# Payment Model
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Wallet', 'Wallet'),
        ('COD', 'COD'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=50, blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Payment for Order {self.order.order_id}"

# Review Model
class Review(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()

    def __str__(self):
        return f"Review by {self.customer.full_name} - {self.rating} Stars"

# FAQ Model
class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return self.question

# Contact Form Model
class ContactForm(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Resolved', 'Resolved'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')

    def __str__(self):
        return self.name

# Blog Model
class Blog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name}'s Profile"

    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'



