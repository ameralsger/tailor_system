from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-change-me'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    employee = db.Column(db.String(50))
    work_type = db.Column(db.String(50))
    branch = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    client_code = db.Column(db.String(20))
    client_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    notes = db.Column(db.String(200))
    fabric_type = db.Column(db.String(50))
    color = db.Column(db.String(50))
    fabric_notes = db.Column(db.String(200))
    fabric_image = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    index = db.Column(db.Integer)
    value = db.Column(db.String(20))

def generate_order_number():
    return f"ORD-{random.randint(10000,99999)}"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="بيانات الدخول غير صحيحة")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/save", methods=["POST"])
def save():
    if "user_id" not in session:
        return redirect(url_for("login"))

    data = request.form.to_dict()
    file = request.files.get("fabric_image")
    filename = None

    if file and file.filename:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(path)

    order_number = generate_order_number()

    order = Order(
        order_number=order_number,
        employee=data.get("employee"),
        work_type=data.get("work_type"),
        branch=data.get("branch"),
        quantity=int(data.get("quantity", 1)),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        client_code=data.get("client_code"),
        client_name=data.get("client_name"),
        phone=data.get("phone"),
        notes=data.get("notes"),
        fabric_type=data.get("fabric_type"),
        color=data.get("color"),
        fabric_notes=data.get("fabric_notes"),
        fabric_image=filename
    )
    db.session.add(order)
    db.session.commit()

    for i in range(1, 20):
        val = data.get(f"m{i}")
        m = Measurement(order_id=order.id, index=i, value=val)
        db.session.add(m)

    db.session.commit()

    return redirect(url_for("invoice", order_id=order.id))

@app.route("/invoice/<int:order_id>")
def invoice(order_id):
    order = Order.query.get_or_404(order_id)
    measurements = Measurement.query.filter_by(order_id=order.id).order_by(Measurement.index).all()
    return render_template("invoice.html", order=order, measurements=measurements)

@app.route("/invoice/<int:order_id>/pdf")
def invoice_pdf(order_id):
    order = Order.query.get_or_404(order_id)
    measurements = Measurement.query.filter_by(order_id=order.id).order_by(Measurement.index).all()

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 12)
    y = 800

    p.drawString(50, y, f"فاتورة قياسات - رقم الطلب: {order.order_number}")
    y -= 30
    p.drawString(50, y, f"العميل: {order.client_name} - الجوال: {order.phone}")
    y -= 20
    p.drawString(50, y, f"الموظف: {order.employee} - الفرع: {order.branch}")
    y -= 20
    p.drawString(50, y, f"تاريخ التفصيل: {order.start_date} - التسليم: {order.end_date}")
    y -= 30

    p.drawString(50, y, "القياسات:")
    y -= 20
    for m in measurements:
        p.drawString(60, y, f"قياس {m.index}: {m.value}")
        y -= 15
        if y < 50:
            p.showPage()
            y = 800

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"invoice_{order.order_number}.pdf", mimetype='application/pdf')

if __name__ == "__main__":
    @app.route("/create_admin")
def create_admin():
    user = User(username="admin", password="1234")
    db.session.add(user)
    db.session.commit()
    return "Admin user created!"
    app.run(host="0.0.0.0", port=5000)
