"""
Backend server for ColorMuse Books.

This Flask application provides an endpoint to process coloring book orders.
It performs the following steps:

1. Accepts a POST request containing a list of image URLs or base64‑encoded images
   for the coloring pages, along with customer details and the PayPal order ID.
2. Generates a single PDF from the images using the reportlab library.
3. Obtains an OAuth token from the Lulu Print API using the client key and secret
   stored in environment variables (LULU_CLIENT_KEY and LULU_CLIENT_SECRET).
4. Creates a print job via Lulu's API and uploads the generated PDF to the
   pre‑signed upload URL returned by the API.
5. (Optional) Sends a confirmation email to the customer (placeholder code).

Note: This is a skeleton implementation. You must replace the placeholder
credentials, API endpoints, and logic with real values from your PayPal and
Lulu accounts. This code is intended for demonstration and does not handle
payment verification or error handling for brevity. Do not use it in
production without proper testing and security reviews.
"""

import os
import base64
import io
from typing import List
from flask import Flask, request, jsonify
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


app = Flask(__name__)

def generate_pdf_from_images(images: List[str]) -> bytes:
    """Generate a PDF file from a list of image URLs or base64 strings.

    Args:
        images: A list of strings representing image sources. Each item can be
            either a data URI/base64 string (prefixed with 'data:image/') or a
            URL pointing to an image file accessible to the server.

    Returns:
        The binary contents of the generated PDF.
    """
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    for src in images:
        # Determine if the source is a data URI. If so, decode it; otherwise
        # download the image from the URL.
        if src.startswith('data:image/'):
            header, encoded = src.split(',', 1)
            img_data = base64.b64decode(encoded)
        else:
            resp = requests.get(src)
            resp.raise_for_status()
            img_data = resp.content

        # Create an ImageReader object from the image bytes
        from reportlab.lib.utils import ImageReader  # import here to avoid circular imports
        image_reader = ImageReader(io.BytesIO(img_data))
        img_width, img_height = image_reader.getSize()
        aspect = img_height / img_width
        # Fit the image within the page margins while preserving aspect ratio
        max_width = width - 72  # 1 inch margins on left and right
        max_height = height - 72  # 1 inch margins on top and bottom
        draw_width = max_width
        draw_height = draw_width * aspect
        if draw_height > max_height:
            draw_height = max_height
            draw_width = draw_height / aspect
        # Center the image on the page
        x = (width - draw_width) / 2
        y = (height - draw_height) / 2
        pdf.drawImage(image_reader, x, y, width=draw_width, height=draw_height)
        pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def get_lulu_access_token() -> str:
    """Obtain an OAuth access token from Lulu using client key/secret.

    Returns the access token as a string.
    """
    client_key = os.environ.get('LULU_CLIENT_KEY')
    client_secret = os.environ.get('LULU_CLIENT_SECRET')
    if not client_key or not client_secret:
        raise RuntimeError('LULU_CLIENT_KEY and LULU_CLIENT_SECRET must be set.')

    token_url = 'https://auth.lulu.com/oauth/token'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_key,
        'client_secret': client_secret
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    resp = requests.post(token_url, data=payload, headers=headers)
    resp.raise_for_status()
    token_data = resp.json()
    return token_data['access_token']


# PayPal utility functions

def get_paypal_access_token() -> str:
    """Obtain an OAuth access token from PayPal.

    The PayPal client ID and secret must be provided via environment variables
    PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET. This function uses PayPal's
    OAuth2 token endpoint to fetch a short-lived bearer token.

    Returns:
        The access token as a string.
    """
    client_id = os.environ.get('PAYPAL_CLIENT_ID')
    client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise RuntimeError('PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set.')

    # Use PayPal's live environment by default. For testing, replace with the
    # sandbox domain (https://api-m.sandbox.paypal.com) and set credentials for
    # the sandbox application.
    token_url = 'https://api-m.paypal.com/v1/oauth2/token'
    auth = (client_id, client_secret)
    headers = {'Accept': 'application/json', 'Accept-Language': 'en_US'}
    payload = {'grant_type': 'client_credentials'}
    resp = requests.post(token_url, data=payload, headers=headers, auth=auth)
    resp.raise_for_status()
    return resp.json()['access_token']


def verify_paypal_order(order_id: str) -> bool:
    """Verify a PayPal order by retrieving its status via the Orders API.

    Args:
        order_id: The PayPal order ID returned after checkout.

    Returns:
        True if the order is completed (paid); False otherwise.
    """
    access_token = get_paypal_access_token()
    # For sandbox use https://api-m.sandbox.paypal.com
    order_url = f'https://api-m.paypal.com/v2/checkout/orders/{order_id}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    resp = requests.get(order_url, headers=headers)
    if resp.status_code != 200:
        print('PayPal order verification failed:', resp.text)
        return False
    order_data = resp.json()
    status = order_data.get('status')
    # The status should be 'COMPLETED' for a paid order
    return status == 'COMPLETED'


# Email utility function
def send_confirmation_email(to_email: str, subject: str, body: str) -> None:
    """Send an email using SMTP credentials stored in environment variables.

    Environment variables required:
        SMTP_SERVER: The hostname of the SMTP server (e.g. smtp.gmail.com)
        SMTP_PORT: The port of the SMTP server (e.g. 587)
        SMTP_USERNAME: SMTP account username
        SMTP_PASSWORD: SMTP account password
        FROM_EMAIL: Sender email address

    Raises an exception if sending fails.
    """
    import smtplib
    from email.mime.text import MIMEText

    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    from_email = os.environ.get('FROM_EMAIL')
    if not all([smtp_server, smtp_username, smtp_password, from_email]):
        raise RuntimeError('SMTP credentials are not fully configured.')

    msg = MIMEText(body, 'plain')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)



def create_lulu_print_job(pdf_bytes: bytes, shipping_address: dict) -> dict:
    """Create a print job on Lulu and upload the PDF.

    Args:
        pdf_bytes: The generated PDF as a byte string.
        shipping_address: A dictionary with keys such as 'name', 'address1',
            'city', 'state', 'zip', 'country'. See Lulu documentation for
            required fields.

    Returns:
        The API response from Lulu as a dictionary.
    """
    access_token = get_lulu_access_token()
    # Step 1: Create a print job
    create_job_url = 'https://api.lulu.com/print-jobs/'
    job_payload = {
        'contact_email': shipping_address.get('email'),
        'shipping_address': shipping_address,
        'line_items': [
            {
                'quantity': 1,
                'title': 'Custom Coloring Book',
                'cover': {
                    'url': 'upload'  # placeholder; Lulu will return upload URL
                },
                'book': {
                    'url': 'upload',  # placeholder for interior PDF upload
                    'format': 'US_TRADE',  # choose an appropriate size
                    'cover_type': 'PAPERBACK',
                    'page_count': len(pdf_bytes)  # approximate; adjust after upload
                }
            }
        ]
    }
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    job_resp = requests.post(create_job_url, json=job_payload, headers=headers)
    job_resp.raise_for_status()
    job_data = job_resp.json()
    # Extract upload URL and file ID for the interior PDF
    files_info = job_data.get('files', [])
    # For simplicity, assume the first file is the interior PDF
    pdf_file_info = next((f for f in files_info if f.get('type') == 'book'), None)
    if not pdf_file_info:
        raise RuntimeError('Print job response did not include PDF file upload information.')
    upload_url = pdf_file_info['upload_url']
    # Step 2: Upload the PDF to the provided URL
    upload_resp = requests.put(upload_url, data=pdf_bytes, headers={'Content-Type': 'application/pdf'})
    upload_resp.raise_for_status()
    return job_data


@app.route('/api/order', methods=['POST'])
def handle_order():
    """Endpoint to process a coloring book order.

    Expects a JSON payload with keys:
        images: List of image sources (URLs or data URIs) for the coloring pages.
        customer: Dictionary with name, email, and shipping address fields.
        paypal_order_id: The PayPal order ID returned after payment.

    Returns a JSON response indicating success or failure.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    images = data.get('images')
    customer = data.get('customer')
    paypal_order_id = data.get('paypal_order_id')
    if not images or not customer or not paypal_order_id:
        return jsonify({'error': 'Missing required fields (images, customer, paypal_order_id)'}), 400

    # Verify PayPal payment
    try:
        if not verify_paypal_order(paypal_order_id):
            return jsonify({'error': 'Payment not completed. Order has not been processed.'}), 402
    except Exception as e:
        return jsonify({'error': f'Failed to verify PayPal order: {e}'}), 500

    try:
        # Generate PDF from the provided images
        pdf_bytes = generate_pdf_from_images(images)
        # Create print job and upload PDF via Lulu API
        job_response = create_lulu_print_job(pdf_bytes, customer)
        # Compose and send a confirmation email to the customer
        email_body = (
            f"Hello {customer.get('name')},\n\n"
            "Thank you for your purchase! Your custom coloring book is being printed and "
            "will be shipped to the address you provided. We'll notify you when your "
            "order ships.\n\n"
            f"Order ID (PayPal): {paypal_order_id}\n"
            f"Lulu Job ID: {job_response.get('id')}\n\n"
            "Thank you for choosing ColorMuse Books!\n"
        )
        try:
            send_confirmation_email(
                to_email=customer.get('email'),
                subject='Your ColorMuse Books Order',
                body=email_body
            )
        except Exception as e:
            # Log email sending errors but do not block order processing
            print('Error sending confirmation email:', e)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'Order processed successfully', 'lulu_job': job_response}), 200


if __name__ == '__main__':
    # Only for local testing; when deployed to production use a WSGI server
    app.run(host='0.0.0.0', port=5000, debug=True)