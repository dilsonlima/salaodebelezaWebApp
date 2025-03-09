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
        # Tabela de agendamentos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                service_description TEXT NOT NULL,
                service_value REAL NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                recurrence TEXT NOT NULL,
                color TEXT NOT NULL,
                pago BOOLEAN DEFAULT 0
            )
        ''')
        # Tabela de contas a pagar
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                due_date TEXT NOT NULL,
                value REAL NOT NULL,
                pago BOOLEAN DEFAULT 0
            )
        ''')
        conn.commit()
init_db()

#Adicionar nova rota para resumo do dia
from datetime import datetime, time

@app.route('/')
def index():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT * FROM appointments WHERE date = ? ORDER BY start_time', (today,))
            appointments = cursor.fetchall()

            # Remove agendamentos com horários já passados
            current_time = datetime.now().time()
            filtered_appointments = []
            for appointment in appointments:
                appointment_time = datetime.strptime(appointment[5], '%H:%M').time()  # appointment[5] é o start_time
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
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        recurrence = request.form['recurrence']
        pago = 0

        # Define a cor baseada no mês
        month = datetime.strptime(date, '%Y-%m-%d').month
        colors = ['#FFB6C1', '#FF69B4', '#FF1493', '#C71585']
        color = colors[(month - 1) % len(colors)]

        # Insere o agendamento e suas recorrências
        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                if recurrence == '1x':
                    # Insere apenas uma vez
                    cursor.execute('''
                        INSERT INTO appointments (client_name, service_description, service_value, date, start_time, end_time, recurrence, color,pago)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (client_name, service_description, service_value, date, start_time, end_time, recurrence, color,pago))
                else:
                    # Insere as recorrências
                    for i in range(4):
                        new_date = calculate_recurrence_date(date, recurrence, i)
                        cursor.execute('''
                            INSERT INTO appointments (client_name, service_description, service_value, date, start_time, end_time, recurrence, color,pago)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (client_name, service_description, service_value, new_date.strftime('%Y-%m-%d'), start_time, end_time, recurrence, color,pago))
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
            cursor.execute('SELECT * FROM appointments ORDER BY date, start_time')  # Substitua 'time' por 'start_time'
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

#rota para calcular o pago
from flask import jsonify  # Certifique-se de que jsonify está importado

@app.route('/update_payment_status', methods=['POST'])
def update_payment_status():
    try:
        data = request.get_json()
        if not data or 'appointmentIds' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

        appointment_ids = data['appointmentIds']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            if appointment_ids:
                # Marca como pago os agendamentos selecionados
                cursor.execute(
                    'UPDATE appointments SET pago = 1 WHERE id IN ({})'.format(
                        ','.join(['?'] * len(appointment_ids))
                    ), appointment_ids)
                # Marca como não pago os agendamentos não selecionados
                cursor.execute(
                    'UPDATE appointments SET pago = 0 WHERE id NOT IN ({})'.format(
                        ','.join(['?'] * len(appointment_ids))
                    ), appointment_ids)
            else:
                # Se nenhum ID for enviado, marca todos como não pagos
                cursor.execute('UPDATE appointments SET pago = 0')
            conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        print(f"Erro ao atualizar o status de pagamento: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    

#Rota para exlusao
@app.route('/delete_appointment/<int:appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Exclui o agendamento com o ID fornecido
            cursor.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
            print(f"Erro ao excluir o agendamento: {e}")
    return jsonify({'success': False, 'error': str(e)}), 500

#Rota para contas a pagar
@app.route('/bills')
def view_bills():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bills ORDER BY due_date')
            bills = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
        bills = []

    return render_template('bills.html', bills=bills)

#Rota para adicionar nova conta
@app.route('/add_bill', methods=['GET', 'POST'])
def add_bill():
    if request.method == 'POST':
        description = request.form['description']
        due_date = request.form['due_date']
        value = request.form['value']

        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO bills (description, due_date, value)
                    VALUES (?, ?, ?)
                ''', (description, due_date, value))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Erro no banco de dados: {e}")

        return redirect(url_for('view_bills'))

    return render_template('add_bill.html')

#Rota para atualizar o status de pagamento
@app.route('/update_bill_payment_status', methods=['POST'])
def update_bill_payment_status():
    try:
        data = request.get_json()
        if not data or 'billIds' not in data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

        bill_ids = data['billIds']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            if bill_ids:
                cursor.execute(
                    'UPDATE bills SET pago = 1 WHERE id IN ({})'.format(
                        ','.join(['?'] * len(bill_ids))
                    ), bill_ids)
            cursor.execute(
                'UPDATE bills SET pago = 0 WHERE id NOT IN ({})'.format(
                    ','.join(['?'] * len(bill_ids)) if bill_ids else '1=1'
                ), bill_ids if bill_ids else [])
            conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        print(f"Erro ao atualizar o status de pagamento: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    #Rota para excluir uma conta
    @app.route('/delete_bill/<int:bill_id>', methods=['DELETE'])
    def delete_bill(bill_id):
        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM bills WHERE id = ?', (bill_id,))
            conn.commit()
            return jsonify({'success': True})
        except Exception as e:
        
            print(f"Erro ao excluir a conta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)
