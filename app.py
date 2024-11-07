from flask import Flask, render_template, request, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from wordcloud import WordCloud
from PIL import Image
import io
import base64

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"), server_api=ServerApi('1'))
db = client["wordcloud_db"]
collection = db["words"]


# Version counter for word cloud updates
wordcloud_version = 0
current_wordcloud_image = ""

# Add the full text submission as a single "word" in the database
def add_text_to_db(text):
    global wordcloud_version, current_wordcloud_image
    existing_text = collection.find_one({"word": text})
    if existing_text:
        collection.update_one({"word": text}, {"$inc": {"count": 1}})
    else:
        collection.insert_one({"word": text, "count": 1})
    # Increment the version and regenerate the word cloud
    wordcloud_version += 1
    current_wordcloud_image = generate_word_cloud()

# Generate the word cloud based on current data in MongoDB
def generate_word_cloud():
    word_counts = {doc["word"]: doc["count"] for doc in collection.find()}
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(word_counts)
    image = wordcloud.to_image()
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Route to submit new text
@app.route("/submit", methods=["POST"])
def submit():
    text = request.form.get("text")
    if text and len(text) <= 80:
        add_text_to_db(text.strip())  # Treat the entire text submission as a single "word"
    return jsonify(success=True)

# Route to get the current word cloud image based on MongoDB data and version check
@app.route("/wordcloud", methods=["GET"])
def get_wordcloud():
    client_version = int(request.args.get("version", 0))
    # Only send updated word cloud if there’s a new version
    if client_version < wordcloud_version:
        return jsonify(image=current_wordcloud_image, version=wordcloud_version)
    return jsonify(image=None, version=wordcloud_version)  # No update

# Home page with HTML template
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    generate_word_cloud()
    app.run(debug=True)