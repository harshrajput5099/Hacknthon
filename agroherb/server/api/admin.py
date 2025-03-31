from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(FarmerProfile)
admin.site.register(CertificationRequest)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Review)
admin.site.register(FAQ)
admin.site.register(ContactForm)
admin.site.register(Blog) 