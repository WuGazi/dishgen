import streamlit as st
import requests
import plotly.graph_objects as go

# Set up the page configuration
st.set_page_config(page_title="Dish Generator", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
    .main-title {
        font-size: 40px;
        font-weight: bold;
        text-align: center;
        color: #2E8B57;
        margin-bottom: 20px;
    }
    .input-container {
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .slider-label {
        margin-top: 10px;
        font-weight: bold;
        color: #2E8B57;
    }
    </style>
    """, unsafe_allow_html=True)

# Main title
st.markdown('<div class="main-title">DISH GENERATOR</div>', unsafe_allow_html=True)

# Create a two-column layout
left_column, right_column = st.columns([3, 2])

# Left Column Layout
with left_column:
    # Input box for dish idea
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    dish_idea = st.text_area(
        "Enter dish idea, ingredients, style, etc. (max 500 characters):",
        height=150, max_chars=500
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Influencers sliders
    st.markdown('<div class="slider-title">Influencers</div>', unsafe_allow_html=True)

    style_labels = ['Modernist', 'Deconstructed', 'Rustic', 'Comfort', 'Molecular Gastronomy']
    style_columns = st.columns(len(style_labels))

    # Sliders for style influences
    style_values = {}
    for col, label in zip(style_columns, style_labels):
        with col:
            st.markdown(f'<div class="slider-label">{label}</div>', unsafe_allow_html=True)
            style_values[label] = st.slider(
                f"{label} Influence", 0, 10, 5, key=label, label_visibility="collapsed"
            )

# Right Column Layout for Radar Graph
with right_column:
    values = list(style_values.values())

    def create_radar_chart(values, labels):
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=labels,
            fill='toself',
            name='Style Influence'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10])
            ),
            showlegend=False,
            margin=dict(t=20, r=20, b=20, l=20)  # Compact layout
        )
        return fig

    # Display radar chart
    radar_chart = create_radar_chart(values, style_labels)
    st.plotly_chart(radar_chart, use_container_width=True)

# Generate button
if st.button("Generate Dishes"):
    if not dish_idea:
        st.error("Please enter a dish idea.")
    else:
        # Prepare data for the POST request
        style_influence = {label: value for label, value in style_values.items()}
        data = {
            "idea": dish_idea,
            "style_influence": style_influence
        }

        try:
            # Use Render-hosted Flask API URL
            api_url = "https://dishgen.onrender.com/generate_dishes"
            response = requests.post(api_url, json=data)

            if response.status_code == 200:
                result = response.json()

                # Display the generated dish details
                st.subheader("Generated Dish")

                # Short Name
                st.markdown("**Short Name (Inspired by Classical Dishes):**")
                st.write(result.get("short_name", "No name generated"))

                # Menu Item Description
                st.markdown("**Menu Item Description:**")
                st.write(result.get("menu_item_description", "No description generated"))

                # Ingredients
                st.markdown("**Ingredients:**")
                ingredients = result.get("ingredients", "No ingredients provided.")
                if isinstance(ingredients, str):
                    ingredients = ingredients.split('\n')
                for ingredient in ingredients:
                    st.write(f"- {ingredient}")

                # Components
                st.markdown("**Components:**")
                components = result.get("components", "No components provided.")
                if isinstance(components, str):
                    components = components.split('\n')
                for component in components:
                    st.write(f"- {component}")

                # Instructions
                st.markdown("**Instructions:**")
                instructions = result.get("instructions", "No instructions provided.")
                st.write(instructions)

                # Dish Image
                st.markdown("**Picture:**")
                image_url = result.get("image_url")
                if image_url and image_url != "Image generation failed.":
                    st.image(image_url, caption="Generated Dish Image")
                else:
                    st.warning("Image generation failed.")

            else:
                st.error(f"Failed to generate dishes. Error {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            st.error(f"Error communicating with Flask API: {e}")
