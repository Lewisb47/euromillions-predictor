# EuroMillions Line Generator (Hot Number Strategy) with Web App Interface + Cold Filter + Export + Result Checker + Email Notifications + SaaS Auth & Stripe
import random
import streamlit as st
import pandas as pd
import smtplib
from email.message import EmailMessage
import firebase_admin
from firebase_admin import credentials, auth
import stripe
import os

# Initialize Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")  # Replace with your Firebase JSON
    firebase_admin.initialize_app(cred)

# Stripe Configuration (Replace with your keys or use environment variables)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
PRODUCT_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

# Hot and Cold Numbers
HOT_MAIN_NUMBERS = [17, 19, 20, 23, 27, 35, 38, 40, 44, 50]
HOT_STARS = [2, 3, 8, 9, 10]
COLD_MAIN_NUMBERS = [1, 22, 26, 33, 43]
COLD_STARS = [6, 11]

def filter_hot_numbers(hot, cold):
    return [num for num in hot if num not in cold]

def generate_line():
    filtered_main = filter_hot_numbers(HOT_MAIN_NUMBERS, COLD_MAIN_NUMBERS)
    filtered_stars = filter_hot_numbers(HOT_STARS, COLD_STARS)
    main_balls = sorted(random.sample(filtered_main, 5))
    lucky_stars = sorted(random.sample(filtered_stars, 2))
    return main_balls, lucky_stars

def generate_multiple_lines(n=5):
    return [generate_line() for _ in range(n)]

def compare_with_results(predictions, actual_main, actual_stars):
    results = []
    for i, (main, stars) in enumerate(predictions):
        main_matches = len(set(main) & set(actual_main))
        star_matches = len(set(stars) & set(actual_stars))
        results.append({
            "Line": i + 1,
            "Main Balls": ', '.join(map(str, main)),
            "Lucky Stars": ', '.join(map(str, stars)),
            "Main Matches": main_matches,
            "Star Matches": star_matches
        })
    return pd.DataFrame(results)

def send_email(recipient, lines):
    msg = EmailMessage()
    msg['Subject'] = 'Your EuroMillions Predictions'
    msg['From'] = os.getenv('EMAIL_SENDER')
    msg['To'] = recipient
    body = "Here are your EuroMillions predictions:\n\n"
    for i, (main, stars) in enumerate(lines, 1):
        body += f"Line {i}: Main Balls: {main} | Lucky Stars: {stars}\n"
    msg.set_content(body)

    try:
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), 587) as server:
            server.starttls()
            server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
            server.send_message(msg)
            return True
    except Exception as e:
        return str(e)

def create_checkout_session(email):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': PRODUCT_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            customer_email=email,
            success_url='https://yourdomain.com/success',
            cancel_url='https://yourdomain.com/cancel',
        )
        return session.url
    except Exception as e:
        return str(e)

# Streamlit UI
st.title("🎯 EuroMillions Predictor - Hot Numbers Strategy (SaaS Edition)")

st.markdown("Sign up to access premium weekly predictions and hot picks.")
email = st.text_input("Enter your email:")
subscribe = st.button("Subscribe for Weekly Predictions (£3.99/month)")

if subscribe and email:
    url = create_checkout_session(email)
    if url.startswith("http"):
        st.success("Redirecting to secure checkout...")
        st.markdown(f"[Click here if not redirected]({url})")
    else:
        st.error(f"Failed to create checkout session: {url}")

if st.button("Generate Free Preview Lines"):
    lines = generate_multiple_lines(5)
    df = pd.DataFrame([{
        "Line": i + 1,
        "Main Balls": ', '.join(map(str, main)),
        "Lucky Stars": ', '.join(map(str, stars))
    } for i, (main, stars) in enumerate(lines)])

    st.dataframe(df)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Preview CSV", data=csv, file_name="euromillions_preview.csv", mime="text/csv")

    if email:
        result = send_email(email, lines)
        if result is True:
            st.success("✅ Preview email sent successfully!")
        else:
            st.error(f"❌ Failed to send preview email: {result}")

    st.markdown("---")
    st.subheader("🔎 Check Results Against Winning Numbers")
    actual_main = st.text_input("Enter winning main numbers (comma-separated):", "")
    actual_stars = st.text_input("Enter winning lucky stars (comma-separated):", "")

    if actual_main and actual_stars:
        try:
            actual_main_list = sorted([int(x.strip()) for x in actual_main.split(",") if x.strip().isdigit()])
            actual_stars_list = sorted([int(x.strip()) for x in actual_stars.split(",") if x.strip().isdigit()])
            result_df = compare_with_results(lines, actual_main_list, actual_stars_list)
            st.markdown("### 🎉 Match Results")
            st.dataframe(result_df)
        except ValueError:
            st.error("Please enter valid numbers.")
