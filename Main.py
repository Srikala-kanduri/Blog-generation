# Import necessary libraries
import streamlit as st
from transformers import pipeline

# Initialize the text generation pipeline from Hugging Face's GPT model (e.g., GPT-2)
generator = pipeline('text-generation', model='gpt2')  # You can replace 'gpt2' with other models like 'EleutherAI/gpt-neo-2.7B' if needed

# Function to generate blog posts using Hugging Face's GPT model
def generate_blog(prompt):
    # Generate text using the model
    generated_text = generator(prompt, max_length=500, num_return_sequences=1)
    return generated_text[0]['generated_text'].strip()  # Extract the generated text

# Streamlit interface
def chatbot_blog_generator():
    st.title("AI Blog Generator")
    st.write("Enter a topic, and I will generate a blog post for you.")
    
    # User input for the topic
    topic = st.text_input("Enter Blog Topic:")
    
    # Button to trigger blog generation
    if st.button("Generate Blog"):
        if topic:
            prompt = f"Write a detailed blog post on the topic '{topic}'. The blog should be engaging, informative, and suitable for a general audience."
            blog_post = generate_blog(prompt)  # Generate the blog post using Hugging Face's model
            st.write("### Generated Blog Post:")
            st.write(blog_post)  # Display the generated blog post
        else:
            st.write("Please enter a topic to generate a blog.")

# Run the Streamlit app
if __name__ == "__main__":
    chatbot_blog_generator()
