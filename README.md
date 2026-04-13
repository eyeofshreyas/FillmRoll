<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-Web_App-black?logo=flask" />
  <img src="https://img.shields.io/badge/Firebase-Firestore-FFCA28?logo=firebase&logoColor=black" />
  <img src="https://img.shields.io/badge/TMDB-API-01d277?logo=themoviedatabase&logoColor=white" />
  <img src="https://img.shields.io/badge/Llama_3.1-AI_Chat-blueviolet?logo=huggingface&logoColor=white" />
  <img src="https://img.shields.io/badge/Google-OAuth2-4285F4?logo=google&logoColor=white" />
</p>

# 🎬 FilmRoll — AI Movie Recommendation System

FilmRoll is a modern, full-stack movie recommendation engine featuring a cinematic dark-themed web UI. It goes beyond simple recommendations by offering **Collaborative Filtering**, **Google OAuth**, **Firebase Cloud Storage**, and a **Llama 3.1 AI Chat Assistant** powered by Hugging Face to help you discover your next favorite movie.

---

## ✨ Features

- **Personal Watchlists & Streaming Providers** — Save movies to your personal watchlist and instantly see *where* you can stream them (Netflix, Hulu, Prime Video, etc.) without leaving the app.
- **Collaborative Filtering & Content-Based ML** — Recommends movies using a hybrid approach. It utilizes TF-IDF vectorization/cosine similarity for content matching, combined with user ratings from your active session.
- **Google OAuth Authentication** — Seamless and secure Single Sign-On (SSO) utilizing `authlib` to manage user sessions.
- **Firebase Firestore Integration** — Persistently stores user ratings and mood history across sessions using a robust NoSQL cloud database.
- **Llama 3.1 AI Chat Assistant** — Context-aware movie assistant powered by the Hugging Face Inference API. Describe a movie in plain English, and the AI will find the closest match.
- **Automatic Matrix Download** — The application automatically fetches the hefty mathematical similarity matrix from the Hugging Face Hub on startup, saving you local storage space and setup time.
- **Cinematic UI** — Dark-themed, responsive frontend with smooth animations, hover effects, a hero landing page, and a trending carousel.
- **Movie Details Modal** — Watch YouTube trailers, browse the cast list, check runtime, genres, and taglines — all fetched live from the TMDB API.

---

## 🛠️ Tech Stack

- **Backend Framework** — Python, Flask, Gunicorn
- **Database / Auth** — Google Firebase Admin SDK (Firestore), Google OAuth 2.0
- **Machine Learning & NLP** — scikit-learn (CountVectorizer, Cosine Similarity), NLTK (Porter Stemmer), Pandas, NumPy
- **External APIs** — [TMDB API v3](https://developers.themoviedb.org/3) for live posters, streaming providers, and trailers. 
- **AI / LLM** — `meta-llama/Llama-3.1-8B-Instruct` via the [Hugging Face Serverless Inference API](https://huggingface.co/docs/api-inference)
- **Frontend** — HTML5, CSS3 (Vanilla + Animations), JavaScript

---

## 📂 Project Structure

```text
FillmRoll/
├── app.py                          # Main Flask application, API endpoints, and Auth integration
├── db.py                           # Firebase initialization and database operations
├── requirements.txt                # Python dependencies for deployment
├── Procfile / runtime.txt          # Heroku deployment configuration files
├── movie-recommender-system.ipynb  # Jupyter notebook covering model creation and ML logic
├── static/
│   ├── styles.css                  # UI styling, responsive design, dark mode aesthetics
│   └── scripts.js                  # Frontend logic (modals, TMDB fetching, Watchlist, AI Chat)
└── templates/
    ├── index.html                  # Main application interface
    └── login.html                  # Google OAuth login landing page
```

> **Note**: `movies_dict.pkl` and `similarity.pkl` are required for ML functionality. `similarity.pkl` is automatically downloaded from the cloud on the first run.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A Google Cloud Platform (GCP) Project with OAuth credentials.
- A Firebase Project with Firestore enabled.
- Hugging Face Access Token.
- *(Note: A TMDB API key is currently embedded in the code for demonstration).*

### 1. Environment Variables Setup

Create a `.env` file in the root directory and add the following keys:

```env
FLASK_SECRET=your_secure_flask_secret_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
FIREBASE_CREDENTIALS_BASE64=base64_encoded_version_of_your_firebase_service_account_json
HF_TOKEN=hf_your_huggingface_access_token
```

### 2. Installation & Running Locally

```bash
# Clone the repository
git clone https://github.com/shreyass0007/FillmRoll.git
cd FillmRoll

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt

# Start the Flask application
python app.py
```

The app will download the required similarity matrices and start a server at **http://127.0.0.1:5000**. 

---

## ☁️ Deployment (Heroku)

This application is configured for easy deployment on Heroku. The included `Procfile` uses `gunicorn` as the web server, and `runtime.txt` specifies Python 3.12.9.

1. Create a new Heroku app.
2. Add all of the `.env` variables from Step 1 to your Heroku **Config Vars** in the dashboard.
3. Push your code to the Heroku remote:
   ```bash
   git push heroku main
   ```
4. *Important:* Due to the size of the similarity matrix downloading on the first boot, you may need to increase the Heroku boot timeout window via the Heroku CLI if you run into `R10` errors.

---

## 📸 Experience the App

> Start the app, log in with Google, and experience the full cinematic UI. Try asking the AI bot, "Find me a movie about a bank heist that goes wrong", save movies to your watchlist, and rate your favorites to improve the Collaborative Filtering results.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request on GitHub.

---

## 📜 License

This project is open-source and available under the [MIT License](LICENSE).

<p align="center">
  Built with ❤️ using Flask, TMDB, Firebase & Llama 3.1
</p>
