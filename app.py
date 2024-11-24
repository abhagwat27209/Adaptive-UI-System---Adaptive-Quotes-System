from flask import Flask, render_template, request, jsonify
import pandas as pd
import sqlite3

app = Flask(__name__)

# Load the dataset
quotes_df = pd.read_csv('/Users/adityanitinbhagwat/Desktop/AdaptiveUI/quotes.csv')  # Path to the downloaded dataset

# Ensure necessary columns exist
assert 'quote' in quotes_df.columns and 'category' in quotes_df.columns

# Database setup
def init_db():
    conn = sqlite3.connect('user_feedback.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (user_id TEXT, quote_id INTEGER, feedback TEXT)''')
    conn.commit()
    conn.close()

# Function to get adaptive recommendation
def get_adaptive_recommendation(user_id, genre=None):
    conn = sqlite3.connect('user_feedback.db')
    c = conn.cursor()

    # Get feedback for the user
    c.execute('SELECT quote_id, feedback FROM feedback WHERE user_id = ?', (user_id,))
    feedback_data = c.fetchall()
    conn.close()

    # Count feedback by category
    tag_preference = {}
    for quote in feedback_data:
        quote_id = quote[0]
        feedback = quote[1]

        # Skip invalid feedback entries
        if quote_id is None or feedback is None:
            continue

        # Check if the quote_id exists in the DataFrame
        if quote_id in quotes_df.index:
            category = quotes_df.loc[quote_id, 'category']
            if feedback == "like":
                for tag in category.split(','):
                    tag_preference[tag.strip()] = tag_preference.get(tag.strip(), 0) + 1

    # Filter by preferred category or genre
    preferred_tag = max(tag_preference, key=tag_preference.get, default=None)
    if genre:
        filtered_quotes = quotes_df[quotes_df['category'].str.contains(genre, na=False, case=False)]
    elif preferred_tag:
        filtered_quotes = quotes_df[quotes_df['category'].str.contains(preferred_tag, na=False, case=False)]
    else:
        filtered_quotes = quotes_df

    # Choose a random quote
    if filtered_quotes.empty:
        return {"id": None, "text": "No quotes available for this preference.", "category": ""}
    random_quote = filtered_quotes.sample(1).iloc[0]

    # Ensure all data types are JSON serializable
    return {
        "id": int(random_quote.name),  # Convert index to native int
        "text": random_quote['quote'],
        "category": random_quote['category']
    }

@app.route('/')
def home():
    """Render the homepage with a random quote."""
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    """Adaptively recommend quotes based on user feedback and genre."""
    user_data = request.json
    user_id = user_data.get('userId')
    genre = user_data.get('genre')

    # Validate user_id
    if not user_id:
        return jsonify({"error": "Invalid user ID"}), 400

    recommended_quote = get_adaptive_recommendation(user_id, genre)
    return jsonify(recommended_quote)

@app.route('/feedback', methods=['POST'])
def feedback():
    """Receive user feedback for a quote."""
    user_data = request.json
    user_id = user_data.get('userId')
    quote_id = user_data.get('quoteId')
    feedback = user_data.get('feedback')

    # Validate inputs
    if quote_id is None or feedback not in ['like', 'dislike']:
        return jsonify({"error": "Invalid feedback data"}), 400

    conn = sqlite3.connect('user_feedback.db')
    c = conn.cursor()
    c.execute('INSERT INTO feedback (user_id, quote_id, feedback) VALUES (?, ?, ?)', (user_id, quote_id, feedback))
    conn.commit()
    conn.close()

    return jsonify({"message": "Feedback recorded successfully!"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)