/* Data layer for mobile app using Capacitor SQLite via sqlite-adapter.js
   Exposes init(), and CRUD helpers for aircraft, batteries, items, flights, and pilot_profile.
*/

const DataLayer = (function() {
  const DB = 'rc_fleet.db';

  function _parseQueryResult(res) {
    // plugin shapes vary; try common properties
    if (!res) return [];
    if (Array.isArray(res)) return res;
    if (res.values) return res.values;
    if (res.results) return res.results;
    if (res.rows) return res.rows;
    if (res.data) return res.data;
    return res;
  }

  async function init() {
    // open DB
    await SQLiteAdapter.openDB(DB).catch(err => { throw err; });

    const schema = [
      `CREATE TABLE IF NOT EXISTS aircraft (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manufacturer TEXT,
        model TEXT,
        name TEXT,
        type TEXT,
        default_battery_id INTEGER,
        notes TEXT,
        manual_filename TEXT,
        receipt_filename TEXT,
        picture_filename TEXT
      );`,

      `CREATE TABLE IF NOT EXISTS batteries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        capacity INTEGER,
        cells INTEGER,
        cycles INTEGER DEFAULT 0,
        type TEXT,
        brand TEXT,
        connector TEXT,
        notes TEXT,
        manual_filename TEXT,
        receipt_filename TEXT
      );`,

      `CREATE TABLE IF NOT EXISTS aircraft_batteries (
        aircraft_id INTEGER,
        battery_id INTEGER
      );`,

      `CREATE TABLE IF NOT EXISTS flights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aircraft_id INTEGER,
        battery_id INTEGER,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        minutes INTEGER,
        notes TEXT
      );`,

      `CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        brand TEXT,
        model TEXT,
        serial TEXT,
        notes TEXT,
        manual_filename TEXT,
        receipt_filename TEXT,
        picture_filename TEXT
      );`,

      `CREATE TABLE IF NOT EXISTS pilot_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        ama_number TEXT,
        ama_expiration TEXT,
        faa_number TEXT,
        faa_expiration TEXT,
        notes TEXT
      );`
    ];

    // execute as batch
    const stmts = schema.map(s => ({ statement: s, values: [] }));
    await SQLiteAdapter.execute(DB, stmts);
    return true;
  }

  /* Aircraft */
  async function getAircraft() {
    const res = await SQLiteAdapter.query(DB, 'SELECT * FROM aircraft ORDER BY name', []);
    return _parseQueryResult(res);
  }

  async function getAircraftById(id) {
    const res = await SQLiteAdapter.query(DB, 'SELECT * FROM aircraft WHERE id=?', [id]);
    const rows = _parseQueryResult(res);
    return rows && rows.length ? rows[0] : null;
  }

  async function addAircraft(a) {
    const stmt = `INSERT INTO aircraft (manufacturer, model, name, type, default_battery_id, notes, manual_filename, receipt_filename, picture_filename) VALUES (?,?,?,?,?,?,?,?,?)`;
    await SQLiteAdapter.execute(DB, [{ statement: stmt, values: [a.manufacturer, a.model, a.name, a.type, a.default_battery_id || null, a.notes || null, a.manual_filename || null, a.receipt_filename || null, a.picture_filename || null] }]);
  }

  async function updateAircraft(id, a) {
    const stmt = `UPDATE aircraft SET manufacturer=?, model=?, name=?, type=?, default_battery_id=?, notes=?, manual_filename=?, receipt_filename=?, picture_filename=? WHERE id=?`;
    await SQLiteAdapter.execute(DB, [{ statement: stmt, values: [a.manufacturer, a.model, a.name, a.type, a.default_battery_id || null, a.notes || null, a.manual_filename || null, a.receipt_filename || null, a.picture_filename || null, id] }]);
  }

  async function deleteAircraft(id) {
    await SQLiteAdapter.execute(DB, [{ statement: 'DELETE FROM flights WHERE aircraft_id=?', values: [id] }, { statement: 'DELETE FROM aircraft_batteries WHERE aircraft_id=?', values: [id] }, { statement: 'DELETE FROM aircraft WHERE id=?', values: [id] }]);
  }

  /* Batteries */
  async function getBatteries() {
    const res = await SQLiteAdapter.query(DB, 'SELECT * FROM batteries ORDER BY name', []);
    return _parseQueryResult(res);
  }

  async function addBattery(b) {
    const stmt = `INSERT INTO batteries (name, type, brand, capacity, cells, connector, cycles, notes, manual_filename, receipt_filename, picture_filename) VALUES (?,?,?,?,?,?,?,?,?,?,?)`;
    await SQLiteAdapter.execute(DB, [{ statement: stmt, values: [b.name, b.type || null, b.brand || null, b.capacity || null, b.cells || null, b.connector || null, b.cycles || 0, b.notes || null, b.manual_filename || null, b.receipt_filename || null, b.picture_filename || null] }]);
  }

  /* Flights */
  async function logFlight(f) {
    const stmt = `INSERT INTO flights (aircraft_id, battery_id, minutes, notes) VALUES (?,?,?,?)`;
    await SQLiteAdapter.execute(DB, [{ statement: stmt, values: [f.aircraft_id, f.battery_id || null, f.minutes, f.notes || null] }]);
    if (f.battery_id) {
      await SQLiteAdapter.execute(DB, [{ statement: 'UPDATE batteries SET cycles = cycles + 1 WHERE id=?', values: [f.battery_id] }]);
    }
  }

  async function getFlightsForAircraft(aircraft_id) {
    const res = await SQLiteAdapter.query(DB, 'SELECT f.*, b.name AS battery_name FROM flights f LEFT JOIN batteries b ON f.battery_id = b.id WHERE aircraft_id=? ORDER BY date DESC', [aircraft_id]);
    return _parseQueryResult(res);
  }

  /* Items */
  async function getItems() {
    const res = await SQLiteAdapter.query(DB, "SELECT * FROM items WHERE category != 'Battery' ORDER BY category, name", []);
    return _parseQueryResult(res);
  }

  async function addItem(it) {
    const stmt = `INSERT INTO items (name, category, brand, model, serial, notes, manual_filename, receipt_filename, picture_filename) VALUES (?,?,?,?,?,?,?,?,?)`;
    await SQLiteAdapter.execute(DB, [{ statement: stmt, values: [it.name, it.category || null, it.brand || null, it.model || null, it.serial || null, it.notes || null, it.manual_filename || null, it.receipt_filename || null, it.picture_filename || null] }]);
  }

  /* Pilot profile */
  async function getPilot() {
    const res = await SQLiteAdapter.query(DB, 'SELECT * FROM pilot_profile WHERE id=1', []);
    const rows = _parseQueryResult(res);
    return rows && rows.length ? rows[0] : null;
  }

  async function upsertPilot(p) {
    // try update, if 0 rows affected then insert
    await SQLiteAdapter.execute(DB, [{ statement: `INSERT OR REPLACE INTO pilot_profile (id, name, ama_number, ama_expiration, faa_number, faa_expiration, notes) VALUES (1,?,?,?,?,?,?)`, values: [p.name || null, p.ama_number || null, p.ama_expiration || null, p.faa_number || null, p.faa_expiration || null, p.notes || null] }]);
  }

  async function close() {
    await SQLiteAdapter.closeDB(DB);
  }

  return {
    init,
    getAircraft,
    getAircraftById,
    addAircraft,
    updateAircraft,
    deleteAircraft,
    getBatteries,
    addBattery,
    logFlight,
    getFlightsForAircraft,
    getItems,
    addItem,
    getPilot,
    upsertPilot,
    close
  };
})();

window.DataLayer = DataLayer;

export default DataLayer;
