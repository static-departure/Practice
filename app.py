from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from intasend import APIService
import os
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set your API token and publishable key as environment variables
TOKEN = os.getenv("INTASEND_API_TOKEN")
PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")

if not TOKEN or not PUBLISHABLE_KEY:
    logging.error("API token or Publishable key not found in environment variables.")

# Initialize the IntaSend APIService
service = APIService(token=TOKEN, publishable_key=PUBLISHABLE_KEY, test=True)

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
    import re
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Route to handle form submission and initiate STK push
@app.route('/pay', methods=['POST'])
def initiate_stk_push():
    try:
        # Collect data from the form
        phone_number = request.form['phone_number']
        email = request.form['email']
        amount = float(request.form['amount'])

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

        narrative = "Purchase"

        # Send the STK Push request using IntaSend
        logging.info(f"Initiating STK Push for phone: {phone_number}, email: {email}, amount: {amount}")
        response = service.collect.mpesa_stk_push(
            phone_number=phone_number,
            email=email,
            amount=amount,
            narrative=narrative
        )

        # Log the STK Push response
        logging.info(f"STK Push response: {response}")

        # Check if the STK Push was successful
        if response.get("success") == True:
            transaction_id = response.get("transaction_id")
            logging.info(f"Transaction ID: {transaction_id}")

            if not transaction_id:
                logging.warning("Transaction ID is missing in response: %s", response)
                return redirect(url_for('failure'))

            # Now, let's check the status of the transaction
            status_response = service.collect.check_transaction_status(transaction_id)
            logging.info(f"Initial transaction status response: {status_response}")
            transaction_state = status_response.get('state')

            # If the state is 'PENDING', redirect to the pending page
            if transaction_state == 'PENDING':
                return redirect(url_for('pending', transaction_id=transaction_id))
            elif transaction_state == 'COMPLETE':
                return redirect(url_for('success'))
            else:
                # Any other state is considered a failure
                logging.warning(f"Transaction state unexpected: {transaction_state}")
                return redirect(url_for('failure'))

        else:
            logging.warning(f"STK Push failed: {response}")
            return redirect(url_for('failure'))

    except Exception as e:
        logging.error(f"Error occurred during payment processing: {str(e)}")
        return jsonify({"error": "An error occurred", "message": str(e)}), 500

# Pending page that checks the transaction status periodically
@app.route('/pending/<transaction_id>')
def pending(transaction_id):
    try:
        # Check transaction status using the transaction ID
        status_response = service.collect.check_transaction_status(transaction_id)
        logging.info(f"Transaction status response in pending: {status_response}")

        if status_response.get("success") == True:
            transaction_state = status_response.get('state')
            logging.info(f"Transaction state: {transaction_state}")

            if transaction_state == 'PENDING':
                # Keep the user on the pending page if the transaction is still pending
                return render_template('pending.html', message="Payment is pending. Please check your phone to confirm the transaction.")
            elif transaction_state == 'COMPLETE':
                # Redirect to success if the payment is completed
                return redirect(url_for('success'))
            else:
                # Handle other cases (e.g., failed transaction)
                logging.warning(f"Unexpected transaction state: {transaction_state}")
                return redirect(url_for('failure'))
        else:
            logging.warning(f"Transaction status check failed: {status_response}")
            return redirect(url_for('failure'))

    except Exception as e:
        logging.error(f"Error occurred during status check: {str(e)}")
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
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Starting the app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)

