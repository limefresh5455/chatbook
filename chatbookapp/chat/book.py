from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from chatbookapp.models import Book, Subscription, Profile
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


########################
class BuyBookAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        required_fields = ['bookId', 'plan_type', 'duration', 'price', 'merchantTransactionId', 'paymentStatus']
        missing_fields = [field for field in required_fields if field not in request.data]
        
        if missing_fields:
            return Response({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        book_id = request.data.get('bookId')
        plan_type = request.data.get('plan_type')
        duration = request.data.get('duration')
        price = request.data.get('price')
        merchant_transaction_id = request.data.get('merchantTransactionId')
        payment_status = request.data.get('paymentStatus')

        if payment_status != 'SUCCESS':
            return Response({"message": "Payment was not successful. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate book
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"error": f"No Book found with id {book_id}"}, status=status.HTTP_404_NOT_FOUND)

        # Validate plan_type and duration
        if plan_type not in dict(Subscription.PLAN_TYPES):
            return Response({"error": "Invalid plan_type"}, status=status.HTTP_400_BAD_REQUEST)
        
        if duration not in dict(Subscription.DURATION_TYPES):
            return Response({"error": "Invalid duration"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate user
        try:
            profile = Profile.objects.get(id=request.user.id)
        except Profile.DoesNotExist:
            return Response({"error": f"No Profile found for the current user"}, status=status.HTTP_404_NOT_FOUND)

        # Calculate end date based on duration
        start_date = timezone.now().date()
        if duration == 'MONTHLY':
            end_date = start_date + timedelta(days=30)
        else:  # YEARLY
            end_date = start_date + timedelta(days=365)

        
        # Create or update user subscription
        subscription, created = Subscription.objects.update_or_create(
            profile=profile,
            book=book,
            defaults={
                'plan_type': plan_type,
                'duration': duration,
                'start_date': start_date,
                'end_date': end_date,
                'price': price,
                'merchant_transaction_id': merchant_transaction_id,
                'payment_status': payment_status,
                'questions_asked_this_month': 0
            }
        )

        return Response({
            "message": "Book purchased successfully",
            "bookId": book_id,
            "book_name":book.book_name,
            "author_name":book.author_name,
            "book_genre":book.book_genre,
            # "subscription_id": subscription.id,
            "plan_type": subscription.get_plan_type_display(),
            "duration": subscription.get_duration_display(),
            "price": price,
            "merchant_transaction_id": subscription.merchant_transaction_id,
            "payment_status": subscription.payment_status,
            "start_date": start_date,
            "end_date": end_date
        }, status=status.HTTP_201_CREATED)
        
###################



###########################

class BookDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({"error": f"No Book found with id {book_id}"}, status=status.HTTP_404_NOT_FOUND)

        # Get all possible plan types and durations
        plan_types = dict(Subscription.PLAN_TYPES)
        durations = dict(Subscription.DURATION_TYPES)

        # Calculate prices for all plan types and durations
        plans = []
        for plan_type in plan_types:
            for duration in durations:
                price = self.calculate_price(book.selling_price, plan_type, duration)
                # questions_per_day = self.calculate_questions_per_day(plan_type)
                questions_per_month = self.calculate_questions_per_month(plan_type,duration)
                plans.append({
                    "plan_type": plan_types[plan_type],
                    "duration": durations[duration],
                    "price": str(price),
                    # "questions_per_day": questions_per_day,
                    "questions_per_month": questions_per_month
                })

        book_data = {
            "id": book.id,
            "book_name": book.book_name,
            "selling_price": str(book.selling_price),
            "plans": plans
        }

        return Response(book_data, status=status.HTTP_200_OK)

  
    
    
    def calculate_price(self, selling_price, plan_type, duration):
        if plan_type == 'BASIC':
            return 0
        elif plan_type == 'LEARNER':
            if duration == 'MONTHLY':
                return selling_price
            else:  # YEARLY
                return selling_price * 10
        else:  # PRO
            if duration == 'MONTHLY':
                return selling_price * 3
            else:  # YEARLY
                return selling_price * 10 * 3

    # def calculate_questions_per_day(self, plan_type):
    #     if plan_type == 'BASIC':
    #         return 5
    #     elif plan_type == 'LEARNER':
    #         return 100
    #     else:  # PRO
    #         return "Unlimited"
        
    def calculate_questions_per_month(self, plan_type,duration):
        if plan_type == 'BASIC':
            return 10
        elif plan_type == 'LEARNER':
            if duration == 'MONTHLY':
                return 300
            else:  # YEARLY
                return 300 * 12
            # return 300
        else:  # PRO
            if duration == 'MONTHLY':
                return 1000
            else:  # YEARLY
                return 1000 * 12
            # return 1000 #"Unlimited"
        

#############################


# class UpgradePlanAPIView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]
#     def post(self, request):
#         required_fields = ['subscription_id', 'new_plan_type', 'new_duration']
#         missing_fields = [field for field in required_fields if field not in request.data]
        
#         if missing_fields:
#             return Response({
#                 "error": f"Missing required fields: {', '.join(missing_fields)}"
#             }, status=status.HTTP_400_BAD_REQUEST)
            
#         subscription_id = request.data.get('subscription_id')
#         new_plan_type = request.data.get('new_plan_type')
#         new_duration = request.data.get('new_duration')

#         # Validate subscription
#         subscription = get_object_or_404(Subscription, id=subscription_id)
        
#         # if subscription.is_expired():
#         #     return Response({
#         #         "error": "Your subscription has expired. Please renew your subscription.",
#         #         "subscription_id": subscription.id,
#         #         "book_id": subscription.book.id
#         #     }, status=status.HTTP_400_BAD_REQUEST)   

#         # Validate new plan type
#         if new_plan_type not in dict(Subscription.PLAN_TYPES):
#             return Response({"error": "Invalid new_plan_type"}, status=status.HTTP_400_BAD_REQUEST)

#         # Validate new duration
#         if new_duration not in dict(Subscription.DURATION_TYPES):
#             return Response({"error": "Invalid new_duration"}, status=status.HTTP_400_BAD_REQUEST)

#         # Update subscription with new plan
#         subscription.plan_type = new_plan_type
#         subscription.duration = new_duration
        
        
#         # Reset questions_asked_this_month according to the new plan
#         if new_plan_type == 'BASIC':
#             subscription.questions_asked_this_month = 20  # Set to 20 for BASIC plan
#         elif new_plan_type == 'LEARNER':
#             subscription.questions_asked_this_month = 200  # Set to 200 for LEARNER plan
#         else:  # PRO plan
#             subscription.questions_asked_this_month = 0  # Unlimited questions for PRO
        
#         subscription.questions_asked_this_month = 0
#         subscription.start_date = timezone.now().date()
#         # Adjust end date if duration changed
#         # Update end_date based on new duration
#         if new_duration == 'MONTHLY':
#             subscription.end_date = subscription.start_date + timedelta(days=30)
#         else:  # YEARLY
#             subscription.end_date = subscription.start_date + timedelta(days=365)
        
#         subscription.save()

#         return Response({
#             "message": "Plan upgraded successfully",
#             "subscription_id": subscription.id,
#             "new_plan": subscription.get_plan_type_display(),
#             "new_duration": subscription.get_duration_display(),
#             "new_price": str(subscription.price),
#             "start_date": subscription.start_date,
#             "end_date": subscription.end_date
#         }, status=status.HTTP_200_OK)


###########################

class SubscriptionStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, subscription_id):
        try:
            profile = Profile.objects.get(id=request.user.id)
            subscription = Subscription.objects.get(id=subscription_id, profile=profile)
        except Subscription.DoesNotExist:
            return Response({"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)

        days_left = (subscription.end_date - timezone.now().date()).days
        # Calculate questions left this month
        if subscription.plan_type == 'EXAMINER':
            questions_left = max(0, 1000 - subscription.questions_asked_this_month)
        elif subscription.plan_type == 'BASIC':
            questions_left = max(0, 200 - subscription.questions_asked_this_month)
        else:  # LEARNER
            questions_left = max(0, 10 - subscription.questions_asked_this_month)



        # questions_left = subscription.questions_per_day - subscription.questions_asked_today

        return Response({
            "subscription_id": subscription.id,
            "book_id": subscription.book.id,
            "plan_type": subscription.get_plan_type_display(),
            "duration": subscription.get_duration_display(),
            "is_expired": subscription.is_expired(),
            "days_left": max(0, days_left),
            "questions_asked_this_month": subscription.questions_asked_this_month,
            # "questions_asked_today": subscription.questions_asked_today,
            # "questions_left_today": max(0, questions_left),
            "questions_asked_this_month": subscription.questions_asked_this_month,
            "questions_left_this_month": questions_left,
            "can_ask_question": subscription.can_ask_question()
        }, status=status.HTTP_200_OK)


#############################

class GetSubscribedBooksAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the profile of the authenticated user
        try:
            profile = Profile.objects.get(id=request.user.id)
        except Profile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all the subscriptions for this user
        subscriptions = Subscription.objects.filter(profile=profile)

        # Prepare the response data
        subscribed_books = []
        for subscription in subscriptions:
            subscribed_books.append({
                "book_id": subscription.book.id,
                "book_name": subscription.book.book_name,
                "author_name": subscription.book.author_name,
                "image": request.build_absolute_uri(subscription.book.image.url),
                "plan_type": subscription.get_plan_type_display(),
                "duration": subscription.get_duration_display(),
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "price": str(subscription.price),
            })

        return Response({
            "message": "Subscribed books retrieved successfully.",
            "subscribed_books": subscribed_books
        }, status=status.HTTP_200_OK)





