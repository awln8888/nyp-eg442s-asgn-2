import os
import time
import requests
import psycopg2

from flask import Flask, render_template_string

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# --------------------------------------------------
# Database Functions
# --------------------------------------------------

def get_db_connection():
    """Connects to the database with a basic retry loop if it's still booting up."""
    retries = 5
    while retries > 0:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except psycopg2.OperationalError:
            retries -= 1
            time.sleep(2)
    raise Exception("Could not connect to the database")


def init_db():
    """Creates a dummy table and inserts a record if it doesn't exist yet."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    cur.execute('INSERT INTO visits DEFAULT VALUES;')
    conn.commit()
    cur.close()
    conn.close()

# --------------------------------------------------
# Data.gov.sg PM2.5 API
# --------------------------------------------------

def get_pm25_data():

    api_key = os.environ.get("DATA_GOV_SG_API_KEY")

    if not api_key:
        print("WARNING: DATA_GOV_SG_API_KEY not configured")
        return None

    url = "https://api-open.data.gov.sg/v2/real-time/api/pm25"

    headers = {
        "X-API-Key": api_key
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(f"PM25 API Error: {e}")
        return None


# --------------------------------------------------
# Route
# --------------------------------------------------

@app.route("/")
def home():

    api_key_present = bool(os.environ.get("DATA_GOV_SG_API_KEY"))
    
    
    # Record page visit
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO visits DEFAULT VALUES"
    )

    conn.commit()

    # Count total visits
    cur.execute(
        "SELECT COUNT(*) FROM visits"
    )

    total_visits = cur.fetchone()[0]

    cur.close()
    conn.close()

    # Get PM2.5 readings
    pm25_data = get_pm25_data()

    readings = {}

    if pm25_data:
        readings = (
            pm25_data["data"]["items"][0]
            ["readings"]["pm25_one_hourly"]
        )

    return render_template_string("""

<!DOCTYPE html>
<html>
<head>
    <title>Singapore PM2.5 Dashboard</title>

    <style>

        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f4f4f4;
        }

        h1 {
            color: #0078d4;
        }

        .card {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.1);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        table,
        th,
        td {
            border: 1px solid #ddd;
        }

        th {
            background-color: #0078d4;
            color: white;
        }

        th,
        td {
            padding: 12px;
            text-align: center;
        }

    </style>

</head>
<body>

    <h1>Singapore PM2.5 Dashboard</h1>

    <div class="card">

        <h2>Application Status</h2>

        <p>
            <strong>Message:</strong>
            Hello from Python inside Docker!
        </p>

        <p>
            <strong>Database Status:</strong>
            Connected
        </p>

        <p>
            <strong>Total Page Views:</strong>
            {{ visits }}
        </p>
        
        <p>
            <strong>API Key Loaded:</strong>
            {{ api_key_present }}
        </p>        

    </div>

    <div class="card">

        <h2>Current PM2.5 Readings</h2>

        <table>

            <tr>
                <th>Region</th>
                <th>PM2.5</th>
            </tr>

            <tr>
                <td>North</td>
                <td>{{ readings.get('north', 'N/A') }}</td>
            </tr>

            <tr>
                <td>South</td>
                <td>{{ readings.get('south', 'N/A') }}</td>
            </tr>

            <tr>
                <td>East</td>
                <td>{{ readings.get('east', 'N/A') }}</td>
            </tr>

            <tr>
                <td>West</td>
                <td>{{ readings.get('west', 'N/A') }}</td>
            </tr>

            <tr>
                <td>Central</td>
                <td>{{ readings.get('central', 'N/A') }}</td>
            </tr>

        </table>

    </div>

</body>
</html>

    """,
    visits=total_visits,
    api_key_present=api_key_present,
    readings=readings)


# --------------------------------------------------
# Application Startup
# --------------------------------------------------

init_db()

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )