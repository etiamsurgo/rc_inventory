// Minimal Capacitor SQLite adapter wrapper
// Provides open/close/execute/query methods using Capacitor plugin when available.

const SQLiteAdapter = (function() {
  let sqlite = null;

  function getPlugin() {
    if (sqlite) return sqlite;
    // Capacitor exposes plugins in different ways depending on platform
    const globalCapacitor = window.Capacitor || {};
    sqlite = (globalCapacitor.Plugins && globalCapacitor.Plugins.CapacitorSQLite) || window.CapacitorSQLite || null;
    return sqlite;
  }

  async function openDB(database) {
    const p = getPlugin();
    if (!p) throw new Error('Capacitor SQLite plugin not available');
    return p.open({ database });
  }

  async function closeDB(database) {
    const p = getPlugin();
    if (!p) throw new Error('Capacitor SQLite plugin not available');
    return p.close({ database });
  }

  async function execute(database, statements) {
    const p = getPlugin();
    if (!p) throw new Error('Capacitor SQLite plugin not available');
    // statements: array of { statement: 'SQL', values: [] }
    const batch = statements.map(s => ({ statement: s.statement, values: s.values || [] }));
    return p.execute({ database, statements: batch });
  }

  async function query(database, statement, values) {
    const p = getPlugin();
    if (!p) throw new Error('Capacitor SQLite plugin not available');
    return p.query({ database, statement, values: values || [] });
  }

  return {
    openDB,
    closeDB,
    execute,
    query
  };
})();

// Expose for app use
window.SQLiteAdapter = SQLiteAdapter;
