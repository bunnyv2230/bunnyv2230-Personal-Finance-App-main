# 💰 Personal Finance Tracker & AI-Powered Analyzer

A comprehensive, state-of-the-art personal finance management application designed to help users effectively monitor, analyze, and manage their expenses. Leveraging advanced Machine Learning algorithms and Natural Language Processing (NLP), this app offers insightful expense clustering, anomaly detection, and predictive analytics, empowering users to make informed, data-driven financial decisions.

---

## 🚀 Key Features

### 1. Core Financial Trackers
* **Income Management:** Easily record and categorize multiple income streams (Salary, Freelance, Investments) to capture your full financial inflow.
* **Expense Logging:** Track expense details, amounts, categories, and descriptions with a modern, responsive user interface.
* **Financial Goal Setter:** Define clear savings goals. The system automatically incorporates historical leftover monthly salaries and displays real-time progress towards your funding targets.

### 2. AI-Powered Predictive Analytics & Anomaly Detection
* **LSTM Expense Prediction:** Forecast next month's total expenditures using a deep-learning Long Short-Term Memory (LSTM) network trained on your personal transaction patterns. Includes forecasted category-by-category breakdowns.
* **Anomalous Spend Detection:** Instantly flags unusual transactions or surprise spikes using **Isolation Forest** (statistical outliers) and **Neural Network Autoencoders** (reconstruction errors).
* **Personalized Savings Advice:** Recommends target savings allocations using Nearest Neighbors algorithm mapped to historical averages.

### 3. NLP-Driven Expense Clustering
* **Contextual Grouping:** Combines transaction monetary amounts, NLP sentiment score (using TextBlob), and LDA topic modeling features extracted from transaction descriptions.
* **Clustering Algorithms:** Dynamically cluster similar transactions using K-Means, Hierarchical (Agglomerative), and DBSCAN models to reveal hidden spending patterns.

### 4. Enterprise-Grade Security
* **Authentication:** Highly secure user onboarding and sign-in with Flask-Bcrypt hashed passwords.
* **Google OAuth 2.0 Integration:** Quick and secure login using active Google credentials.

---

## 🛠️ Project Architecture Overview

```
Personal-Finance-App-main/
├── app.py                      # Main lightweight launch entry point
├── models.py                   # Compatibility layer for auxiliary scripts
├── ml_model.py                 # Core AI/ML training & prediction engines
├── personal_finance.db         # Active SQLite relational database
├── generate_test_data.py       # Command Line interface to generate mock data
├── gui.py                      # Standalone TKinter desktop application
├── static/                     # Styling (CSS), scripts, and uploaded media
├── templates/                  # Frontend HTML templates
│
└── finance_app/                # Core Web App Backend (Refactored Package)
    ├── __init__.py             # Application Factory initialization (create_app)
    ├── config.py               # Central configurations (secrets, db URIs)
    ├── extensions.py           # Declares database, Bcrypt, and OAuth
    ├── helpers.py              # salary leftovers and database helpers
    ├── models.py               # Core SQLAlchemy models & controllers
    └── routes/                 # Isolated domain route registries
        ├── auth.py             # Auth & Profile APIs
        ├── expenses.py         # Expense Trackers
        ├── goals.py            # Goal managers
        ├── income.py           # Income logger
        ├── ml.py               # ML analytical routes
        └── main.py             # Dashboard homepage & APIs
```

---

## 💻 Installation & Quickstart

### Prerequisites
- Python 3.9, 3.10, or 3.11 installed on your system.

### 1. Clone & Set Up Directory
Navigate to the directory in your shell of choice:
```bash
cd Personal-Finance-App-main
```

### 2. Install Dependencies
Install all required libraries including web engines, ML frameworks (TensorFlow, scikit-learn), and NLP parsers:
```bash
pip install flask flask-sqlalchemy flask-bcrypt authlib pandas numpy scikit-learn tensorflow textblob
```

### 3. Create Environmental Variables (Optional)
For Google OAuth, configure a `.env` file at the root directory:
```env
FLASK_SECRET_KEY=your_super_secret_key_123
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### 4. Populate Testing Data
To immediately explore the Machine Learning analytical graphs, run the test data generator CLI to ingest realistic mock transactions spanning the past 6 months:
```bash
python generate_test_data.py
```

### 5. Launch the Web Application
Start the Flask application server:
```bash
python app.py
```
Open your browser and navigate to **`http://127.0.0.1:5000`** to log in, register, and explore your personal finance dashboard!

---

## 🖥️ Alternative Clients (Desktop GUI)

If you prefer a native desktop workspace instead of the web browser, launch the desktop client:
```bash
python gui.py
```
*(Requires `tkinter` support built-in with your Python installation)*.
