import streamlit as st
import requests
import plotly.graph_objects as go

# Configure Streamlit page
st.set_page_config(page_title="Dish Generator", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 40px; font-weight: bold; text-align: center; color: #2E8B57; margin-bottom: 20px; }
    .slider-label { margin-top: 10px; font-weight: bold; color: #2E8B57; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">DISH GENERATOR</div>', unsafe_allow_html=True)

# Top section with two columns
top_left, top_right = st.columns([3, 2])

with top_left:
    # User input
    dish_idea = st.text_area("Enter dish idea (max 500 characters):", height=150, max_chars=500)

    # Style sliders
    style_labels = ['Modernist', 'Deconstructed', 'Rustic', 'Comfort', 'Molecular Gastronomy']
    style_values = {label: st.slider(label, 0, 10, 5) for label in style_labels}

    # Radar chart
    def radar_chart(values, labels):
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values, theta=labels, fill='toself'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
        return fig
    st.plotly_chart(radar_chart(list(style_values.values()), style_labels))

with top_right:
    st.markdown("### Generated Image")
    image_placeholder = st.empty()

# Generate button
if st.button("Generate Dishes"):
    if not dish_idea:
        st.error("Enter a valid dish idea.")
    else:
        data = {"idea": dish_idea, "style_influence": style_values}
        try:
            with st.spinner("Generating your dish..."):
                response = requests.post("http://localhost:5000/generate_dishes", json=data)

            if response.status_code == 200:
                result = response.json()
                st.subheader(result["short_name"])
                st.write(result["menu_item_description"])

                # Ingredients and instructions dropdowns
                with st.expander("Ingredients", expanded=True):
                    ingredients = result["ingredients"].split('\n')
                    for item in ingredients:
                        st.write(f"- {item}")

                with st.expander("Instructions", expanded=True):
                    st.write(result["instructions"])

                # Display generated image
                if result["image_url"]:
                    image_placeholder.image(result["image_url"], caption="Generated Dish Image")
                else:
                    st.warning("No image was generated.")
            else:
                st.error(f"Error {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            st.error(f"Error communicating with Flask API: {e}")
