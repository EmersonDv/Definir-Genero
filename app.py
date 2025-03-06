from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import pandas as pd
import requests
import time
from io import BytesIO
from datetime import datetime

# Configuración de Flask
app = Flask(__name__, static_folder='frontend/static', template_folder='frontend/templates')

# Conectar a la base de datos SQLite (o crearla si no existe)
conn = sqlite3.connect('gender_cache.db', check_same_thread=False)
cursor = conn.cursor()
print("Base de datos SQLite creada correctamente.")

# Crear la tabla de caché si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS gender_cache (
    name TEXT PRIMARY KEY,
    gender TEXT
)
''')

# Crear la tabla para el contador de solicitudes si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS api_requests (
    date TEXT PRIMARY KEY,
    count INTEGER
)
''')
conn.commit()

# Función para obtener el contador de solicitudes del día actual
def get_request_count():
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT count FROM api_requests WHERE date = ?', (today,))
    result = cursor.fetchone()
    return result[0] if result else 0

# Función para incrementar el contador de solicitudes
def increment_request_count():
    today = datetime.now().strftime('%Y-%m-%d')
    count = get_request_count()
    if count == 0:
        cursor.execute('INSERT INTO api_requests (date, count) VALUES (?, ?)', (today, 1))
    else:
        cursor.execute('UPDATE api_requests SET count = ? WHERE date = ?', (count + 1, today))
    conn.commit()

# Función para obtener el género desde la caché o la API
def get_gender(name):
    # Buscar en la caché
    cursor.execute('SELECT gender FROM gender_cache WHERE name = ?', (name,))
    result = cursor.fetchone()
    if result:
        return result[0]  # Devolver el género desde la caché

    # Si no está en la caché, llamar a la API
    increment_request_count()  # Incrementar el contador de solicitudes
    url = f"https://api.genderize.io/?name={name}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        gender = data.get('gender')
        if gender == 'female':
            gender = 'F'  # Femenino
        elif gender == 'male':
            gender = 'M'  # Masculino
        else:
            gender = 'Unknown'  # Si no se puede determinar el género

        # Guardar en la caché
        cursor.execute('INSERT OR REPLACE INTO gender_cache (name, gender) VALUES (?, ?)', (name, gender))
        conn.commit()

        return gender
    return 'Unknown'

# Ruta principal
@app.route('/')
def index():
    request_count = get_request_count()
    return render_template('index.html', request_count=request_count)

# Ruta para subir archivos
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'excelFile' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['excelFile']
    df = pd.read_excel(file)

    # Verifica si la columna 'Nombre' existe
    if 'Nombre' not in df.columns:
        return jsonify({'error': "La columna 'Nombre' no existe en el archivo."}), 400

    # Extraer el primer nombre
    df['Nombre'] = df['Nombre'].apply(lambda x: x.split()[0])

    # Procesar en lotes de 10 nombres con un retraso de 1 segundo entre lotes
    batch_size = 10
    total_rows = len(df)
    df['Genero'] = ''  # Inicializar la columna de género

    for i in range(0, total_rows, batch_size):
        batch = df['Nombre'][i:i + batch_size]
        df.loc[i:i + batch_size - 1, 'Genero'] = [get_gender(name) for name in batch]
        print(f"Procesados {min(i + batch_size, total_rows)} de {total_rows} registros.")
        time.sleep(1)  # Espera 1 segundo entre lotes

    # Guardar el archivo procesado en un objeto BytesIO
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    # Enviar el archivo como respuesta para descargar
    return send_file(
        output,
        as_attachment=True,
        download_name='processed_file.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# Ruta para obtener el contador de solicitudes
@app.route('/get_request_count', methods=['GET'])
def get_request_count_route():
    return jsonify({'request_count': get_request_count()})

# Iniciar la aplicación
if __name__ == '__main__':
    app.run(debug=True)