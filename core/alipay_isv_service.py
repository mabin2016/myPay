import logging
from django.conf import settings
from urllib.parse import urlencode, quote_plus
# from alipay.aop.api.AlipayClientConfig import AlipayClientConfig # Actual: from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
# from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient # Actual: from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
# from alipay.aop.api.domain.AlipayOpenAuthTokenAppModel import AlipayOpenAuthTokenAppModel
# from alipay.aop.api.request.AlipayOpenAuthTokenAppRequest import AlipayOpenAuthTokenAppRequest
# For mocking, we won't use actual SDK classes to avoid dependency on live environment for now.

logger = logging.getLogger(__name__)

# --- Mock SDK Classes and Methods ---
# In a real scenario, these would be actual imports from `alipay-sdk-python`
class MockAlipayClient:
    def __init__(self, alipay_client_config, logger_instance):
        self.app_id = alipay_client_config.app_id
        self.app_private_key = alipay_client_config.app_private_key
        self.alipay_public_key = alipay_client_config.alipay_public_key
        self.sign_type = alipay_client_config.sign_type
        self.sandbox_mode = alipay_client_config.sandbox_mode
        self.logger = logger_instance
        self.logger.info(f"MockAlipayClient initialized for APP_ID: {self.app_id}, Sandbox: {self.sandbox_mode}")

    def execute(self, request, access_token=None, app_auth_token=None):
        self.logger.info(f"MockAlipayClient executing request: {request.__class__.__name__}")
        if isinstance(request, MockAlipayOpenAuthTokenAppRequest):
            # Simulate response for alipay.open.auth.token.app
            if request.biz_content_model.grant_type == 'authorization_code':
                self.logger.info(f"Mocking token exchange for auth_code: {request.biz_content_model.code}")
                return { # This is a simplified dict, actual response is an object or JSON string
                    "alipay_open_auth_token_app_response": {
                        "code": "10000",
                        "msg": "Success",
                        "app_auth_token": f"mock_app_auth_token_for_{request.biz_content_model.code}",
                        "user_id": f"mock_alipay_user_id_{request.biz_content_model.code[:5]}",
                        "auth_app_id": self.app_id, # ISV app id
                        "expires_in": 31536000,
                        "re_expires_in": 31536000,
                        "app_refresh_token": f"mock_app_refresh_token_for_{request.biz_content_model.code}"
                    },
                    "sign": "mock_sign_value"
                }
            elif request.biz_content_model.grant_type == 'refresh_token':
                self.logger.info(f"Mocking token refresh for refresh_token: {request.biz_content_model.refresh_token}")
                return {
                     "alipay_open_auth_token_app_response": {
                        "code": "10000",
                        "msg": "Success",
                        "app_auth_token": f"mock_refreshed_app_auth_token_for_{request.biz_content_model.refresh_token[:10]}",
                        "user_id": f"mock_alipay_user_id_refreshed",
                        "auth_app_id": self.app_id,
                        "expires_in": 31536000,
                        "re_expires_in": 31536000,
                    },
                    "sign": "mock_sign_value"
                }
        self.logger.error(f"MockAlipayClient does not support request type: {request.__class__.__name__}")
        return None

class MockAlipayClientConfig:
    def __init__(self):
        self.app_id = None
        self.app_private_key = None
        self.alipay_public_key = None
        self.sign_type = "RSA2"
        self.sandbox_mode = False # Default to False, can be overridden by settings

class MockAlipayOpenAuthTokenAppModel:
    def __init__(self):
        self.grant_type = None # 'authorization_code' or 'refresh_token'
        self.code = None # auth_code
        self.refresh_token = None # refresh_token

class MockAlipayOpenAuthTokenAppRequest:
    def __init__(self):
        self.biz_content_model = MockAlipayOpenAuthTokenAppModel()
# --- End Mock SDK ---


_alipay_isv_client = None

def get_alipay_isv_client():
    """
    Initializes and returns an Alipay SDK client instance using settings.
    This is a mock version.
    """
    global _alipay_isv_client
    if _alipay_isv_client:
        return _alipay_isv_client

    if not hasattr(settings, 'ALIPAY_ISV_CONFIG'):
        logger.error("ALIPAY_ISV_CONFIG is not defined in Django settings.")
        return None

    config = settings.ALIPAY_ISV_CONFIG
    required_keys = ['APP_ID', 'APP_PRIVATE_KEY_STRING', 'ALIPAY_PUBLIC_KEY_STRING', 'OAUTH_CALLBACK_URL']
    for key in required_keys:
        if not config.get(key):
            logger.error(f"ALIPAY_ISV_CONFIG is missing required key: {key}")
            return None

    alipay_client_config = MockAlipayClientConfig() # Actual: AlipayClientConfig()
    alipay_client_config.app_id = config['APP_ID']
    alipay_client_config.app_private_key = config['APP_PRIVATE_KEY_STRING']
    alipay_client_config.alipay_public_key = config['ALIPAY_PUBLIC_KEY_STRING']
    alipay_client_config.sign_type = config.get('SIGN_TYPE', 'RSA2')
    alipay_client_config.sandbox_mode = config.get('DEBUG', False) # Use Django's DEBUG for sandbox mode

    # In actual SDK, logger might be passed differently or configured globally
    _alipay_isv_client = MockAlipayClient(alipay_client_config=alipay_client_config, logger_instance=logger) # Actual: DefaultAlipayClient(...)
    logger.info("Mock Alipay ISV client initialized.")
    return _alipay_isv_client


def generate_app_auth_url(state_param, is_sandbox=False):
    """
    Generates the URL to redirect the merchant to for app authorization.
    https://opendocs.alipay.com/open/20160728150111277227/appauthtutorial#%E6%8B%BC%E6%8E%A5%E6%8E%88%E6%9D%83%E9%93%BE%E6%8E%A5
    """
    if not hasattr(settings, 'ALIPAY_ISV_CONFIG'):
        logger.error("ALIPAY_ISV_CONFIG missing for generating auth URL.")
        return None

    app_id = settings.ALIPAY_ISV_CONFIG.get('APP_ID')
    redirect_uri = settings.ALIPAY_ISV_CONFIG.get('OAUTH_CALLBACK_URL')

    if not app_id or not redirect_uri:
        logger.error("APP_ID or OAUTH_CALLBACK_URL not configured for Alipay ISV.")
        return None

    base_url = "https://openauth.alipay.com/oauth2/appToAppAuth.htm"
    if is_sandbox or getattr(settings, 'ALIPAY_ISV_CONFIG', {}).get('DEBUG', False):
        base_url = "https://openauth.alipaydev.com/oauth2/appToAppAuth.htm"

    params = {
        "app_id": app_id,
        "redirect_uri": redirect_uri,
        "state": state_param # Custom state parameter
    }
    auth_url = f"{base_url}?{urlencode(params)}"
    logger.info(f"Generated Alipay ISV App Auth URL (state: {state_param}): {auth_url}")
    return auth_url


def exchange_auth_code_for_token(auth_code):
    """
    Exchanges an authorization code for an app_auth_token.
    Uses a mocked Alipay client.
    """
    client = get_alipay_isv_client()
    if not client:
        return None

    request = MockAlipayOpenAuthTokenAppRequest() # Actual: AlipayOpenAuthTokenAppRequest()
    model = request.biz_content_model # Actual: model = AlipayOpenAuthTokenAppModel()
    model.grant_type = "authorization_code"
    model.code = auth_code
    # request.biz_content = json.dumps(model.__dict__, ensure_ascii=False) # For actual SDK if model is dict-like

    try:
        response_dict = client.execute(request) # No app_auth_token needed for this specific call
        logger.debug(f"Alipay OpenAuthTokenApp (auth_code) raw response: {response_dict}")

        # Parse the mock dictionary response
        token_response = response_dict.get("alipay_open_auth_token_app_response", {})
        if token_response.get("code") == "10000":
            return {
                "app_auth_token": token_response.get("app_auth_token"),
                "app_refresh_token": token_response.get("app_refresh_token"),
                "alipay_user_id": token_response.get("user_id"), # This is the merchant's Alipay User ID
                "auth_app_id": token_response.get("auth_app_id"), # ISV's APP ID
                "expires_in": token_response.get("expires_in"),
                "re_expires_in": token_response.get("re_expires_in"),
            }
        else:
            logger.error(f"Error exchanging auth code: {token_response.get('msg')} (SubCode: {token_response.get('sub_code')}, SubMsg: {token_response.get('sub_msg')})")
            return None
    except Exception as e:
        logger.error(f"Exception exchanging auth code for token: {e}", exc_info=True)
        return None

def refresh_app_auth_token(refresh_token):
    """
    Refreshes an app_auth_token using a refresh_token.
    Uses a mocked Alipay client.
    """
    client = get_alipay_isv_client()
    if not client:
        return None

    request = MockAlipayOpenAuthTokenAppRequest() # Actual: AlipayOpenAuthTokenAppRequest()
    model = request.biz_content_model # Actual: AlipayOpenAuthTokenAppModel()
    model.grant_type = "refresh_token"
    model.refresh_token = refresh_token

    try:
        response_dict = client.execute(request)
        logger.debug(f"Alipay OpenAuthTokenApp (refresh_token) raw response: {response_dict}")

        token_response = response_dict.get("alipay_open_auth_token_app_response", {})
        if token_response.get("code") == "10000":
            return {
                "app_auth_token": token_response.get("app_auth_token"),
                "alipay_user_id": token_response.get("user_id"),
                "auth_app_id": token_response.get("auth_app_id"),
                "expires_in": token_response.get("expires_in"),
                # Note: refresh_token might not be returned again, or a new one might be. Behavior can vary.
            }
        else:
            logger.error(f"Error refreshing app_auth_token: {token_response.get('msg')} (SubCode: {token_response.get('sub_code')}, SubMsg: {token_response.get('sub_msg')})")
            return None
    except Exception as e:
        logger.error(f"Exception refreshing app_auth_token: {e}", exc_info=True)
        return None

# TODO: Add wrappers for other common Alipay ISV API calls (e.g., payment, query, refund)
# These would typically require `app_auth_token` to be passed to `client.execute()`.
# Example:
# def alipay_trade_create(app_auth_token, biz_content_model):
#     client = get_alipay_isv_client()
#     if not client: return None
#     request = AlipayTradeCreateRequest() # Actual SDK request object
#     request.biz_content_model = biz_content_model # Pass the specific model for trade create
#     response = client.execute(request, app_auth_token=app_auth_token)
#     # ... process response ...
#     return response

# --- Mocked Service Functions for Payment Processing ---

def batch_payment(orders_data, payment_subject_configs, app_auth_token):
    """
    Mocks calling an Alipay batch payment API.
    `orders_data`: list of dicts, each dict representing an order for Alipay.
                   e.g., [{"order_id": "our_id_1", "amount": "10.00", "payee_account": "...", ...}]
    `payment_subject_configs`: dict containing Alipay config for this subject.
    `app_auth_token`: The app_auth_token for the merchant.
    Returns a mocked response dictionary.
    """
    client = get_alipay_isv_client()
    if not client:
        logger.error("Alipay client not available for batch_payment.")
        # Simulate a total failure if client can't be initialized
        return {"error": "Alipay client configuration error.", "order_results": {
            order_item["order_id"]: {"status": "FAIL", "message": "Client init error"} for order_item in orders_data
        }}

    logger.info(f"Mocking Alipay batch payment for {len(orders_data)} orders. AppAuthToken: {app_auth_token[:10]}...")

    # Simulate some orders succeeding, some failing, some processing
    import random
    response = {"status": "PARTIAL_SUCCESS", "batch_id": f"mock_alipay_batch_{random.randint(1000,9999)}", "order_results": {}}

    for order_item in orders_data:
        rand_val = random.random()
        order_id_str = str(order_item.get("order_id", order_item.get("out_biz_no", "unknown"))) # Adapt to key used

        if rand_val < 0.7: # 70% success
            response["order_results"][order_id_str] = {
                "status": "SUCCESS",
                "message": "Payment successful.",
                "channel_tx_id": f"mock_alipay_tx_{order_id_str}_{random.randint(10000,99999)}"
            }
        elif rand_val < 0.9: # 20% processing
            response["order_results"][order_id_str] = {
                "status": "PROCESSING",
                "message": "Payment is processing.",
                "channel_tx_id": f"mock_alipay_tx_{order_id_str}_{random.randint(10000,99999)}"
            }
        else: # 10% failure
            response["order_results"][order_id_str] = {
                "status": "FAIL",
                "message": "Mocked payment failure (e.g., insufficient balance, risk).",
                "error_code": "MOCK_PAYMENT_ERROR"
            }

    # Simulate overall batch status based on order results
    all_success = all(res["status"] == "SUCCESS" for res in response["order_results"].values())
    any_success = any(res["status"] == "SUCCESS" for res in response["order_results"].values())

    if all_success: response["status"] = "SUCCESS"
    elif not any_success: response["status"] = "FAIL"
    # else it remains PARTIAL_SUCCESS

    logger.info(f"Mock Alipay batch payment response: {response}")
    return response


def query_transaction(our_order_id, payment_subject_configs, app_auth_token):
    """
    Mocks querying a single transaction status from Alipay.
    `our_order_id`: Our system's order ID or number.
    Returns a mocked transaction status dictionary.
    """
    client = get_alipay_isv_client()
    if not client:
        logger.error("Alipay client not available for query_transaction.")
        return {"status": "UNKNOWN", "message": "Client init error"}

    logger.info(f"Mocking Alipay transaction query for Order ID: {our_order_id}. AppAuthToken: {app_auth_token[:10]}...")

    # Simulate different outcomes for query
    import random
    rand_val = random.random()
    if rand_val < 0.8: # 80% chance it's now successful
        return {
            "status": "SUCCESS",
            "message": "Transaction successful (queried).",
            "channel_tx_id": f"mock_alipay_tx_{our_order_id}_{random.randint(10000,99999)}",
            "amount": "10.00", # Example
            "pay_time": "2023-10-01 10:00:00" # Example
        }
    elif rand_val < 0.95: # 15% chance it failed
        return {
            "status": "FAIL",
            "message": "Transaction failed (queried).",
            "error_code": "MOCK_QUERY_FAIL_ERROR"
        }
    else: # 5% chance it's still processing or unknown
        return {"status": "PROCESSING", "message": "Transaction still processing (queried)."}


def verify_callback_signature(callback_data_dict, alipay_public_key_string):
    """
    Mocks verifying the signature of an Alipay callback.
    In a real scenario, this uses the Alipay SDK's verify() method.
    `callback_data_dict`: The dictionary of parameters from Alipay (excluding 'sign_type', and 'sign' itself for verification).
    `alipay_public_key_string`: The Alipay public key string.
    Returns True if signature is (mock) verified, False otherwise.
    """
    # This is a MOCK. Real verification is complex.
    # The SDK handles stringifying, sorting, encoding, and crypto verification.
    if not callback_data_dict or not alipay_public_key_string:
        logger.error("Missing data or Alipay public key for signature verification mock.")
        return False

    # sign = callback_data_dict.get('sign') # The actual signature sent by Alipay
    # For mock purposes, we'll just assume it's valid if some key fields are present.
    if 'out_trade_no' in callback_data_dict and 'trade_no' in callback_data_dict and 'trade_status' in callback_data_dict:
        logger.info("Mock Alipay callback signature verification: PASSED (mocked)")
        return True

    logger.warning("Mock Alipay callback signature verification: FAILED due to missing key fields (mocked)")
    return False

def refund_transaction(original_order_id, refund_amount, refund_reason, payment_subject_configs, app_auth_token):
    """
    Mocks initiating a refund with Alipay.
    `original_order_id`: The `out_trade_no` (our system's order ID) of the transaction to refund.
    `refund_amount`: The amount to refund.
    `refund_reason`: Reason for the refund.
    Returns a mocked response dictionary.
    """
    client = get_alipay_isv_client()
    if not client:
        logger.error("Alipay client not available for refund_transaction.")
        return {"status": "FAIL", "message": "Client init error", "error_code": "CLIENT_INIT_ERROR"}

    logger.info(f"Mocking Alipay refund initiation for Order ID: {original_order_id}, Amount: {refund_amount}, Reason: {refund_reason}. AppAuthToken: {app_auth_token[:10]}...")

    import random
    # Simulate API call success/failure
    if random.random() < 0.9: # 90% chance the refund initiation call itself is accepted
        return {
            "status": "SUCCESS", # Indicates Alipay accepted the refund request
            "message": "Refund request accepted by Alipay, processing.",
            "channel_refund_id": f"mock_alipay_refund_tx_{original_order_id}_{random.randint(1000,9999)}",
            "original_order_id": original_order_id,
            "refund_amount": str(refund_amount)
        }
    else:
        return {
            "status": "FAIL",
            "message": "Mocked refund initiation failed (e.g., invalid parameters, duplicate refund ID).",
            "error_code": "MOCK_REFUND_INIT_FAIL"
        }

def query_refund_transaction(channel_refund_id_or_original_order_id, payment_subject_configs, app_auth_token, out_request_no=None):
    """
    Mocks querying a refund transaction status from Alipay.
    `channel_refund_id_or_original_order_id`: Alipay's refund_batch_no/trade_no or our original order ID.
    `out_request_no`: Our unique ID for the refund request if `original_order_id` is used for query.
    Returns a mocked refund status dictionary.
    """
    client = get_alipay_isv_client()
    if not client:
        logger.error("Alipay client not available for query_refund_transaction.")
        return {"status": "UNKNOWN", "message": "Client init error"}

    logger.info(f"Mocking Alipay refund query for ID: {channel_refund_id_or_original_order_id}. AppAuthToken: {app_auth_token[:10]}...")

    import random
    rand_val = random.random()
    if rand_val < 0.8: # 80% chance refund is now successful
        return {
            "status": "REFUND_SUCCESS",
            "message": "Refund successful (queried).",
            "channel_refund_id": f"mock_alipay_refund_tx_{channel_refund_id_or_original_order_id}",
            "original_order_id": channel_refund_id_or_original_order_id, # Assuming it's our ID for simplicity
            "refund_amount": "10.00", # Example
            "refund_time": "2023-10-01 11:00:00" # Example
        }
    elif rand_val < 0.95: # 15% chance it failed
        return {
            "status": "REFUND_FAIL",
            "message": "Refund failed (queried).",
            "error_code": "MOCK_REFUND_QUERY_FAIL"
        }
    else: # 5% chance it's still processing
        return {"status": "REFUND_PROCESSING", "message": "Refund still processing (queried)."}
