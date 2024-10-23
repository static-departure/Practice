from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from intasend import APIService
import os
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set your API token and publishable key as environment variables
TOKEN = os.getenv("INTASEND_API_TOKEN")
PUBLISHABLE_KEY = os.getenv("PUBLISHABLE_KEY")

# Initialize the IntaSend APIService
service = APIService(token=TOKEN, publishable_key=PUBLISHABLE_KEY, test=True)

# Route to display the shop page
@app.route('/')
def shop():
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
        phone_number = request.form['phone_number']
        email = request.form['email']
        amount = float(request.form['amount'])

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

        logging.info(f"Initiating STK Push for phone: {phone_number}, email: {email}, amount: {amount}")
        response = service.collect.mpesa_stk_push(
            phone_number=phone_number,
            email=email,
            amount=amount,
            narrative=narrative
        )

        logging.info(f"Full STK Push response: {response}")

        if response.get("success") == True:
            transaction_id = response.get("transaction_id")
            logging.info(f"Transaction ID: {transaction_id}")

            if not transaction_id:
                logging.warning("Transaction ID is missing in response: %s", response)
                return redirect(url_for('failure'))

            # Here, we use the transaction_id to check the status of the payment
            status_response = service.collect.check_transaction_status(transaction_id)
            logging.info(f"Transaction status response: {status_response}")

            transaction_state = status_response.get('state')
            success_flag = status_response.get("success")

            logging.info(f"Transaction State: {transaction_state}, Success: {success_flag}")

            # Handle PENDING status based on JSON response
            if transaction_state == 'PENDING' or status_response.get('ResponseCode') == "1":
                logging.info(f"Transaction is pending for transaction ID: {transaction_id}")
                return redirect(url_for('pending', transaction_id=transaction_id))
            
            # Handle SUCCESS status based on JSON response
            elif transaction_state == 'COMPLETE' or status_response.get("ResponseCode") == "0":
                logging.info(f"Transaction is complete for transaction ID: {transaction_id}")
                return redirect(url_for('success'))
            
            else:
                logging.warning(f"Transaction failed or unknown state: {transaction_state}")
                return redirect(url_for('failure'))

        else:
            logging.warning(f"STK Push failed: {response}")
            return redirect(url_for('failure'))

    except Exception as e:
        logging.error(f"Error occurred during payment processing: {str(e)}")
        return jsonify({"error": "An error occurred", "message": str(e)}), 500

# Pending route when payment is awaiting action (e.g., PIN input)
@app.route('/pay/pending')
def pending():
    transaction_id = request.args.get('transaction_id')
    return render_template('pending.html', message="Payment is Pending. Please complete the transaction.", transaction_id=transaction_id)

# Success route after payment is complete
@app.route('/pay/success')
def success():
    return render_template('success.html', message="Payment Successful! Thank you for your purchase.")

# Failure route in case of payment failure
@app.route('/pay/failure')
def failure():
    return render_template('failure.html', message="Payment Failed. Please try again or contact support.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
