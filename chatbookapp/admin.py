
# Register your models here.
from django.contrib import admin
from .models import *
from django.utils.html import format_html

from django.contrib import admin
from django.utils import timezone
from .models import Subscription
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _ 
from django.utils.html import format_html


# Custom admin classes

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('book_name', 'id','author_name', 'selling_price', 'book_genre','image_preview', 'pdf_preview','created_at')
    list_filter = (
        ('selling_price', admin.EmptyFieldListFilter),
        'book_genre', 
        'author_name',
        'created_at',
        'updated_at',
    )
    search_fields = ('book_name', 'uuid')
    readonly_fields = ('uuid', 'image_preview', 'pdf_preview','created_at')#'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('book_name', 'uuid', 'selling_price','book_genre','author_name')
        }),
        ('Files', {
            'fields': ('image', 'image_preview', 'pdf', 'pdf_preview'),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="65" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'

    def pdf_preview(self, obj):
        if obj.pdf:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.pdf.url)
        return "No PDF"
    pdf_preview.short_description = 'PDF Preview'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related()  
        return queryset

    actions = ['clear_selling_price']

    def clear_selling_price(self, request, queryset):
        updated = queryset.update(selling_price=None)
        self.message_user(request, f'Selling price cleared for {updated} books.')
    clear_selling_price.short_description = "Clear selling price for selected books"

    # Custom price range filter
    class PriceRangeFilter(admin.SimpleListFilter):
        title = 'Price Range'
        parameter_name = 'price_range'

        def lookups(self, request, model_admin):
            return (
                ('0-10', '0 - 10'),
                ('10-50', '10 - 50'),
                ('50-100', '50 - 100'),
                ('100+', '100+'),
            )

        def queryset(self, request, queryset):
            if self.value() == '0-10':
                return queryset.filter(selling_price__gte=0, selling_price__lte=10)
            if self.value() == '10-50':
                return queryset.filter(selling_price__gt=10, selling_price__lte=50)
            if self.value() == '50-100':
                return queryset.filter(selling_price__gt=50, selling_price__lte=100)
            if self.value() == '100+':
                return queryset.filter(selling_price__gt=100)

    list_filter += (PriceRangeFilter,)



class OTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp_code', 'created_at', 'expires_at')
    search_fields = ('email',)
    list_filter = ('created_at',)

class SigninWithGoogleAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'last_login', 'authid')
    search_fields = ('name', 'email')
    list_filter = (
        ('last_login', admin.DateFieldListFilter),  
    )

admin.site.register(SigninWithGoogle, SigninWithGoogleAdmin)


admin.site.register(OTP, OTPAdmin)
admin.site.register(ChatMessage)


    
    
    

@admin.register(Profile)
class ProfileAdmin(UserAdmin):
    list_display = ('username', 'email',  'is_verified', 'is_active', 'avatar_preview', 'date_joined', "last_login")
    list_filter = (
        'is_verified',
        'is_staff',
        'is_active',
        'is_superuser',
        'groups',
        ('date_joined', admin.DateFieldListFilter),
        ('last_login', admin.DateFieldListFilter),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email', 'user_id')
    ordering = ('-date_joined',)
    readonly_fields = ('user_id', 'date_joined', 'last_login', 'created_at', 'avatar_preview')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'avatar', 'avatar_preview')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at')}),
        (_('Additional info'), {'fields': ('user_id',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:50%;" />', obj.avatar.url)
        return "No Image"
    avatar_preview.short_description = 'Avatar Preview'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related()  # Add select_related if there are any ForeignKey fields
        return queryset

    actions = ['verify_users', 'unverify_users']

    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} users were successfully verified.')
    verify_users.short_description = "Mark selected users as verified"

    def unverify_users(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} users were successfully unverified.')
    unverify_users.short_description = "Mark selected users as unverified"




@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'book', 'plan_type','payment_status', 'duration', 'display_price','questions_asked_this_month',  'start_date', 'end_date', 'is_active')#'questions_asked_today'
    list_filter = ('plan_type', 'duration','payment_status', 'book')
    search_fields = ('profile__username', 'book__book_name', 'profile__email')
    date_hierarchy = 'start_date'
    readonly_fields = ('start_date', 'display_price')

    def is_active(self, obj):
        return not obj.is_expired()
    is_active.boolean = True
    is_active.short_description = 'Active'

    def display_price(self, obj):
        return f"₹{obj.price:.2f}"
    display_price.short_description = 'Price'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('profile', 'book')
        return queryset

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        try:
            search_term_as_date = timezone.datetime.strptime(search_term, "%Y-%m-%d").date()
        except ValueError:
            pass
        else:
            queryset |= self.model.objects.filter(start_date=search_term_as_date)
            queryset |= self.model.objects.filter(end_date=search_term_as_date)
        return queryset, use_distinct

    actions = ['mark_as_expired', 'reset_questions_asked_today']

    def mark_as_expired(self, request, queryset):
        queryset.update(end_date=timezone.now().date() - timezone.timedelta(days=1))
    mark_as_expired.short_description = "Mark selected subscriptions as expired"

    def reset_questions_asked_today(self, request, queryset):
        queryset.update(questions_asked_today=0, last_question_date=timezone.now().date())
    reset_questions_asked_today.short_description = "Reset questions asked today for selected subscriptions"

    fieldsets = (
        (None, {
            'fields': ('profile', 'book', 'plan_type', 'duration', 'display_price')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Usage', {
            'fields': ('questions_asked_this_month', 'last_question_date')
            # 'fields': ('questions_asked_today','questions_asked_this_month', 'last_question_date')
        }),
    )
    

