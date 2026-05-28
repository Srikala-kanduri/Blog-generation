# Deploying the Blog Generator

This project is a Streamlit app. The main entry point is `main.py`.

## 1. Set up secrets locally

Create `.streamlit/secrets.toml` from the example file:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
PEXELS_API_KEY = "your_pexels_api_key_here"
```

Do not commit `.streamlit/secrets.toml`.

## 2. Run locally

```powershell
pip install -r requirements.txt
streamlit run main.py
```

## 3. Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Go to `https://share.streamlit.io`.
3. Create a new app.
4. Select the repository, branch, and set the main file path to `main.py`.
5. In Advanced settings, add these secrets:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
PEXELS_API_KEY = "your_pexels_api_key_here"
```

6. Deploy the app.

## 4. Deploy on Render

Use these settings:

- Service type: Web Service
- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run main.py --server.port $PORT --server.address 0.0.0.0`

Add `GROQ_API_KEY` and `PEXELS_API_KEY` as environment variables in Render.
