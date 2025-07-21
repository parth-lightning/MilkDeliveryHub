# DairyDash Connect

A web application for managing a dairy delivery service, built with Flask. DairyDash Connect streamlines the process for both customers and milkmen, enabling easy order management, delivery tracking, and payments.

## Features

- **Customer & Milkman Registration/Login**
- **Customer Dashboard**: View orders, update milk preferences, see delivery calendar, manage profile, and make payments.
- **Milkman Dashboard**: View customer orders for selected dates, mark deliveries, upload UPI QR for payments, and manage customer list.
- **Order Management**: Customers can set daily milk preferences, place/cancel orders, and view order history.
- **Delivery Tracking**: Calendar view for customers, daily order list for milkmen, and delivery marking.
- **Payment Calculation**: Customers can view outstanding dues and pay via UPI QR code.
- **Profile Management**: Customers can update address and linked milkman.

## Tech Stack

- **Backend**: Python, Flask
- **Database**: SQLite
- **Frontend**: Jinja2 HTML templates, CSS
- **Static Assets**: Images, CSS

## Folder Structure

```
.
├── app.py                  # Main Flask application
├── dairy_dash.db           # SQLite database file
├── templates/              # HTML templates (Jinja2)
├── static/
│   ├── css/
│   │   └── style.css       # Main stylesheet
│   └── images/             # Image assets (QR, dairy-farm, etc.)
├── public/                 # Favicon, robots.txt, placeholder SVG
├── test.py                 # (Unrelated) Number conversion script
├── package.json            # (Unused) Node.js dependencies (Flask listed by mistake)
├── package-lock.json       # (Unused) Node.js lockfile
├── vite.config.js          # (Unused) Vite config (for static assets/dev server)
└── README.md               # Project documentation
```

## Setup Instructions

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Installation
1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd dairy-replica-web-main
   ```
2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install flask werkzeug
   ```
4. **Run the application:**
   ```bash
   python app.py
   ```
5. **Access the app:**
   Open your browser and go to [http://localhost:5000](http://localhost:5000)

### Notes
- The app will auto-create the SQLite database (`dairy_dash.db`) and required tables on first run.
- Static files (images, CSS) are served from the `static/` directory.
- The `package.json` and `vite.config.js` are not required for running the Flask app.

## Usage
- Register as a customer or milkman.
- Customers can set milk preferences, place/cancel orders, view delivery calendar, and pay dues.
- Milkmen can view daily orders, mark deliveries, upload UPI QR, and manage customers.

## License
[MIT](LICENSE)

---
