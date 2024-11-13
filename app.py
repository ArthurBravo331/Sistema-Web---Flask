from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import check_password_hash
from flask_login import UserMixin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Função para gerar um PDF para um veículo específico
@app.route('/relatorio/veiculo/<int:id>', methods=['GET'])
def download_vehicle_report(id):
    vehicle = Vehicle.query.get(id)
    if not vehicle:
        flash("Veículo não encontrado.", "danger")
        return redirect(url_for('paginaInicial'))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    p = canvas.Canvas(buffer, pagesize=A4)
    p.drawString(100, 770, f"Gerado por: {current_user.name} ({current_user.email})")
    p.drawString(100, 720, f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, 750, f"Relatório do Veículo - ID: {vehicle.id}")
    p.drawString(100, 730, f"Placa: {vehicle.license_plate}")
    p.drawString(100, 710, f"Vaga: {vehicle.parking_spot}")
    p.drawString(100, 690, f"Entrada: {vehicle.entry_time}")
    p.drawString(100, 670, f"Saída: {vehicle.exit_time}")
    p.drawString(100, 650, f"Tarifa: {vehicle.tariff}")
    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"relatorio_veiculo_{vehicle.license_plate}.pdf", mimetype='application/pdf')

# Função para gerar um PDF com todos os veículos registrados
@app.route('/relatorio/todos', methods=['GET'])
def download_all_reports():
    vehicles = Vehicle.query.all()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.drawString(100, 800, "Relatório Completo de Veículos")

    y_position = 780
    for vehicle in vehicles:
        p.drawString(100, y_position, f"ID: {vehicle.id} - Placa: {vehicle.license_plate}, Vaga: {vehicle.parking_spot}, Entrada: {vehicle.entry_time}, Saída: {vehicle.exit_time}, Tarifa: {vehicle.tariff}")
        p.drawString(100, 700, f"Gerado por: {current_user.name} ({current_user.email})")
        y_position -= 20
        if y_position < 100:  # Adiciona nova página se o espaço vertical acabar
            p.showPage()
            y_position = 780

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="relatorio_completo_veiculos.pdf", mimetype='application/pdf')

# Modelos de dados
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), unique=True)
    entry_time = db.Column(db.DateTime, default=datetime.now)
    exit_time = db.Column(db.DateTime, nullable=True)
    parking_spot = db.Column(db.Integer)
    tariff = db.Column(db.Float)

# Criação do banco de dados
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rota de cadastro de usuário
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Conta criada com sucesso!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Credenciais inválidas', 'danger')
    return render_template('login.html')

# Rota para logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Página principal de gerenciamento
@app.route('/')
@login_required
def home():
    vehicles = Vehicle.query.all()
    return render_template('home.html', vehicles=vehicles)

# Rota para adicionar veículo
@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        license_plate = request.form.get('license_plate')
        parking_spot = request.form.get('parking_spot')
        tariff = 5.00  # Tarifa inicial para cálculo
        new_vehicle = Vehicle(license_plate=license_plate, parking_spot=parking_spot, tariff=tariff)
        db.session.add(new_vehicle)
        db.session.commit()
        flash('Veículo adicionado com sucesso', 'success')
        return redirect(url_for('home'))
    return render_template('add_vehicle.html')

# Rota para editar veículo
@app.route('/edit_vehicle/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    if request.method == 'POST':
        vehicle.license_plate = request.form.get('license_plate')
        vehicle.exit_time = datetime.now()  # Atualiza saída ao editar
        vehicle.tariff = request.form.get('tariff')
        db.session.commit()
        flash('Veículo atualizado', 'success')
        return redirect(url_for('home'))
    return render_template('edit_vehicle.html', vehicle=vehicle)

# Rota para deletar veículo
@app.route('/delete_vehicle/<int:id>')
@login_required
def delete_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    db.session.delete(vehicle)
    db.session.commit()
    flash('Veículo removido', 'success')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
