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

#cria banco de dados pago
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
                color TEXT NOT NULL,
                pago BOOLEAN DEFAULT 0  -- Novo campo (0 = não pago, 1 = pago)
            )
        ''')
        conn.commit()

#Adicionar nova rota para resumo do dia
from datetime import datetime, time

@app.route('/')
def index():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT * FROM appointments WHERE date = ? ORDER BY time', (today,))
            appointments = cursor.fetchall()

            # Remove agendamentos com horários já passados
            current_time = datetime.now().time()
            filtered_appointments = []
            for appointment in appointments:
                appointment_time = datetime.strptime(appointment[5], '%H:%M').time()  # appointment[5] é a hora
                if appointment_time >= current_time:
                    filtered_appointments.append(appointment)

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
        filtered_appointments = []

    return render_template('index.html', appointments=filtered_appointments)

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
    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
        appointments = []

    return render_template('view_appointments.html', appointments=appointments)


#rota para calcular o pago
@app.route('/update_payment_status', methods=['POST'])
def update_payment_status():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Obtém todos os IDs dos agendamentos
            cursor.execute('SELECT id FROM appointments')
            all_ids = [row[0] for row in cursor.fetchall()]

            # Obtém os IDs dos agendamentos marcados como pagos
            paid_ids = request.form.getlist('pago')

            # Atualiza o status de pagamento
            for appointment_id in all_ids:
                pago = 1 if str(appointment_id) in paid_ids else 0
                cursor.execute('UPDATE appointments SET pago = ? WHERE id = ?', (pago, appointment_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")

    return redirect(url_for('view_appointments'))


if __name__ == '__main__':
    app.run(debug=True)
