# Web Scraper

This project is a research-oriented web scraper designed to find and present unique, high-quality information from the web on a given topic.

---

## How to Run

### 1. Clone the Repository
git clone https://github.com/cadelxd/Web-Scraper.git<br>
cd Web-Scraper<br>

### 2. Create and Activate Virtual Environment
python -m venv venv<br>
venv\Scripts\activate<br>

### 3. Install Dependencies
pip install -r requirements.txt

### 4. Apply Migrations
python manage.py makemigrations<br>
python manage.py migrate

### 5. Run the Development Server
python manage.py runserver

### 6. Access the App
visit: http://localhost:8000