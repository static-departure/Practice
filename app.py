from flask import Flask, render_template, request, jsonify, redirect, url_for
from intasend import APIService
import os

app = Flask(__name__)

# Set your API token and publishable key as environment variables
TOKEN = os.getenv("INTASEND_API_TOKEN")  # Set your API token in the environment
PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")  # Set your publishable key in the environment

# Initialize the IntaSend APIService
service = APIService(token=TOKEN, publishable_key=PUBLISHABLE_KEY)

# Route to display the shop page
@app.route('/')
def Shop():
    return render_template('Shop.html') 

# Route to display the payment form
@app.route('/payment_form')
def payment_form():
    return render_template('payment_form.html')


# Route to handle form submission and initiate STK push
@app.route('/pay', methods=['POST'])
def initiate_stk_push():
    try:
        # Collect data from the form
        phone_number = request.form['phone_number']
        email = request.form['email']
        amount = float(request.form['amount'])  # Convert amount to float
        narrative = "Purchase"  # Set the narrative for the transaction

        # Prepare and send the STK Push request
        response = service.collect.mpesa_stk_push(
            phone_number=phone_number,
            email=email,
            amount=amount,
            narrative=narrative
        )

        # Check the response from IntaSend
        if response.get("status") == "success":
            # Redirect to the success page
            return redirect(url_for('payment_success'))
        else:
            # Redirect to the failure page if status is not success
            return redirect(url_for('payment_failure'))

    except Exception as e:
        # Catch all exceptions and return an error message
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
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)
