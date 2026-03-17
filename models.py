from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Aircraft(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    type = db.Column(db.String(50))

    default_battery_id = db.Column(
        db.Integer,
        db.ForeignKey("battery.id"),
        nullable=True
    )

    default_battery = db.relationship(
        "Battery",
        foreign_keys=[default_battery_id]
    )

    flights = db.relationship(
        "Flight",
        backref="aircraft",
        lazy=True,
        cascade="all, delete-orphan"
    )

    maintenance_logs = db.relationship(
        "MaintenanceLog",
        backref="aircraft",
        lazy=True,
        cascade="all, delete-orphan"
    )

    @property
    def total_minutes(self):
        return sum(f.duration_minutes for f in self.flights)


class Battery(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    brand = db.Column(db.String(100))

    capacity = db.Column(db.Integer)

    battery_type = db.Column(db.String(50))

    cells = db.Column(db.Integer)

    cycles = db.Column(db.Integer, default=0)

    notes = db.Column(db.Text)

    flights = db.relationship("Flight", backref="battery", lazy=True)

    @property
    def health(self):

        if self.cycles < 100:
            return "Excellent"

        elif self.cycles < 200:
            return "Good"

        elif self.cycles < 300:
            return "Aging"

        else:
            return "Replace Soon"

    @property
    def warning(self):

        if self.cycles >= 300:
            return "🔴 Replace Soon"

        elif self.cycles >= 200:
            return "⚠ Aging Battery"

        return ""


class Flight(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey("aircraft.id"),
        index=True
    )

    battery_id = db.Column(
        db.Integer,
        db.ForeignKey("battery.id"),
        index=True
    )

    duration_minutes = db.Column(db.Integer)

    notes = db.Column(db.Text)

    date = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True
    )


class MaintenanceLog(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey("aircraft.id")
    )

    description = db.Column(db.Text)

    date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )