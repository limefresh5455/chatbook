from django.shortcuts import render
# Create your views here.
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required


from account.vector_search import query
from .search import BookAssistant  


assistant = BookAssistant()

def index(request):
    return render(request, 'chat.html')

@csrf_exempt
def chat(request):
    if request.method == 'GET':
        user_input = request.GET.get('message', '')
        
        def event_stream():
            # Replace this with your actual query function
            for chunk in assistant.query(user_input):  # Simulating streaming response
                yield f"data: {chunk}\n\n"
        
        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    
    # If not a GET request, return an empty response
    return StreamingHttpResponse()


# def chat_view(request):
#     if request.method == 'POST':
#         data = json.loads(request.body)
#         user_message = data.get('message', '')
#         print("USER QUERY",user_message)
#         # Call your chat function here
#         # response = chat_function(user_message)
        
#         response=query(user_message)
#         print("THIS IS RESPONSE",response)
#         return JsonResponse({'response': response})
#     chat_messages = []  # You can load previous messages here if needed
#     return render(request, 'chat.html', {'chat_messages': chat_messages})



###########################################

def login(request):
    return render(request,'login.html')

@login_required
def home(request):
    return render(request,'home.html')


def chat(request):
    user_input = "what is computer network"
    # query(user_input)
    return render(request,"chat.html")


def upload_pdf(request):
    pass

