from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from intasend import APIService
import os
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set your API token and publishable key as environment variables
TOKEN = os.getenv("INTASEND_API_TOKEN")  # Set your API token in the environment
PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")  # Set your publishable key in the environment

# Initialize the IntaSend APIService
service = APIService(token=TOKEN, publishable_key=PUBLISHABLE_KEY, test=True)  # test=True for testing

# Route to display the shop page
@app.route('/')
def Shop():
    return render_template('Shop.html')

# Route to display the payment form
@app.route('/payment_form')
def payment_form():
    return render_template('payment_form.html')

# Function to validate email format
def validate_email(email):
    # Simple email validation logic
    import re
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Route to handle form submission and initiate STK push
@app.route('/pay', methods=['POST'])
def initiate_stk_push():
    try:
        # Collect data from the form
        phone_number = request.form['phone_number']
        email = request.form['email']
        amount = float(request.form['amount'])  # Convert amount to float

        # Input validation
        if not phone_number.isdigit() or len(phone_number) < 10:
            abort(400, description="Invalid phone number.")
        if amount <= 0:
            abort(400, description="Amount must be positive.")
        if not validate_email(email):
            abort(400, description="Invalid email address.")

        narrative = "Purchase"  # Set the narrative for the transaction

        # Prepare and send the STK Push request using IntaSend
        response = service.collect.mpesa_stk_push(
            phone_number=phone_number,
            email=email,
            amount=amount,
            narrative=narrative
        )

        # Log the response for debugging
        logging.info("STK Push response: %s", response)

        # Check the response from IntaSend for the correct success indicator
  try:
    # Assuming 'response' is obtained from IntaSend API call
    # Check the response from IntaSend for the correct success indicator
    if response.get("success") == True:  # Adjusted to check for "success" key
        return redirect(url_for('payment_success'))
    else:
        # Log failure reason for debugging
        logging.warning("Payment failure: %s", response)
        return redirect(url_for('payment_failure'))

except Exception as e:
    logging.error("Error occurred: %s", str(e))
    return jsonify({"error": "An error occurred", "message": str(e)}), 500

# Success route after payment is complete
@app.route('/payment/success')
def payment_success():
    return render_template('success.html', message="Payment Successful! Thank you for your purchase.")

# Failure route in case of payment failure
@app.route('/payment/failure')
def payment_failure():
    return render_template('failure.html', message="Payment Failed. Please try again or contact support.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)  # Keep debug=True for testing

