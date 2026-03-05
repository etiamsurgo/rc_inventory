from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =======================
# MODELS
# =======================

class Aircraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    category = db.Column(db.String(100))
    notes = db.Column(db.String(300))
    total_hours = db.Column(db.Float, default=0)

    maint_logs = db.relationship(
        'MaintenanceLog',
        backref='aircraft',
        cascade="all, delete"
    )

    flights = db.relationship(
        'FlightLog',
        backref='aircraft',
        cascade="all, delete"
    )


class MaintenanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'))
    description = db.Column(db.String(300))
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Battery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100))
    capacity = db.Column(db.String(100))
    cycles = db.Column(db.Integer, default=0)
    notes = db.Column(db.String(300))

    flights = db.relationship(
        'FlightLog',
        backref='battery',
        cascade="all, delete"
    )


class FlightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'))
    battery_id = db.Column(db.Integer, db.ForeignKey('battery.id'))
    duration = db.Column(db.Float)  # minutes
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    ama_number = db.Column(db.String(50))
    faa_number = db.Column(db.String(50))
    ama_expiration = db.Column(db.String(20))
    faa_expiration = db.Column(db.String(20))


# =======================
# DASHBOARD
# =======================

@app.route('/')
def dashboard():
    aircraft_count = Aircraft.query.count()
    battery_count = Battery.query.count()
    flight_count = FlightLog.query.count()

    total_hours = db.session.query(db.func.sum(Aircraft.total_hours)).scalar() or 0

    owner = Owner.query.first()

    return render_template(
        'home.html',
        aircraft_count=aircraft_count,
        battery_count=battery_count,
        flight_count=flight_count,
        total_hours=round(total_hours, 1),
        owner=owner
    )


# =======================
# AIRCRAFT (Sorting + Filtering)
# =======================

@app.route('/aircraft')
def aircraft():
    sort = request.args.get('sort', 'name')
    category_filter = request.args.get('category')

    query = Aircraft.query

    if category_filter:
        query = query.filter_by(category=category_filter)

    if sort == 'hours':
        query = query.order_by(Aircraft.total_hours.desc())
    else:
        query = query.order_by(Aircraft.name.asc())

    aircraft = query.all()

    categories = db.session.query(Aircraft.category).distinct()

    batteries = Battery.query.all()
    owner = Owner.query.first()

    return render_template(
        'aircraft.html',
        aircraft=aircraft,
        batteries=batteries,
        categories=categories,
        owner=owner
    )


@app.route('/add_aircraft', methods=['POST'])
def add_aircraft():
    new_aircraft = Aircraft(
        name=request.form['name'],
        brand=request.form['brand'],
        category=request.form['category'],
        notes=request.form['notes']
    )
    db.session.add(new_aircraft)
    db.session.commit()
    return redirect(url_for('aircraft'))


@app.route('/delete_aircraft/<int:id>')
def delete_aircraft(id):
    aircraft = Aircraft.query.get_or_404(id)
    db.session.delete(aircraft)
    db.session.commit()
    return redirect(url_for('aircraft'))


# =======================
# FLIGHT LOGGING (Links Battery ↔ Aircraft)
# =======================

@app.route('/add_flight/<int:aircraft_id>', methods=['POST'])
def add_flight(aircraft_id):
    duration = float(request.form['duration'])
    battery_id = int(request.form['battery_id'])

    flight = FlightLog(
        aircraft_id=aircraft_id,
        battery_id=battery_id,
        duration=duration
    )

    db.session.add(flight)

    aircraft = Aircraft.query.get(aircraft_id)
    aircraft.total_hours += duration / 60

    battery = Battery.query.get(battery_id)
    battery.cycles += 1

    db.session.commit()

    return redirect(url_for('aircraft'))


# =======================
# BATTERIES
# =======================

@app.route('/batteries')
def batteries():
    batteries = Battery.query.order_by(Battery.cycles.desc()).all()
    owner = Owner.query.first()
    return render_template('batteries.html', batteries=batteries, owner=owner)


@app.route('/add_battery', methods=['POST'])
def add_battery():
    battery = Battery(
        brand=request.form['brand'],
        capacity=request.form['capacity'],
        notes=request.form['notes']
    )
    db.session.add(battery)
    db.session.commit()
    return redirect(url_for('batteries'))


@app.route('/delete_battery/<int:id>')
def delete_battery(id):
    battery = Battery.query.get_or_404(id)
    db.session.delete(battery)
    db.session.commit()
    return redirect(url_for('batteries'))

@app.route("/owner")
def owner():
    return render_template("owner.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/reset-database", methods=["POST"])
def reset_database():
    from models import db, Aircraft, Battery, MaintenanceLog

    MaintenanceLog.query.delete()
    Battery.query.delete()
    Aircraft.query.delete()

    db.session.commit()

    return redirect(url_for("admin"))


# =======================

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
    app.run(debug=True)