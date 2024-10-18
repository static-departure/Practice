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

# Log if tokens are not properly loaded
if not TOKEN or not PUBLISHABLE_KEY:
    logging.error("API token or Publishable key not found in environment variables.")

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
            logging.warning("Invalid phone number: %s", phone_number)
            abort(400, description="Invalid phone number.")
        if amount <= 0:
            logging.warning("Invalid amount: %s", amount)
            abort(400, description="Amount must be positive.")
        if not validate_email(email):
            logging.warning("Invalid email address: %s", email)
            abort(400, description="Invalid email address.")

        narrative = "Purchase"  # Set the narrative for the transaction

        # Prepare and send the STK Push request using IntaSend
        logging.info(f"Initiating STK Push for phone: {phone_number}, email: {email}, amount: {amount}")
        response = service.collect.mpesa_stk_push(
            phone_number=phone_number,
            email=email,
            amount=amount,
            narrative=narrative
        )

        # Log the STK Push response for debugging
        logging.info(f"STK Push response: {response}")

        # Check if the STK Push was successful
        if response.get("success") == True:  # Ensure this checks for boolean True
            transaction_id = response.get("transaction_id")  # Get transaction ID
            logging.info(f"Transaction ID: {transaction_id}")

            if not transaction_id:
                logging.warning("Transaction ID is missing in response: %s", response)
                return redirect(url_for('failure'))

            # Check transaction status using the transaction ID
            logging.info(f"Checking transaction status for ID: {transaction_id}")
            status_response = service.collect.check_transaction_status(transaction_id)
            logging.info(f"Transaction status response: {status_response}")

            if status_response.get("success") == True:
                logging.info("Payment was successful.")
                return redirect(url_for('success'))
            else:
                logging.warning(f"Transaction failed: {status_response}")
                return redirect(url_for('failure'))
        else:
            logging.warning(f"STK Push failed: {response}")
            return redirect(url_for('failure'))

    except Exception as e:
        logging.error(f"Error occurred during payment processing: {str(e)}")
        return jsonify({"error": "An error occurred", "message": str(e)}), 500

# Success route after payment is complete
@app.route('/success')
def success():
    return render_template('success.html', message="Payment Successful! Thank you for your purchase.")

# Failure route in case of payment failure
@app.route('/failure')
def failure():
    return render_template('failure.html', message="Payment Failed. Please try again or contact support.")

if __name__ == '__main__':
    # Check if PORT environment variable is set, default to 5000
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Starting the app on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=True)  # Keep debug=True for testing
