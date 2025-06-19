from flask import Flask, render_template_string
from tinydb import TinyDB
import os

app = Flask(__name__)

def get_db():
    db_path = os.path.join(os.path.dirname(__file__), '../data/transactions.json')
    return TinyDB(db_path)

@app.route('/')
def index():
    db = get_db()
    transactions = db.all()
    html = '''
    <html>
    <head>
        <title>Transactions TinyDB</title>
        <style>
            body { font-family: Arial, sans-serif; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 6px; text-align: left; }
            th { background: #eee; }
        </style>
    </head>
    <body>
        <h2>Transactions enregistrées</h2>
        <table>
            <tr>
                <th>#</th>
                <th>Date</th>
                <th>Token</th>
                <th>Symbole</th>
                <th>Valeur</th>
                <th>De</th>
                <th>À</th>
                <th>Hash</th>
            </tr>
            {% for tx in transactions %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ tx.get('date', '') }}</td>
                <td>{{ tx.get('tokenName', '') }}</td>
                <td>{{ tx.get('tokenSymbol', '') }}</td>
                <td>{{ tx.get('value', '') }}</td>
                <td>{{ tx.get('from', '') }}</td>
                <td>{{ tx.get('to', '') }}</td>
                <td style="font-size: 0.8em; word-break: break-all;">{{ tx.get('hash', '') }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, transactions=transactions)

if __name__ == '__main__':
    app.run(debug=True)
