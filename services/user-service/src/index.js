const express = require('express');
const client = require('prom-client');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

// Prometheus metrics
const register = new client.Registry();
client.collectDefaultMetrics({ register });
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.get('/health', (req, res) =>
  res.json({ status: 'ok', service: 'user-service', timestamp: new Date() })
);

// TODO: add routes
// app.use('/api/auth',  require('./routes/auth'));
// app.use('/api/users', require('./routes/users'));

app.listen(PORT, () => console.log(`user-service running on :${PORT}`));
module.exports = app;
