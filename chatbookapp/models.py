from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError


class Book(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    book_name = models.CharField(max_length=255)
    author_name = models.CharField(max_length=255,blank=True)
    image = models.ImageField(upload_to='upload/images/')
    pdf = models.FileField(upload_to='upload/pdfs/')
    selling_price = models.FloatField(null=True,blank=True)
    book_genre = models.CharField(max_length=100, blank=True) 
    created_at = models.DateTimeField(default=timezone.now)  # Editable
    updated_at = models.DateTimeField(auto_now=True)  # Automatically updates on save

    def save(self, *args, **kwargs):
        # Set the created_at timestamp only when the object is created
        if not self.pk:
            self.created_at = timezone.now()
        super().save(*args, **kwargs)
    def __str__(self):
        return self.book_name

def validate_image_size(image):
    file_size = image.file.size
    limit_mb = 5
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Max size of file is {limit_mb} MB")

class Profile(AbstractUser):
    id = models.AutoField(primary_key=True)
    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=150, unique=False)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    avatar = models.ImageField(upload_to='upload/avatars/', null=True, blank=True, validators=[validate_image_size])
    
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='profile_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='profile_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    class Meta:
        unique_together = ('email',)





class OTP(models.Model):
 id = models.AutoField(primary_key=True)
 email = models.EmailField()
 otp_code = models.IntegerField()
 created_at = models.DateTimeField(auto_now_add=True)
 expires_at = models.DateTimeField()

 def save(self, *args, **kwargs):
    if not self.pk:
        self.expires_at = timezone.now() + timedelta(minutes=5)
    super().save(*args, **kwargs)

 def __str__(self):
    return f"{self.email} - {self.otp_code}"
 

class SigninWithGoogle(models.Model):
    id = models.AutoField(primary_key=True)
    authid = models.CharField(max_length=255, null=False)
    name = models.CharField(max_length=255, null=False)
    email = models.EmailField(null=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.name
    @classmethod
    def handle_google_signin(cls, authid, name, email):
        # Retrieve or create a Profile
        profile, created = Profile.objects.get_or_create(
            email=email,
            defaults={
                'username': name, 
                'is_verified': True
            }
        )
        
        # If the profile already exists but isn't verified, verify it
        if not created and not profile.is_verified:
            profile.is_verified = True
            profile.save()
        
        # Create or update the SigninWithGoogle entry
        signin_instance, _ = cls.objects.update_or_create(
            authid=authid,
            defaults={
                'name': name,
                'email': email,
                'profile': profile,
                'last_login': timezone.now()
            }
        )
        
        return signin_instance
    
#####################################




class Subscription(models.Model):
    PLAN_TYPES = [
        ('BASIC', 'Basic'),
        ('LEARNER', 'Learner'),
        ('EXAMINER', 'Examiner'),
    ]
    DURATION_TYPES = [
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    PAYMENT_STATUS=[
        ('SUCCESS', 'Success'), 
        ('FAILED', 'Failed'), 
        ('PENDING', 'Pending')
        ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    plan_type = models.CharField(max_length=8, choices=PLAN_TYPES)
    duration = models.CharField(max_length=7, choices=DURATION_TYPES)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    questions_asked_today = models.IntegerField(default=0)
    last_question_date = models.DateField(null=True, blank=True)
    questions_asked_this_month = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    merchant_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS,null=True, blank=True)
    

    def __str__(self):
        return f"{self.profile.username} - {self.book.book_name} - {self.get_plan_type_display()} {self.get_duration_display()}"

    # @property
    # def price(self):
    #     selling_price = self.book.selling_price
    #     if self.plan_type == 'BASIC':
    #         return 0
    #     elif self.plan_type == 'LEARNER':
    #         if self.duration == 'MONTHLY':
    #             return selling_price
    #         else:  # YEARLY
    #             return selling_price * 10
    #     else:  # PRO
    #         if self.duration == 'MONTHLY':
    #             return selling_price * 3
    #         else:  # YEARLY
    #             return selling_price * 10 * 3

    # @property
    # def questions_per_day(self):
    #     if self.plan_type == 'Basic':
    #         return 5
    #     elif self.plan_type == 'LEARNER':
    #         return 100
    #     else:  # PRO
    #         return 0  # Unlimited

    def is_expired(self):
        return self.end_date < timezone.now().date()

    # def reset_daily_questions(self):
    #     today = timezone.now().date()
    #     if self.last_question_date != today:
    #         self.questions_asked_today = 0
    #         self.last_question_date = today
    #         self.save()
            
    def reset_monthly_questions(self):
        today = timezone.now().date()
        if self.last_question_date and self.last_question_date.month != today.month:
            self.questions_asked_this_month = 0
            self.last_question_date = today
            self.save()

    # def can_ask_question(self):
    #     self.reset_daily_questions()
    #     if self.plan_type == 'BASIC':
    #         return self.questions_asked_today < 5
    #     elif self.plan_type == 'Learner':
    #         return self.questions_asked_today < 100
    #     else:  # PRO Examiner
    #         return True
    
    def can_ask_question(self):
        if self.plan_type == 'BASIC':
            return self.questions_asked_this_month <10
        elif self.plan_type == 'LEARNER':
            if self.duration == 'MONTHLY':
                return self.questions_asked_this_month <300
            else:  # YEARLY
                return self.questions_asked_this_month < 300 * 12
            # return 300
        else:  # PRO
            if self.duration == 'MONTHLY':
                return self.questions_asked_this_month <1000
            else:  # YEARLY
                return self.questions_asked_this_month <1000 * 12
            
            # return 1000 #"Unlimited"
        # # self.reset_monthly_questions()
        # if self.plan_type == 'BASIC':
        #     return self.questions_asked_this_month < 10
        # elif self.plan_type == 'LEARNER':
        #     return self.questions_asked_this_month < 300
        # else:  # PRO
        #     return self.questions_asked_this_month < 1000
        #     # return True #1000

    def increment_question_count(self):
        # self.reset_daily_questions()
        # self.questions_asked_today += 1
        self.reset_monthly_questions()
        self.questions_asked_this_month += 1
        self.last_question_date=timezone.now().date()
        self.save()




class ChatMessage(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='chat_messages')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    content = models.TextField()
    is_user_message = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.profile.username} - {self.timestamp}"
