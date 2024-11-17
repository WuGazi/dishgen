import os
import boto3
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

client = OpenAI(api_key=openai_api_key)
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()
bucket_name = os.getenv('BUCKET_NAME')
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
openai_api_key = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI API

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for the app
CORS(app)

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

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


# Step 1: Generate Description from Prompt and Style Influences
def generate_description(idea, style_influence):
    try:
        # Prepare the style influence part of the prompt
        style_texts = [f"{key}: {value}" for key, value in style_influence.items() if value > 5]
        style_description = ", ".join(style_texts)

        # Construct the prompt
        prompt = (
            f"Create a luxurious menu description for a dish based on the idea '{idea}' with the following influences: {style_description}. "
            f"The description should be evocative, luxurious, and provide a vivid sense of what the dish is like."
        )

        response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a culinary expert generating dish descriptions."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.7)

        # Extract the generated description
        description = response.choices[0].message.content.strip()
        return description
    except Exception as e:
        app.logger.error(f"Error generating description: {e}")
        return None


# Step 2: Generate Dish Name from Description
def generate_name(description):
    try:
        prompt = f"Based on the following menu description, generate a short and inspired name for the dish: '{description}'"

        response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a culinary expert generating dish names."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=50,
        temperature=0.7)

        # Extract the generated name
        name = response.choices[0].message.content.strip()
        return name
    except Exception as e:
        app.logger.error(f"Error generating name: {e}")
        return None


# Step 3: Generate Ingredients, Components, and Instructions from Description
def generate_ingredients_components_instructions(description):
    try:
        # Prompt for generating the ingredients, components, and instructions
        prompt = (
            f"Based on the following menu description: '{description}', generate the following:\n"
            f"1. A detailed list of ingredients.\n"
            f"2. Components or parts of the dish (e.g., sauce, filling, garnish).\n"
            f"3. Step-by-step instructions for preparing the dish.\n"
            f"Ensure the output is well-structured."
        )

        response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a culinary expert generating ingredients, components, and instructions for dishes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=700,
        temperature=0.7)

        content = response.choices[0].message.content.strip()

        # Extract ingredients, components, and instructions using regex
        ingredients_match = re.search(r'Ingredients:(.*?)Components:', content, re.DOTALL)
        components_match = re.search(r'Components:(.*?)Instructions:', content, re.DOTALL)
        instructions_match = re.search(r'Instructions:(.*)', content, re.DOTALL)

        ingredients = ingredients_match.group(1).strip() if ingredients_match else "No ingredients found."
        components = components_match.group(1).strip() if components_match else "No components found."
        instructions = instructions_match.group(1).strip() if instructions_match else "No instructions found."

        return ingredients, components, instructions
    except Exception as e:
        app.logger.error(f"Error generating ingredients, components, and instructions: {e}")
        return None, None, None


# Step 4: Generate Dish Image
def generate_image(description):
    try:
        response = client.images.generate(prompt=description[:1000],  # Ensure the description is within 1000 characters
        n=1,
        size="256x256")
        image_url = response.data[0].url if response and 'data' in response else None
        return image_url
    except Exception as e:
        app.logger.error(f"Error generating image: {e}")
        return None


# Endpoint to Generate Dish
@app.route('/generate_dishes', methods=['POST'])
def generate_dishes():
    data = request.json
    idea = data.get("idea")
    style_influence = data.get("style_influence", {})

    if not idea:
        return jsonify({"error": "Idea is required"}), 400

    # Step 1: Generate description
    description = generate_description(idea, style_influence)
    if not description:
        return jsonify({"error": "Failed to generate description."}), 500

    # Step 2: Generate name
    name = generate_name(description)
    if not name:
        return jsonify({"error": "Failed to generate name."}), 500

    # Step 3: Generate ingredients, components, and instructions
    ingredients, components, instructions = generate_ingredients_components_instructions(description)
    if not ingredients or not components or not instructions:
        return jsonify({"error": "Failed to generate ingredients, components, or instructions."}), 500

    # Step 4: Generate image
    image_url = generate_image(description)
    if not image_url:
        return jsonify({"error": "Failed to generate image."}), 500

    return jsonify({
        "short_name": name,
        "menu_item_description": description,
        "ingredients": ingredients,
        "components": components,
        "instructions": instructions,
        "image_url": image_url
    })


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
