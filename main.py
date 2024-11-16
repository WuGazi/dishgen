import os
import boto3
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()
bucket_name = os.getenv('BUCKET_NAME')
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
openai_api_key = os.getenv('OPENAI_API_KEY')

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

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


def generate_image(description):
    try:
        description = description[:1000]  # Truncate if needed
        app.logger.debug(f"Generating image for: {description}")
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


def interact_with_chatgpt(idea, style_influence):
    try:
        # Generate ingredients and instructions
        influences = ', '.join([f"{k}: {v}" for k, v in style_influence.items() if v > 5])
        ingredients_prompt = (
            f"Create a detailed list of ingredients and step-by-step cooking instructions "
            f"for a dish inspired by '{idea}'. The dish should reflect the following influences: {influences}. "
            f"Make it unique, luxurious, and suitable for a fine dining menu."
        )
        ingredients_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant that creates recipes."},
                      {"role": "user", "content": ingredients_prompt}],
            max_tokens=500,
            temperature=0.7
        )
        content = ingredients_response.choices[0].message.content.strip()
        ingredients = re.search(r'Ingredients:(.*?)Instructions:', content, re.DOTALL)
        instructions = re.search(r'Instructions:(.*)', content, re.DOTALL)
        ingredients = ingredients.group(1).strip() if ingredients else "No ingredients found."
        instructions = instructions.group(1).strip() if instructions else "No instructions found."

        # Generate menu description
        description_prompt = (
            f"Based on the following refined recipe, craft a luxurious menu description:\n\n"
            f"Ingredients:\n{ingredients}\n\nInstructions:\n{instructions}"
        )
        description_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are an expert in menu descriptions."},
                      {"role": "user", "content": description_prompt}],
            max_tokens=200,
            temperature=0.7
        )
        description = description_response.choices[0].message.content.strip()

        # Generate a short name
        name_prompt = f"Create a short (2-5 words) dish name inspired by the menu description: '{description}'."
        name_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are an expert in naming dishes."},
                      {"role": "user", "content": name_prompt}],
            max_tokens=20,
            temperature=0.8
        )
        short_name = name_response.choices[0].message.content.strip()

        app.logger.info(f"Generated Dish: {short_name}")
        return short_name, description, ingredients, instructions
    except Exception as e:
        app.logger.error(f"Error interacting with ChatGPT: {e}")
        return None, None, None, None


@app.route('/generate_dishes', methods=['POST'])
def generate_dishes():
    data = request.json
    idea = data.get("idea")
    style_influence = data.get("style_influence", {})
    if not idea:
        return jsonify({"error": "Idea is required"}), 400

    short_name, description, ingredients, instructions = interact_with_chatgpt(idea, style_influence)
    if not all([short_name, description, ingredients, instructions]):
        return jsonify({"error": "Failed to generate dish details."}), 500

    # Generate image based on the menu description
    image_url = generate_image(description)

    response_data = {
        "short_name": short_name,
        "menu_item_description": description,
        "ingredients": ingredients.replace('\n', '\n- '),
        "instructions": instructions,
        "image_url": image_url,
    }
    return jsonify(response_data)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
