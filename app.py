from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # Para cálculos de recorrência mensal

app = Flask(__name__)
DATABASE = 'database.db'

# Inicializa o banco de dados
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                service_description TEXT NOT NULL,
                service_value REAL NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                recurrence TEXT NOT NULL,
                color TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

# Rota principal
@app.route('/')
def index():
    return render_template('index.html')

# Rota para adicionar agendamento
@app.route('/add', methods=['GET', 'POST'])
def add_appointment():
    if request.method == 'POST':
        client_name = request.form['client_name']
        service_description = request.form['service_description']
        service_value = request.form['service_value']
        date = request.form['date']
        time = request.form['time']
        recurrence = request.form['recurrence']

        # Define a cor baseada no mês
        month = datetime.strptime(date, '%Y-%m-%d').month
        colors = ['#FFB6C1', '#FF69B4', '#FF1493', '#C71585']
        color = colors[(month - 1) % len(colors)]

        # Insere o agendamento e suas recorrências
        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                for i in range(4):
                    new_date = calculate_recurrence_date(date, recurrence, i)
                    cursor.execute('''
                        INSERT INTO appointments (client_name, service_description, service_value, date, time, recurrence, color)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (client_name, service_description, service_value, new_date.strftime('%Y-%m-%d'), time, recurrence, color))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Erro no banco de dados: {e}")

        return redirect(url_for('view_appointments'))

    return render_template('add_appointment.html')

# Função para calcular a data de recorrência
def calculate_recurrence_date(start_date, recurrence, iteration):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if recurrence == '1x':
        return start_date
    elif recurrence == '1 a cada 15 dias':
        return start_date + timedelta(days=15 * iteration)
    elif recurrence == 'toda semana':
        return start_date + timedelta(weeks=iteration)
    elif recurrence == 'todo mês':
        return start_date + relativedelta(months=iteration)
    return start_date

# Rota para visualizar agendamentos
@app.route('/view')
def view_appointments():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM appointments ORDER BY date, time')
            appointments = cursor.fetchall()

            # Agrupa os agendamentos por mês e calcula a soma dos valores
            grouped_appointments = {}
            colors = ['#FFB6C1', '#FF69B4', '#FF1493', '#C71585']  # Cores para cada mês
            for appointment in appointments:
                date = datetime.strptime(appointment[4], '%Y-%m-%d')  # appointment[4] é a data
                month_year = date.strftime('%Y-%m')  # Formato: "2023-10"
                month_name = date.strftime('%B %Y')  # Formato: "October 2023"
                service_value = float(appointment[3])  # appointment[3] é o valor do serviço

                if month_year not in grouped_appointments:
                    grouped_appointments[month_year] = {
                        'month_name': month_name,
                        'color': colors[(date.month - 1) % len(colors)],  # Cor baseada no mês
                        'total_value': 0.0,  # Inicializa a soma dos valores
                        'appointments': []
                    }

                grouped_appointments[month_year]['total_value'] += service_value
                grouped_appointments[month_year]['appointments'].append(appointment)

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
        grouped_appointments = {}

    return render_template('view_appointments.html', grouped_appointments=grouped_appointments)

if __name__ == '__main__':
    app.run(debug=True)
