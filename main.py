import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-desenvolvimento' # Troque por algo seguro em produção
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///imc.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Funções de Lógica (Originais) ---
def calcular_imc(peso, altura):
    imc = peso / (altura ** 2)
    return imc

def classificar_imc(imc):
    if imc < 18.5:
        return "Abaixo do peso"
    elif imc < 24.9:
        return "Peso normal"
    elif imc < 29.9:
        return "Sobrepeso"
    elif imc < 34.9:
        return "Obesidade grau I"
    elif imc < 39.9:
        return "Obesidade grau II"
    else:
        return "Obesidade grau III"

# --- Banco de Dados ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class IMCRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    peso = db.Column(db.Float, nullable=False)
    altura = db.Column(db.Float, nullable=False)
    imc = db.Column(db.Float, nullable=False)
    classificacao = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Templates HTML (Embutidos) ---
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calculadora IMC Web</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary mb-4">
        <div class="container">
            <a class="navbar-brand" href="/">IMC Tracker</a>
            <div>
                {% if current_user.is_authenticated %}
                    <span class="text-white me-3">Olá, {{ current_user.username }}</span>
                    <a href="/logout" class="btn btn-sm btn-light">Sair</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container">
        {% for message in get_flashed_messages() %}
            <div class="alert alert-info">{{ message }}</div>
        {% endfor %}
        {{ content|safe }}
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow">
            <div class="card-header text-center"><h4>Login</h4></div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3"><label>Usuário</label><input type="text" name="username" class="form-control" required></div>
                    <div class="mb-3"><label>Senha</label><input type="password" name="password" class="form-control" required></div>
                    <button class="btn btn-primary w-100">Entrar</button>
                </form>
                <div class="mt-3 text-center"><a href="/register">Criar nova conta</a></div>
            </div>
        </div>
    </div>
</div>
"""

REGISTER_TEMPLATE = """
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow">
            <div class="card-header text-center"><h4>Cadastro</h4></div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3"><label>Usuário</label><input type="text" name="username" class="form-control" required></div>
                    <div class="mb-3"><label>Senha</label><input type="password" name="password" class="form-control" required></div>
                    <button class="btn btn-success w-100">Cadastrar</button>
                </form>
                <div class="mt-3 text-center"><a href="/login">Já possui conta? Faça login</a></div>
            </div>
        </div>
    </div>
</div>
"""

DASHBOARD_TEMPLATE = """
<div class="row">
    <div class="col-md-4 mb-4">
        <div class="card h-100 shadow-sm">
            <div class="card-header">Novo Cálculo</div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3"><label>Peso (kg)</label><input type="number" step="0.1" name="peso" class="form-control" required></div>
                    <div class="mb-3"><label>Altura (m)</label><input type="number" step="0.01" name="altura" class="form-control" required></div>
                    <button class="btn btn-primary w-100">Calcular e Salvar</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-8 mb-4">
        <div class="card h-100 shadow-sm">
            <div class="card-header">Evolução do seu IMC</div>
            <div class="card-body"><canvas id="imcChart"></canvas></div>
        </div>
    </div>
</div>
<div class="card shadow-sm mt-4">
    <div class="card-header">Histórico Detalhado</div>
    <div class="card-body">
        <table class="table table-hover">
            <thead><tr><th>Data</th><th>Peso</th><th>Altura</th><th>IMC</th><th>Classificação</th></tr></thead>
            <tbody>
                {% for item in history %}
                <tr>
                    <td>{{ item.date.strftime('%d/%m/%Y %H:%M') }}</td>
                    <td>{{ item.peso }}</td>
                    <td>{{ item.altura }}</td>
                    <td><strong>{{ "%.2f"|format(item.imc) }}</strong></td>
                    <td>{{ item.classificacao }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
<script>
    new Chart(document.getElementById('imcChart'), {
        type: 'line',
        data: {
            labels: {{ dates|tojson }},
            datasets: [{
                label: 'IMC',
                data: {{ values|tojson }},
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                tension: 0.3,
                fill: true
            }]
        },
        options: { scales: { y: { suggestedMin: 15, suggestedMax: 40 } } }
    });
</script>
"""

# --- Rotas ---
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        try:
            peso = float(request.form.get('peso'))
            altura = float(request.form.get('altura'))
            imc = calcular_imc(peso, altura)
            classificacao = classificar_imc(imc)
            
            novo_registro = IMCRecord(peso=peso, altura=altura, imc=imc, classificacao=classificacao, user_id=current_user.id)
            db.session.add(novo_registro)
            db.session.commit()
            flash(f"IMC Calculado: {imc:.2f} - {classificacao}")
        except ValueError:
            flash("Erro: Verifique os valores digitados.")
        return redirect('/')

    history = IMCRecord.query.filter_by(user_id=current_user.id).order_by(IMCRecord.date).all()
    dates = [h.date.strftime('%d/%m') for h in history]
    values = [round(h.imc, 2) for h in history]
    
    content = render_template_string(DASHBOARD_TEMPLATE, history=history, dates=dates, values=values)
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect('/')
        flash('Usuário ou senha incorretos.')
    
    content = render_template_string(LOGIN_TEMPLATE)
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe.')
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            flash('Cadastro realizado! Faça login.')
            return redirect('/login')
            
    content = render_template_string(REGISTER_TEMPLATE)
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Cria o banco de dados na primeira execução
    app.run(debug=True)
