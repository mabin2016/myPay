from rest_framework.response import Response
from rest_framework import status

def api_success_response(data=None, message="Success", status_code=status.HTTP_200_OK, **kwargs):
    """
    Standard success API response.
    Includes a general 'success' flag, a message, and the actual data.
    Additional kwargs can be added to the response dictionary.
    """
    response_data = {
        "success": True,
        "message": message,
        "data": data if data is not None else {} # Ensure data is at least an empty dict if None
    }
    response_data.update(kwargs) # Add any extra keyword arguments to the response
    return Response(response_data, status=status_code)

def api_error_response(message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
    """
    Standard error API response.
    Includes a general 'success' flag (False), an error message, and specific error details.
    Additional kwargs can be added to the response dictionary.
    """
    response_data = {
        "success": False,
        "message": message,
        "errors": errors if errors is not None else {} # Ensure errors is at least an empty dict if None
    }
    response_data.update(kwargs)
    return Response(response_data, status=status_code)

# Example Usage in a DRF View:
# from .responses import api_success_response, api_error_response
#
# class MyView(APIView):
#     def get(self, request, *args, **kwargs):
#         try:
#             data = {"key": "value"}
#             return api_success_response(data=data, message="Data retrieved successfully.")
#         except Exception as e:
#             # Log the exception e
#             return api_error_response(message="Failed to retrieve data.", errors=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#     def post(self, request, *args, **kwargs):
#         serializer = MySerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return api_success_response(data=serializer.data, message="Resource created.", status_code=status.HTTP_201_CREATED)
#         else:
#             return api_error_response(message="Validation failed.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

# Specific success responses for common scenarios (optional)
def api_created_response(data=None, message="Resource created successfully.", **kwargs):
    return api_success_response(data=data, message=message, status_code=status.HTTP_201_CREATED, **kwargs)

def api_no_content_response(message="Operation successful, no content to return.", **kwargs):
    # HTTP 204 No Content should not have a response body.
    # However, our standard format expects one. So we can either:
    # 1. Return HTTP 200 with a message indicating no content.
    # 2. Return HTTP 204 and the client must handle it (no body).
    # For consistency with the api_success_response structure, option 1 might be chosen,
    # or return a 200 OK with a specific message.
    # If strictly adhering to HTTP 204, then: return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"success": True, "message": message}, status=status.HTTP_200_OK, **kwargs)


# Specific error responses (optional)
def api_not_found_response(message="Resource not found.", errors=None, **kwargs):
    return api_error_response(message=message, errors=errors, status_code=status.HTTP_404_NOT_FOUND, **kwargs)

def api_unauthorized_response(message="Authentication credentials were not provided or are invalid.", errors=None, **kwargs):
    return api_error_response(message=message, errors=errors, status_code=status.HTTP_401_UNAUTHORIZED, **kwargs)

def api_forbidden_response(message="You do not have permission to perform this action.", errors=None, **kwargs):
    return api_error_response(message=message, errors=errors, status_code=status.HTTP_403_FORBIDDEN, **kwargs)

def api_validation_error_response(message="Validation failed.", errors=None, **kwargs):
    return api_error_response(message=message, errors=errors, status_code=status.HTTP_400_BAD_REQUEST, **kwargs)
