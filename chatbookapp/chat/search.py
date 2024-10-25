from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv 
from openai import OpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from typing import List, Dict
import json
from langchain_community.chat_models import ChatOpenAI
from langchain_postgres.vectorstores import PGVector
from langchain_core.messages import AIMessage, HumanMessage
import base64
import tiktoken
from typing import Tuple
from nltk.corpus import stopwords
from django.core.cache import cache
from collections import defaultdict
from django.conf import settings
final_chunk=""



def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
class BookAssistant:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.session_timeout = 3600 

        # Load API keys from environment variables
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.OPENAI_API_KEY)

        # Set environment variables for  OpenAI
        os.environ["OPENAI_API_KEY"] = self.OPENAI_API_KEY

        # current_language = "English"
        # self.chat_history = []
        self.current_book_name = None
        # current_book_name = None 
        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.OPENAI_API_KEY)
        # self.connection_string = "postgresql+psycopg2://linuxbean:linux123@127.0.0.1:5432/harry"
        self.connection_string = settings.CONNECTION_STRING
        # Initialize vector store
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name='exclusive_book',
            connection=self.connection_string,
            use_jsonb=True,
        )

        # Define function for OpenAI function calling
        self.function = [
            {
                "type": "function",
                "name": "fetch_page_number",
                "description": "This function fetches relevant content from a vector database to answer user's questions. The content will be fetched based on specific page number or similarity search. Pass arguments as per user's query, but either page number or query must be passed. If user has asked about summary of book and author about the book, pass page number 0 in the page argument.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "number",
                            "description": "If user's question is about any specific page number, pass the page number here. If user has asked about the  summary of book and author about the book, pass page number 0.",
                        },
                        "query": {
                            "type": "string",
                            "description": "Rephrased user's question or query that can better find similar content from vector database to answer user's question.",
                        },
                    },
                    "required": [],
                }
            },
        ]
        
        # Tokenizer for GPT models (use gpt-4 or other as per your need)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")
        
        self.stop_words = set(stopwords.words('english'))
    def remove_stopwords(self, text: str) -> str:
        """Remove stopwords from the input text."""
        return ' '.join(word for word in text.split() if word.lower() not in self.stop_words)
    
    def count_tokens(self, text: str) -> int:
        """Counts tokens in the given text using the appropriate tokenizer."""
        return len(self.tokenizer.encode(text))

    def count_message_tokens(self, messages: List[Dict]) -> int:
        """Counts tokens in a list of messages."""
        total_tokens = 0
        for message in messages:
            message_text = message.get("content", "")
            total_tokens += self.count_tokens(message_text)
        return total_tokens
    
    # def get_user_session(self, user_id, session_id):
    #     cache_key = f"user_{user_id}_{session_id}"
    #     session = cache.get(cache_key)
    #     if not session:
    #         session = {
    #             'current_book_name': None,
    #             'current_language': "English",
    #             'chat_history': []
    #         }
    #         cache.set(cache_key, session, self.session_timeout)
    #     return session

    # def set_current_book(self, user_id, session_id, book_name):
    #     session = self.get_user_session(user_id, session_id)
    #     session['current_book_name'] = book_name
    #     self._update_session(user_id, session_id, session)

    # def set_current_language(self, user_id, session_id, language="English"):
    #     session = self.get_user_session(user_id, session_id)
    #     session['current_language'] = language
    #     self._update_session(user_id, session_id, session)
    
    def find_nearest_answer_key(self,book_name, given_page):
        """
        Find the nearest answer key pages within the next 15 pages from the given page.
        
        Args:
        given_page (str or int): The starting page number to search from.
        
        Returns:
        list: A list of page numbers containing answer keys, or an empty list if none found.
        """
        # session = self.get_user_session(user_id, session_id)
        # current_book_name = session['current_book_name']
        current_book_name = book_name
        
        given_page = int(given_page)
        

        answer_key_pages = []
        search_range = range(given_page, given_page + 10)  # Search up to 15 pages ahead
        
        for page in search_range:
            filter_query = {
                "$and": [
                    {"filename": current_book_name},
                    {"page": page},
                ]
            }
            
            page_context = self.vector_store.similarity_search("", k=3, filter=filter_query)
            # print(f"&&&&&&&&&&&&&&{page}&&&&&&&&&&{page_context}")
            if page_context and page_context[0].metadata.get('label') == 'answerkeys':
                # print(f"&&&&&&&&&&&&&&{page_context}&&&&&&&&&&")
                answer_key_pages.append(page_context)
            elif answer_key_pages:
                # If we've found answer keys and then hit a non-answer key page, stop searching
                break
        # print(f"&&&&&&&&&&&&&&{answer_key_pages}&&&&&&&&&&")
        return answer_key_pages
            
    def fetch_page_number(self,query="", page=None,book_name=None):
        """
        Fetch relevant content from the vector database based on query or page number.
        """
        if book_name is None:
            book_name = self.current_book_name
        # session = self.get_user_session(user_id, session_id)
        # current_book_name = session['current_book_name']
        current_book_name = self.current_book_name
        # bk="Principles and Practice of Clinical Research",
        print("BOOK NAME**",current_book_name)
        if current_book_name is None:
            raise ValueError("No book selected. Please set a book first.")
        # print("BK1************",current_book_name)
        # print("PAGE NO ######",page)
        if page:
            
            filter_query = {
                "$and": [
                    {"filename":current_book_name},
                    { "page": { "$in": [ int(page), int(page)+1] }},#int(page)-1,
                ]
            }
        elif page == 0:
            filter_query = {
                "$and": [
                    {"filename":current_book_name},
                    { "page": { "$in": [int(page)] }},
                ]
            }
        else:        
            filter_query = {
                "$or": [
                    {"filename":current_book_name},
                ]
            }
        document_context = self.vector_store.similarity_search(query, k=2, filter=filter_query)
        print("THIS IS  FILTER",filter_query)
        
        # Check if the page is labeled as "objective" or "exercise"
        if page and any(doc.metadata.get('label') in ['objectives', 'exercises'] for doc in document_context):
            # print("HELLO@@@@@label='objectives', 'exercises'@@@@@@@@@@@@@@@")
            answer_key_pages = self.find_nearest_answer_key(book_name,page)
            # print("HELLO@@@@@@@@@@@@@@@@@@@@QQQQQQQQQQQQ*******answer_key_pages",answer_key_pages)
            if answer_key_pages:
                for answer_context in answer_key_pages:
                    # print("HELLO@@@@@@@@@@@@@@@@@@@@QQQQQQQQQQQQ*******answer_key_pages",answer_context)
                    document_context.extend(answer_context)
        # print("\n\n\n**********THIS IS CONTEXT*********\n\n\n\n",document_context)
        print("\n********** THIS IS CONTEXT METADATA *********\n")
        for doc in document_context:
            metadata = doc.metadata
            print(f"Page: {metadata.get('page')}, Filename: {metadata.get('filename')}, Label: {metadata.get('label')}")
        return document_context


   
    
    def extract_query(self,user_input,chat_history):
        """
        Extract query parameters from user input using OpenAI function calling.
        """
        # session = self.get_user_session(user_id, session_id)
        # chat_history = session['chat_history']
        # chat_history = self.chat_history
        # print("CHAT history>>>>",chat_history)
        question_prompt = f"""
                Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.

                Chat History:
                {chat_history}
                Follow Up Input: {user_input}
                Standalone question:"""
        ststem_prompt1="""
            You are working as a middleware between user and a chatbot that answers questions related to a book. Your task is to provide that chatbot with enough relevant content from vector database about the book to answer user's query. You will be provided with user's current and previous questions and you will call fetch_content function to get enough context. 
            
            Important: 
            1. If user is asking about any specific page number, then pass page argument. 
            2. If user didn't define any specific page and just asked something about content, then just rephrase the user's question based on previous question to make a complete question and then pass it in the query argument. 
            3. Either one argument must be passed.
        
        """
        messages = [
            {"role": "system", "content": ststem_prompt1 },
            {"role": "user", "content": question_prompt}
        ]  
        # Count tokens for the prompt
        token_count = self.count_message_tokens(messages)
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=self.function,
            # function_call="auto"
            function_call={"name":"fetch_page_number"},
            temperature=0.1
        )    
        return response.choices[0].message ,token_count

    def extract_data(self, context, query,book_name,language,image_path=None,page_no=None,):
        """
        Generate response based on context and query using OpenAI.
        """
        # session = self.get_user_session(user_id, session_id)
        # current_language = session['current_language']
        # current_book_name = session['current_book_name']
        
        assistant_prompt = f"The current discussion is focused on the book titled '{book_name}'. Please frame your responses and questions in the context of this specific book."
        
        if image_path:
            
            system_prompt=f"""
            
                     You are an AI assistant capable of analyzing images and understanding context. Your task is to examine the provided image and any accompanying context, then respond based on whether a specific query is given or not.

                *If a query is provided:*
                1. Carefully analyze the image and consider any contextual information given.
                2. Formulate a response that directly answers the query, using relevant details from the image and context.
                3. If the query cannot be fully answered based on the available information, state this clearly and provide the best possible answer with the information at hand.

                *If no query is provided:*
                1. Analyze the image thoroughly.
                2. Provide a brief, clear explanation of what you observe in the image. Focus on the main elements, subjects, or actions depicted.
                3. Keep your explanation concise, typically within 2-3 sentences, unless the image is particularly complex.

                *In all cases:*
                - Be objective and accurate in your observations.
                - If you're unsure about any aspect of the image, state your uncertainty.
                - Do not make assumptions beyond what is clearly visible or provided in the context.
                - If text is present in the image, mention its content if relevant.
                - Respect privacy by not attempting to identify specific individuals.
                **Remember:**
                - Always respond in the language specified by the user. Languages: {language}. Regardless of the language the user asks in, always provide responses in the specified language.
                Please process the image and respond accordingly.
            """
            
            # base64_image = encode_image(image_path)
            base64_image = image_path
            # print("\n\nBASE64\n\n",base64_image)
            
            user_prompt = f"""
                    Here is the user's question:
                    {query}
                    ======================
                    And here is the relevant book content to answer user's query:
                    {context}
                    ======================
                   
            """
            messages = [
            {"role": "assistant", "content": assistant_prompt},
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": base64_image,"detail": "low"}},
                # {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
            ]
        # response = self.client.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=messages,
        #     stream=True,
        #     temperature=0.1,
        #     max_tokens=400
        # )
        
        # for chunk in response:
        #     if chunk.choices[0].delta.content is not None:
        #         yield chunk.choices[0].delta.content
                    

        else:
            
            system_prompt = f"""
                You are an AI assistant tasked with describing book content. Your responsibilities include:
                1. Providing explanations about the book's content
                2. Answering user questions related to the book
                3. Clarifying specific parts or pages of the book

                *Guidelines:*
                - Use only the provided relevant content to answer questions
                - Focus exclusively on the selected book
                - Provide clear explanations for user queries
                - For multiple-choice questions, use only provided answer keys
                - For mathematics or physics or chemistry questions, if the provided context doesn't contain enough information, use your general knowledge base to answer
                - Make sure your answer is between 100 and 300 words.

                *Restrictions:*
                - Only answer questions about the selected book
                - If the context lacks information to answer multiple questions, respectfully decline to answer those specific questions
                - Do not answer multiple-choice questions without a provided answer key
                - Do not use your own knowledge or reasoning for multiple-choice questions
                - For non-math/physics/chemistry questions, if the book content is insufficient, politely decline to answer

                *Response Protocol*:
                - Offer clear, concise explanations
                - Reference specific pages when applicable
                - If unable to answer, politely explain why
                **Remember:**
                - Always respond in the language specified by the user. Languages: {language}. Regardless of the language the user asks in, always provide responses in the specified language.
                You will now receive the user's query and the relevant book content needed to formulate your response.
                """
            
            user_prompt = f"""
            Here is the user's question:
            {query}
            ======================
            And here is the relevant book content to answer user's query:
            {context}
            """
            
            if not isinstance(context, str):
                context = json.dumps(context)
        
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": user_prompt},
            ]
        
            
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            temperature=0.1,
            max_tokens=450
        )
        
        
        
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
                
    def run_function(self,response) :
        """
        Execute the function call based on the response from OpenAI.
        """
        if response.function_call is None:
            # No function call was specified, return an appropriate message or handle this case
            return "No function call was specified in the response."
        
        function_name = response.function_call.name
        function_args = json.loads(response.function_call.arguments)
        
        # Add user_id and session_id to function_args if missing
        # function_args['user_id'] = user_id
        # function_args['session_id'] = session_id
        
        print("ARG************", function_args)
        # Include book_name in the function arguments
        if function_name == 'fetch_page_number':
            function_args['book_name'] = self.current_book_name
        result = getattr(self, function_name)(**function_args)
        return result
    
    

    def greet_user(self, user_input,book_name,language):
        # Check if the user input is in the valid greetings list
        assistant_prompt = f"The current discussion is focused on the book titled book '{book_name}'. Please frame your responses and questions in the context of this specific book."
        system_prompt = f"""
            You are a knowledgeable and patient teacher specializing in the book "{book_name}". Your role is to help and guide users by answering any questions they may have about this book.           

            - Always respond in language {language}. 
            """

        messages = [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": user_input},
            ]
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            temperature=0.1,
            max_tokens=400
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

       

    def query(self, user_input, image_path, page_no,book_name,language,chat_history):
        # session = self.get_user_session(user_id, session_id)
        # current_book_name = session['current_book_name']
        # chat_history = session['chat_history']
        # # page_no=int(page_no)
        # global final_chunk
        # if len(chat_history)>2:
        #     del chat_history[0:2]
        
        # Keep track of total tokens used
        self.current_book_name = book_name
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        # input_Image_tokens=0
        # Count tokens for the user input
        
        
        # chat_history.append(user_input)
        # chat_history.append(HumanMessage(content= user_input))
        
        ai_response=""
        valid_greetings = ["Hello", "Hi", "Greetings", "Hey", "Good morning", "Good afternoon", "Good evening", "Happy Spring", "Happy",'Good',"helo",'hy',"hyy"]
        if any(greeting.lower() in user_input.lower() for greeting in valid_greetings):
            for chunk in self.greet_user(user_input,book_name,language):
                    print(chunk, end="", flush=True)  # Print the chunk as it arrives
                    ai_response += chunk
                    yield chunk  #
            ai_response_tokens = self.count_tokens(ai_response)
            output_tokens += ai_response_tokens
            print(f"\n\nTotal tokens used: {output_tokens}\n\n")
        else:
        
        # Check if the user input is a greeting
        # greeting_response = self.greet_user(user_input,book_name)
        # if greeting_response:
        #     yield greeting_response
        #     return
        
            if book_name is None:
                yield "No book selected. Please select a book first."
            # if current_book_name is None:
            #     yield "No book selected. Please select a book first."
            # chat_history.append(HumanMessage(content= user_input))
            if not image_path :
                response,prompt_tokens = self.extract_query(user_input,chat_history)
                
            
                # Add prompt tokens to total
                total_tokens += prompt_tokens
                # print("INFO RES**************",response)
                collected_data=[]
                if response.function_call:
                    content = self.run_function(response)
                    
                    page_contents = [doc.page_content for doc in content]
                    page_contents = [self.remove_stopwords(page) for page in page_contents]
                    page_contents_tokens = sum(self.count_tokens(page) for page in page_contents)
                    input_tokens += page_contents_tokens
                    
                    for chunk in self.extract_data(context=page_contents, query=user_input, image_path=image_path, page_no=page_no, book_name=self.current_book_name, language=language):
                        print(chunk, end="", flush=True)  # Print the chunk as it arrives
                        ai_response += chunk
                        yield chunk  #
                    ai_response_tokens = self.count_tokens(ai_response)
                    output_tokens += ai_response_tokens
                else:
                    yield response.content
                    ai_response_tokens = self.count_tokens(response.content)
                    total_tokens += ai_response_tokens
            
            else:
            
                context=self.fetch_page_number(query=user_input,page=page_no)
                page_contents = [doc.page_content for doc in context]
                page_contents = [self.remove_stopwords(page) for page in page_contents]
                # Token count for `page_contents`
                page_contents_tokens = sum(self.count_tokens(page) for page in page_contents)
                input_tokens += page_contents_tokens
                
                for chunk in self.extract_data(context=page_contents, query=user_input, image_path=image_path, page_no=page_no, book_name=self.current_book_name, language=language):
                    print(chunk, end="", flush=True)  # Print the chunk as it arrives
                    ai_response += chunk
                    yield chunk  #
                ai_response_tokens = self.count_tokens(ai_response)
                output_tokens += ai_response_tokens
                        
            # chat_history.append(AIMessage(content= ai_response))
            # print("\n\n*********THIS IS CHAT HISTORY******\n",chat_history)
            print(f"\n\nTotal tokens used: {input_tokens+output_tokens}\nInput token: {input_tokens}\nOutput token: {output_tokens}\n\n")
        # session['chat_history'] = chat_history
        # self._update_session(user_id, session_id, session)

    # def _update_session(self, user_id, session_id, session):
    #     cache_key = f"user_{user_id}_{session_id}"
    #     cache.set(cache_key, session, self.session_timeout)
        
        
# Example usage
# if __name__ == "__main__":
#     assistant = BookAssistant()
#     user_input = "What is a computer network?"
#     for chunk in assistant.query(user_input):
#         print(chunk, end="")


