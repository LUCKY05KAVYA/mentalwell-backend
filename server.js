const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const admin = require('./firebase'); // Firebase config

const app = express();
const port = 5000;

// Middleware
app.use(cors());
app.use(express.json());

// PostgreSQL connection config
const pool = new Pool({
  user: 'postgres.pxmnuseazbkkhtrycbko',
  host: 'aws-0-ap-south-1.pooler.supabase.com',
  database: 'postgres',
  password: 'Lemon@iitm55',
  port: 5432,
  ssl: {
    rejectUnauthorized: false,
  },
});

// Endpoint to get a random motivational quote
app.get('/get_daily_quote', async (req, res) => {
  try {
    const result = await pool.query('SELECT quote FROM motivational_quotes ORDER BY RANDOM() LIMIT 1');
    res.json({ quote: result.rows[0].quote });
  } catch (err) {
    console.error('Error fetching quote:', err);
    res.status(500).json({ error: 'Failed to fetch quote', details: err.message });
  }
});

// Endpoint to get a random fact
app.get('/get_daily_fact', async (req, res) => {
  try {
    const result = await pool.query('SELECT fact FROM facts ORDER BY RANDOM() LIMIT 1');
    res.json({ fact: result.rows[0].fact });
  } catch (err) {
    console.error('Error fetching fact:', err);
    res.status(500).json({ error: 'Failed to fetch fact', details: err.message });
  }
});

// Endpoint to submit mood and stress
// Endpoint to submit mood and stress
app.post('/submit_mood', async (req, res) => {
  console.log("Received POST request to /submit_mood", req.body); // Add this line to log the request
  
  const { mood, stress } = req.body;
  
  if (!mood || stress === undefined) {
    return res.status(400).json({ message: "Mood and stress are required." });
  }
  
  try {
    // Save to PostgreSQL
    await pool.query(
      'INSERT INTO mood_entries (mood, stress) VALUES ($1, $2)',
      [mood, stress]
    );

    // Push to Firebase Realtime DB
    const db = admin.database();
    const ref = db.ref('mood_updates');
    await ref.push({
      mood,
      stress,
      timestamp: Date.now(),
    });

    res.status(200).json({ message: 'Mood and stress submitted successfully.' });
  } catch (error) {
    console.error('Error submitting mood:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});


app.get('/ping', (req, res) => {
  res.send('pong');
});


// Start the server
app.listen(port, () => {
  console.log(`✅ Server is running on http://localhost:${port}`);
});
