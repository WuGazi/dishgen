import os
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# Configure logging
if not app.debug:
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

# Root route to display a welcome message
@app.route('/')
def home():
    return "Welcome to the Dish Generator API! Use the /generate_dishes endpoint to generate dishes."

# Function to interact with ChatGPT
def interact_with_chatgpt(idea, style_influence):
    influences = ', '.join([f"{k}: {v}" for k, v in style_influence.items() if v > 5])
    prompt = (
        f"Create a luxurious three-course meal based on the idea '{idea}' with the following influences: {influences}. "
        f"Each course should include a name, a detailed description, a list of ingredients, and step-by-step instructions. "
        f"Format the response as:\n"
        f"Course 1: <Course Name>\nDescription: <Detailed Description>\nIngredients:\n- Ingredient 1\n- Ingredient 2\nInstructions:\n1. Step 1\n2. Step 2\n"
        f"Repeat this for all three courses."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a culinary expert generating three-course meals."},
                      {"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        courses = re.findall(r'Course \d+:.*?(?=Course \d+:|$)', content, re.DOTALL)

        parsed_courses = []
        for course in courses:
            name = re.search(r'Course \d+: (.+)', course)
            description = re.search(r'Description: (.+)', course, re.DOTALL)
            ingredients = re.search(r'Ingredients:\n(.+?)Instructions:', course, re.DOTALL)
            instructions = re.search(r'Instructions:\n(.+)', course, re.DOTALL)

            parsed_courses.append({
                "name": name.group(1).strip() if name else "Unnamed Course",
                "description": description.group(1).strip() if description else "No description provided.",
                "ingredients": ingredients.group(1).strip() if ingredients else "No ingredients provided.",
                "instructions": instructions.group(1).strip() if instructions else "No instructions provided."
            })

        return parsed_courses
    except Exception as e:
        app.logger.error(f"Error generating courses: {e}")
        return []

# Function to generate an image for a dish
def generate_image(description):
    try:
        description = description[:1000]
        response = client.images.generate(
            prompt=description,
            n=1,
            size="256x256"
        )
        if response and response.data and len(response.data) > 0:
            return response.data[0].url
        else:
            app.logger.error("Image generation failed.")
            return None
    except Exception as e:
        app.logger.error(f"Error generating image: {e}")
        return None

# Main route to generate dishes
@app.route('/generate_dishes', methods=['POST'])
def generate_dishes():
    data = request.json
    idea = data.get("idea")
    style_influence = data.get("style_influence", {})
    if not idea:
        return jsonify({"error": "Idea is required"}), 400

    courses = interact_with_chatgpt(idea, style_influence)
    if not courses:
        return jsonify({"error": "Failed to generate dishes."}), 500

    # Generate image for the main course (second course)
    main_course_description = courses[1]["description"] if len(courses) > 1 else "No description available."
    image_url = generate_image(main_course_description)

    return jsonify({"courses": courses, "image_url": image_url})

# Run the app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
